"""India website and data compliance endpoints (docs/compliance).

Public:   legal profile, demo-data status, guest erasure via manage link.
Account:  consents, withdrawal, export, correction, nominee, data requests,
          erasure, two-step sign-in enrolment.
Admin:    legal profile (super admin), incidents, compliance summary,
          minor-account action, data-request handling, audited reveal of
          identity and bank numbers.
"""
from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import get_db
from app.models.core import (
    AuditLog,
    Booking,
    BreachIncident,
    ConsentRecord,
    DataRequest,
    Nominee,
    OwnerBankAccount,
    OwnerVerification,
    SupportTicket,
    SystemConfiguration,
    User,
)
from app.modules.auth import service as auth_service
from app.modules.auth import totp
from app.modules.auth.dependencies import (
    CurrentUser,
    get_current_user,
    get_current_user_row,
    get_super_admin_actor,
    require_role,
)
from app.modules.auth.security import hash_password, verify_password
from app.modules.core.config_service import get_system_config
from app.modules.privacy import consent as consent_service
from app.modules.privacy import demo, legal_profile, rights
from app.modules.privacy.erasure import erase_guest_booking, erase_user
from app.modules.privacy.versions import NOTICE_VERSION, TERMS_VERSION
from app.modules.support import sla

router = APIRouter()


def _naive(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


# ── Public ───────────────────────────────────────────────────────────────

@router.get("/api/v1/legal/profile", tags=["Legal"])
async def get_legal_profile(db: AsyncSession = Depends(get_db)) -> dict:
    """Business facts and live booking terms that the legal pages, footer
    and checkout render. Unset facts are null (shown as placeholders)."""
    return await legal_profile.public_profile(db)


@router.get("/api/v1/meta/demo", tags=["Legal"])
async def demo_status(db: AsyncSession = Depends(get_db)) -> dict:
    counts = await demo.demo_counts(db)
    return {"demo_data_present": any(counts.values()), "counts": counts}


class ConfirmErase(BaseModel):
    confirm: str

    @field_validator("confirm")
    @classmethod
    def _must_say_delete(cls, v: str) -> str:
        if v.strip().upper() != "DELETE":
            raise ValueError('Type DELETE to confirm')
        return v


@router.post("/api/v1/bookings/manage/{token}/erase", tags=["Your data"])
async def guest_erase(token: str, body: ConfirmErase, request: Request, db: AsyncSession = Depends(get_db)) -> dict:
    """A guest erases their contact details from a booking with the private
    manage link. The booking itself (date, venue, amount) is kept for
    accounting; the link stops working."""
    from app.modules.booking.service import hash_manage_token

    ip = auth_service.get_client_ip(request)
    await auth_service.check_rate_limit(db, f"ratelimit:erase:ip:{ip}", max_attempts=10, window_seconds=300)
    async with db.begin():
        booking = (await db.execute(select(Booking).where(Booking.manage_token_hash == hash_manage_token(token)))).scalar_one_or_none()
        if booking is None or booking.customer_id is not None:
            raise HTTPException(status_code=404, detail="Booking not found")
        result = await erase_guest_booking(db, booking, reason="guest_request")
        req = await rights.record_completed_request(db, None, "erasure", result, booking_id=booking.id)
    return {"request_number": req.request_number, **result}


# ── Account: consents, export, correction, nominee, requests, erasure ────

@router.get("/api/v1/me/consents", tags=["Your data"])
async def my_consents(current_user: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> list[dict]:
    rows = await consent_service.list_for_user(db, current_user.id)
    return [consent_service.view(r) for r in rows]


class AcceptBody(BaseModel):
    """Acceptance of the current Privacy Notice and Terms by an existing
    account (DPDP s.5(2): notice for consent given before the Act), plus the
    18+ confirmation if the account never gave one."""

    accept: bool
    age_confirmed: bool = False

    @field_validator("accept")
    @classmethod
    def _accepted(cls, v: bool) -> bool:
        if v is not True:
            raise ValueError("accept must be true")
        return v


@router.post("/api/v1/me/consents/accept", tags=["Your data"])
async def accept_current_terms(
    body: AcceptBody,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    existing = await consent_service.list_for_user(db, current_user.id)
    has_age = any(r.purpose == "age_18_plus" and r.action == "given" for r in existing)
    if not has_age and not body.age_confirmed:
        raise HTTPException(status_code=422, detail=consent_service.AGE_REQUIRED_MESSAGE)
    purposes = ["terms", "privacy_notice"] + ([] if has_age else ["age_18_plus"])
    await db.rollback()
    async with db.begin():
        consent_service.add_records(db, purposes=purposes, source="notice_update", request=request, user_id=current_user.id)
    return {"accepted_terms_version": TERMS_VERSION, "notice_version": NOTICE_VERSION, "age_confirmed": True}


class WithdrawBody(BaseModel):
    confirm: bool

    @field_validator("confirm")
    @classmethod
    def _true(cls, v: bool) -> bool:
        if v is not True:
            raise ValueError("confirm must be true")
        return v


@router.post("/api/v1/me/consents/withdraw", tags=["Your data"])
async def withdraw_consent(
    body: WithdrawBody,
    user: User = Depends(get_current_user_row),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Withdraws consent for everything GroundKart does on the basis of
    consent (DPDP s.6(4)): the account is closed and personal data erased,
    except records a law requires us to keep."""
    if user.is_super_admin:
        raise HTTPException(status_code=409, detail="The super admin account can't be closed. Transfer the role first.")
    user_id = user.id
    await db.rollback()
    async with db.begin():
        result = await erase_user(db, user_id, reason="consent_withdrawn")
        req = await rights.record_completed_request(db, user_id, "withdraw_consent", result)
    return {"request_number": req.request_number, **result}


@router.get("/api/v1/me/data/export", tags=["Your data"])
async def export_my_data(current_user: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> Response:
    data = await rights.export(db, current_user.id)
    db.add(AuditLog(actor_id=current_user.id, action="user.data_exported", entity_type="user", entity_id=current_user.id))
    await db.commit()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    return Response(
        content=json.dumps(data, indent=2, ensure_ascii=False, default=str),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="groundkart-my-data-{stamp}.json"', "Cache-Control": "no-store"},
    )


class ProfileUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, min_length=8, max_length=20)


@router.patch("/api/v1/users/me", tags=["Your data"])
async def correct_profile(body: ProfileUpdate, user: User = Depends(get_current_user_row), db: AsyncSession = Depends(get_db)) -> dict:
    """Correction right (DPDP s.12)."""
    changes = body.model_dump(exclude_unset=True, exclude_none=True)
    if "phone" in changes:
        changes["phone"] = re.sub(r"[^\d+]", "", changes["phone"])
    if "email" in changes:
        changes["email"] = str(changes["email"]).strip().lower()
    for field in ("email", "phone"):
        if field in changes:
            clash = (await db.execute(select(User.id).where(getattr(User, field) == changes[field], User.id != user.id))).first()
            if clash:
                raise HTTPException(status_code=409, detail=f"That {field} is already used by another account")
    user_id = user.id
    await db.rollback()
    async with db.begin():
        row = (await db.execute(select(User).where(User.id == user_id))).scalar_one()
        for k, v in changes.items():
            setattr(row, k, v)
        row.updated_at = datetime.now(timezone.utc)
        db.add(AuditLog(actor_id=user_id, action="user.profile_corrected", entity_type="user", entity_id=user_id, extra_data={"fields": sorted(changes)}))
    return {"id": str(row.id), "name": row.name, "email": row.email, "phone": row.phone}


class NomineeBody(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    relationship: str | None = Field(default=None, max_length=100)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=20)


def _nominee_view(n: Nominee | None) -> dict | None:
    if n is None:
        return None
    return {"name": n.name, "relationship": n.relationship_to_user, "email": n.email, "phone": n.phone, "updated_at": n.updated_at.isoformat() if n.updated_at else None}


@router.get("/api/v1/me/nominee", tags=["Your data"])
async def get_nominee(current_user: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> dict | None:
    return _nominee_view((await db.execute(select(Nominee).where(Nominee.user_id == current_user.id))).scalar_one_or_none())


@router.put("/api/v1/me/nominee", tags=["Your data"])
async def set_nominee(body: NomineeBody, current_user: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> dict:
    async with db.begin():
        row = (await db.execute(select(Nominee).where(Nominee.user_id == current_user.id))).scalar_one_or_none()
        if row is None:
            row = Nominee(user_id=current_user.id, name=body.name)
            db.add(row)
        row.name = body.name
        row.relationship_to_user = body.relationship
        row.email = str(body.email) if body.email else None
        row.phone = body.phone
        row.updated_at = datetime.now(timezone.utc)
        db.add(AuditLog(actor_id=current_user.id, action="user.nominee_set", entity_type="user", entity_id=current_user.id))
    return _nominee_view(row)


@router.delete("/api/v1/me/nominee", status_code=204, tags=["Your data"])
async def delete_nominee(current_user: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> Response:
    async with db.begin():
        row = (await db.execute(select(Nominee).where(Nominee.user_id == current_user.id))).scalar_one_or_none()
        if row is not None:
            await db.delete(row)
    return Response(status_code=204)


class DataRequestBody(BaseModel):
    type: str
    details: str | None = Field(default=None, max_length=4000)

    @field_validator("type")
    @classmethod
    def _known(cls, v: str) -> str:
        if v not in rights.REQUEST_TYPES:
            raise ValueError(f"type must be one of {', '.join(rights.REQUEST_TYPES)}")
        return v


@router.get("/api/v1/me/data-requests", tags=["Your data"])
async def my_data_requests(current_user: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> list[dict]:
    rows = (await db.execute(select(DataRequest).where(DataRequest.user_id == current_user.id).order_by(DataRequest.created_at.desc()))).scalars().all()
    return [rights.request_view(r) for r in rows]


@router.post("/api/v1/me/data-requests", status_code=201, tags=["Your data"])
async def create_data_request(body: DataRequestBody, current_user: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> dict:
    async with db.begin():
        req = await rights.open_request(db, current_user.id, body.type, body.details)
    return rights.request_view(req)


@router.post("/api/v1/me/erase", tags=["Your data"])
async def erase_me(body: ConfirmErase, user: User = Depends(get_current_user_row), db: AsyncSession = Depends(get_db)) -> dict:
    if user.is_super_admin:
        raise HTTPException(status_code=409, detail="The super admin account can't be deleted. Transfer the role first.")
    user_id = user.id
    await db.rollback()
    async with db.begin():
        result = await erase_user(db, user_id, reason="self_service_erasure")
        req = await rights.record_completed_request(db, user_id, "erasure", result)
    return {"request_number": req.request_number, **result}


# ── Two-step sign-in (admins) ────────────────────────────────────────────

class CodeBody(BaseModel):
    code: str = Field(min_length=6, max_length=20)


@router.post("/api/v1/auth/2fa/setup", tags=["Auth"])
async def two_factor_setup(user: User = Depends(get_current_user_row), db: AsyncSession = Depends(get_db)) -> dict:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Two-step sign-in is for admin accounts")
    if user.totp_enabled_at is not None:
        raise HTTPException(status_code=409, detail="Two-step sign-in is already on. Turn it off first to re-enrol.")
    secret = totp.new_secret()
    user_id, account = user.id, user.email or user.phone
    await db.rollback()
    async with db.begin():
        row = (await db.execute(select(User).where(User.id == user_id))).scalar_one()
        row.totp_secret_enc = secret  # EncryptedText column
    return {"secret": secret, "otpauth_uri": totp.provisioning_uri(secret, account)}


@router.post("/api/v1/auth/2fa/enable", tags=["Auth"])
async def two_factor_enable(body: CodeBody, user: User = Depends(get_current_user_row), db: AsyncSession = Depends(get_db)) -> dict:
    if user.role != "admin" or not user.totp_secret_enc:
        raise HTTPException(status_code=400, detail="Start set-up first")
    step = totp.verify(user.totp_secret_enc, body.code)
    if step is None:
        raise HTTPException(status_code=400, detail="That code is not right. Check the time on your phone and try again.")
    codes = totp.new_recovery_codes()
    user_id = user.id
    await db.rollback()
    async with db.begin():
        row = (await db.execute(select(User).where(User.id == user_id))).scalar_one()
        row.totp_enabled_at = datetime.now(timezone.utc)
        row.totp_last_used_step = step
        row.totp_recovery_hashes = [hash_password(c) for c in codes]
        db.add(AuditLog(actor_id=user_id, action="user.2fa_enabled", entity_type="user", entity_id=user_id))
    return {"enabled": True, "recovery_codes": codes}


@router.post("/api/v1/auth/2fa/disable", tags=["Auth"])
async def two_factor_disable(body: CodeBody, user: User = Depends(get_current_user_row), db: AsyncSession = Depends(get_db)) -> dict:
    if user.totp_enabled_at is None:
        return {"enabled": False}
    if settings.resolve_admin_2fa_required():
        raise HTTPException(status_code=409, detail="Two-step sign-in is required for admins on this server")
    if totp.verify(user.totp_secret_enc or "", body.code, last_used_step=user.totp_last_used_step) is None:
        raise HTTPException(status_code=400, detail="That code is not right")
    user_id = user.id
    await db.rollback()
    async with db.begin():
        row = (await db.execute(select(User).where(User.id == user_id))).scalar_one()
        row.totp_enabled_at = None
        row.totp_secret_enc = None
        row.totp_recovery_hashes = None
        db.add(AuditLog(actor_id=user_id, action="user.2fa_disabled", entity_type="user", entity_id=user_id))
    return {"enabled": False}


# ── Admin ────────────────────────────────────────────────────────────────

@router.put("/api/v1/admin/legal/profile", tags=["Legal"])
async def update_legal_profile(body: dict, actor: User = Depends(get_super_admin_actor), db: AsyncSession = Depends(get_db)) -> dict:
    updates = legal_profile.clean_update(body)
    async with db.begin():
        config = await get_system_config(db)
        merged = dict(config.legal_profile or {})
        merged.update(updates)
        config.legal_profile = merged
        db.add(AuditLog(actor_id=actor.id, action="legal_profile.updated", entity_type="system_configuration", extra_data={"fields": sorted(updates)}))
    return await legal_profile.public_profile(db)


class MinorBody(BaseModel):
    note: str | None = Field(default=None, max_length=1000)


@router.post("/api/v1/admin/users/{user_id}/minor-account", tags=["Admin: compliance"])
async def minor_account(user_id: uuid.UUID, body: MinorBody, current_user: CurrentUser = Depends(require_role("admin")), db: AsyncSession = Depends(get_db)) -> dict:
    """GroundKart is adults-only. When an account is found to belong to
    someone under 18: suspend it and erase its personal data, keeping only
    what a law requires. No parental-consent flow by design (D-12)."""
    target = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if target is None:
        raise HTTPException(status_code=404, detail="User not found")
    if target.role == "admin":
        raise HTTPException(status_code=409, detail="Admin accounts can't be closed this way")
    await db.rollback()
    async with db.begin():
        row = (await db.execute(select(User).where(User.id == user_id))).scalar_one()
        row.suspension_reason = "Account belongs to a person under 18 (GroundKart is adults-only)"
        result = await erase_user(db, user_id, reason="minor_account", actor_id=current_user.id, suspend=True)
        req = await rights.record_completed_request(db, user_id, "erasure", {**result, "note": body.note, "by_admin": str(current_user.id)})
    return {"request_number": req.request_number, **result}


@router.get("/api/v1/admin/owner-verifications/{verification_id}/numbers", tags=["Admin: compliance"])
async def reveal_verification_numbers(verification_id: uuid.UUID, current_user: CurrentUser = Depends(require_role("admin")), db: AsyncSession = Depends(get_db)) -> dict:
    """Full identity numbers for checking against the document. Every call is audit-logged."""
    v = (await db.execute(select(OwnerVerification).where(OwnerVerification.id == verification_id))).scalar_one_or_none()
    if v is None:
        raise HTTPException(status_code=404, detail="Verification not found")
    data = {"identification_type": v.identification_type, "identification_number": v.identification_number, "pan": v.pan, "gstin": v.gstin}
    await db.rollback()
    async with db.begin():
        db.add(AuditLog(actor_id=current_user.id, action="owner_verification.numbers_viewed", entity_type="owner_verification", entity_id=verification_id))
    return data


@router.get("/api/v1/admin/owners/{owner_id}/bank-accounts/{account_id}/reveal", tags=["Admin: compliance"])
async def reveal_bank_account(owner_id: uuid.UUID, account_id: uuid.UUID, current_user: CurrentUser = Depends(require_role("admin")), db: AsyncSession = Depends(get_db)) -> dict:
    acc = (await db.execute(select(OwnerBankAccount).where(OwnerBankAccount.id == account_id, OwnerBankAccount.owner_id == owner_id))).scalar_one_or_none()
    if acc is None:
        raise HTTPException(status_code=404, detail="Bank account not found")
    data = {"account_holder_name": acc.account_holder_name, "account_number": acc.account_number, "ifsc_code": acc.ifsc_code}
    await db.rollback()
    async with db.begin():
        db.add(AuditLog(actor_id=current_user.id, action="owner_bank_account.number_viewed", entity_type="owner_bank_account", entity_id=account_id))
    return data


class IncidentCreate(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=1, max_length=10000)
    detected_at: datetime | None = None
    occurred_at: datetime | None = None
    data_categories: list[str] | None = None
    affected_count: int | None = Field(default=None, ge=0)
    is_cyber_incident: bool = True
    is_personal_data_breach: bool = True


class IncidentUpdate(BaseModel):
    status: str | None = None
    cert_in_reported_at: datetime | None = None
    board_initial_reported_at: datetime | None = None
    board_report_submitted_at: datetime | None = None
    users_notified_at: datetime | None = None
    containment_notes: str | None = Field(default=None, max_length=10000)
    remediation_notes: str | None = Field(default=None, max_length=10000)
    affected_count: int | None = Field(default=None, ge=0)

    @field_validator("status")
    @classmethod
    def _status(cls, v):
        if v is not None and v not in ("open", "contained", "closed"):
            raise ValueError("status must be open, contained or closed")
        return v


def _overdue(inc: BreachIncident, now: datetime) -> list[str]:
    out = []
    if inc.is_cyber_incident and inc.cert_in_reported_at is None and now > _naive(inc.cert_in_due_at):
        out.append("cert_in")
    if inc.is_personal_data_breach and inc.board_report_submitted_at is None and now > _naive(inc.board_report_due_at):
        out.append("board_report")
    if inc.is_personal_data_breach and inc.users_notified_at is None and now > _naive(inc.detected_at) + timedelta(hours=24):
        out.append("users_notice")
    return out


def _incident_view(inc: BreachIncident) -> dict:
    now = datetime.now(timezone.utc)
    iso = lambda d: _naive(d).isoformat() if d else None  # noqa: E731
    return {
        "id": str(inc.id),
        "reference": inc.reference,
        "title": inc.title,
        "description": inc.description,
        "status": inc.status,
        "detected_at": iso(inc.detected_at),
        "occurred_at": iso(inc.occurred_at),
        "data_categories": inc.data_categories or [],
        "affected_count": inc.affected_count,
        "is_cyber_incident": inc.is_cyber_incident,
        "is_personal_data_breach": inc.is_personal_data_breach,
        "cert_in_due_at": iso(inc.cert_in_due_at),
        "board_report_due_at": iso(inc.board_report_due_at),
        "users_notice_due": "without_delay",
        "cert_in_reported_at": iso(inc.cert_in_reported_at),
        "board_initial_reported_at": iso(inc.board_initial_reported_at),
        "board_report_submitted_at": iso(inc.board_report_submitted_at),
        "users_notified_at": iso(inc.users_notified_at),
        "containment_notes": inc.containment_notes,
        "remediation_notes": inc.remediation_notes,
        "overdue": _overdue(inc, now) if inc.status != "closed" else [],
        "created_at": iso(inc.created_at),
        "closed_at": iso(inc.closed_at),
    }


@router.post("/api/v1/admin/compliance/incidents", status_code=201, tags=["Admin: compliance"])
async def create_incident(body: IncidentCreate, current_user: CurrentUser = Depends(require_role("admin")), db: AsyncSession = Depends(get_db)) -> dict:
    detected = _naive(body.detected_at or datetime.now(timezone.utc))
    async with db.begin():
        ref = await sla.next_number(db, "GK-INC", "incident_number_seq", width=3, at=detected)
        inc = BreachIncident(
            reference=ref,
            title=body.title,
            description=body.description,
            detected_at=detected,
            occurred_at=body.occurred_at,
            data_categories=body.data_categories,
            affected_count=body.affected_count,
            is_cyber_incident=body.is_cyber_incident,
            is_personal_data_breach=body.is_personal_data_breach,
            cert_in_due_at=detected + timedelta(hours=6),
            board_report_due_at=detected + timedelta(hours=72),
            created_by=current_user.id,
        )
        db.add(inc)
        await db.flush()
        db.add(AuditLog(actor_id=current_user.id, action="breach_incident.created", entity_type="breach_incident", entity_id=inc.id))
    await db.refresh(inc)
    return _incident_view(inc)


@router.get("/api/v1/admin/compliance/incidents", tags=["Admin: compliance"])
async def list_incidents(current_user: CurrentUser = Depends(require_role("admin")), db: AsyncSession = Depends(get_db)) -> list[dict]:
    rows = (await db.execute(select(BreachIncident).order_by(BreachIncident.detected_at.desc()))).scalars().all()
    return [_incident_view(r) for r in rows]


@router.patch("/api/v1/admin/compliance/incidents/{incident_id}", tags=["Admin: compliance"])
async def update_incident(incident_id: uuid.UUID, body: IncidentUpdate, current_user: CurrentUser = Depends(require_role("admin")), db: AsyncSession = Depends(get_db)) -> dict:
    async with db.begin():
        inc = (await db.execute(select(BreachIncident).where(BreachIncident.id == incident_id))).scalar_one_or_none()
        if inc is None:
            raise HTTPException(status_code=404, detail="Incident not found")
        changes = body.model_dump(exclude_unset=True)
        for k, v in changes.items():
            setattr(inc, k, v)
        if changes.get("status") == "closed" and inc.closed_at is None:
            inc.closed_at = datetime.now(timezone.utc)
        inc.updated_at = datetime.now(timezone.utc)
        db.add(AuditLog(actor_id=current_user.id, action="breach_incident.updated", entity_type="breach_incident", entity_id=inc.id, extra_data={"fields": sorted(changes)}))
    await db.refresh(inc)
    return _incident_view(inc)


@router.get("/api/v1/admin/compliance/data-requests", tags=["Admin: compliance"])
async def list_data_requests(status: str | None = None, current_user: CurrentUser = Depends(require_role("admin")), db: AsyncSession = Depends(get_db)) -> list[dict]:
    q = select(DataRequest).order_by(DataRequest.due_at.asc())
    if status:
        q = q.where(DataRequest.status == status)
    rows = (await db.execute(q.limit(200))).scalars().all()
    now = datetime.now(timezone.utc)
    return [{**rights.request_view(r), "id": str(r.id), "user_id": str(r.user_id) if r.user_id else None, "overdue": r.status == "open" and now > _naive(r.due_at)} for r in rows]


class DataRequestUpdate(BaseModel):
    status: str
    note: str | None = Field(default=None, max_length=4000)

    @field_validator("status")
    @classmethod
    def _s(cls, v):
        if v not in ("completed", "rejected", "open"):
            raise ValueError("status must be open, completed or rejected")
        return v


@router.patch("/api/v1/admin/compliance/data-requests/{request_id}", tags=["Admin: compliance"])
async def update_data_request(request_id: uuid.UUID, body: DataRequestUpdate, current_user: CurrentUser = Depends(require_role("admin")), db: AsyncSession = Depends(get_db)) -> dict:
    async with db.begin():
        req = (await db.execute(select(DataRequest).where(DataRequest.id == request_id))).scalar_one_or_none()
        if req is None:
            raise HTTPException(status_code=404, detail="Request not found")
        req.status = body.status
        req.completed_at = datetime.now(timezone.utc) if body.status != "open" else None
        req.result = {**(req.result or {}), "note": body.note, "by_admin": str(current_user.id)}
        req.updated_at = datetime.now(timezone.utc)
        db.add(AuditLog(actor_id=current_user.id, action="data_request.updated", entity_type="data_request", entity_id=req.id, extra_data={"status": body.status}))
    return rights.request_view(req)


@router.get("/api/v1/admin/compliance/summary", tags=["Admin: compliance"])
async def compliance_summary(current_user: CurrentUser = Depends(require_role("admin")), db: AsyncSession = Depends(get_db)) -> dict:
    """One screen for the Grievance Officer: open complaints and data
    requests with due dates, overdue items, consent counts, incidents."""
    now = datetime.now(timezone.utc)
    open_states = ["open", "in_review", "waiting_customer"]
    count = lambda q: db.scalar(select(func.count()).select_from(q.subquery()))  # noqa: E731
    tickets_open = await count(select(SupportTicket.id).where(SupportTicket.status.in_(open_states)))
    ack_overdue = await count(select(SupportTicket.id).where(SupportTicket.status.in_(open_states), SupportTicket.acknowledged_at.is_(None), SupportTicket.ack_due_at < now))
    resolve_overdue = await count(select(SupportTicket.id).where(SupportTicket.status.in_(open_states), SupportTicket.resolve_due_at < now))
    grievances_open = await count(select(SupportTicket.id).where(SupportTicket.status.in_(open_states), SupportTicket.category.in_(["grievance", "content_report", "data_request"])))
    dr_open = await count(select(DataRequest.id).where(DataRequest.status == "open"))
    dr_overdue = await count(select(DataRequest.id).where(DataRequest.status == "open", DataRequest.due_at < now))
    consent_rows = (await db.execute(select(ConsentRecord.purpose, ConsentRecord.action, func.count()).group_by(ConsentRecord.purpose, ConsentRecord.action))).all()
    incidents = (await db.execute(select(BreachIncident).where(BreachIncident.status != "closed"))).scalars().all()
    upcoming = (
        await db.execute(
            select(SupportTicket)
            .where(SupportTicket.status.in_(open_states), SupportTicket.resolve_due_at.is_not(None))
            .order_by(SupportTicket.resolve_due_at.asc())
            .limit(10)
        )
    ).scalars().all()
    config = await db.get(SystemConfiguration, 1)
    return {
        "tickets": {"open": tickets_open, "ack_overdue": ack_overdue, "resolve_overdue": resolve_overdue, "grievances_open": grievances_open},
        "data_requests": {"open": dr_open, "overdue": dr_overdue},
        "consents": [{"purpose": p, "action": a, "count": c} for p, a, c in consent_rows],
        "incidents": [_incident_view(i) for i in incidents],
        "next_due": [
            {
                "id": str(t.id),
                "ticket_number": t.ticket_number,
                "subject": t.subject,
                "category": t.category,
                "resolve_due_at": _naive(t.resolve_due_at).isoformat(),
                "sla_state": sla.sla_state(t, now),
            }
            for t in upcoming
        ],
        "legal_profile_missing": [k for k in legal_profile.FIELDS if not ((config.legal_profile or {}).get(k) if config else None)],
        "admin_2fa_required": settings.resolve_admin_2fa_required(),
    }
