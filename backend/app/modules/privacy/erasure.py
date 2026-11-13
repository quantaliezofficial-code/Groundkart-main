"""Erasure and anonymisation (DPDP Act s.8(7), s.12; Rules r.8).

``erase_user`` is used by self-service deletion (My Data, DELETE /users/me),
consent withdrawal, the admin minor-account action and the inactivity job.
It removes or anonymises personal data across tables and files, and keeps
only what a law requires, recording why in the returned ``kept`` list.
"""
from __future__ import annotations

import logging
import secrets
import uuid
from datetime import datetime, timezone

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.core import (
    AuditLog,
    Booking,
    BrokerProfile,
    GuestEnquiry,
    HelpFeedback,
    IdempotencyKey,
    Nominee,
    Notification,
    OwnerBankAccount,
    OwnerVerification,
    RefreshToken,
    SupportTicket,
    TicketEvent,
    User,
    Venue,
)
from app.modules.auth.security import hash_password
from app.modules.privacy import consent as consent_service

log = logging.getLogger("groundkart.erasure")

ERASED = "[erased at the user's request]"

KEPT_BY_LAW = [
    {"table": "bookings (date, venue, amount, status)", "reason": "Tax and accounting records, kept 8 years (D-07, Q-12)"},
    {"table": "payments, refunds, payouts, ledger_entries, broker_commissions", "reason": "Tax and accounting records, kept 8 years (D-07, Q-12)"},
    {"table": "audit_logs", "reason": "Security logs kept at least 1 year (DPDP Rules r.6(1)(e), CERT-In Directions 2022)"},
    {"table": "consent_records", "reason": "Proof of what was agreed (DPDP Act s.6(10)); deleted 1 year after closure"},
]

FORMER_NAMES = {"customer": "Former customer", "owner": "Former venue owner", "broker": "Former partner", "admin": "Former admin"}


def former_name(role: str) -> str:
    return FORMER_NAMES.get(role, "Former customer")


async def _delete_private_file(storage_key: str | None) -> None:
    if not storage_key:
        return
    try:
        from app.storage_client import get_private_file_storage

        storage = get_private_file_storage()
        if hasattr(storage, "delete"):
            await storage.delete(storage_key)
    except Exception:  # never block erasure on a missing file; log for follow-up
        log.warning("could not delete private file %s during erasure", storage_key, exc_info=True)


async def erase_user(
    session: AsyncSession,
    user_id: uuid.UUID,
    *,
    reason: str,
    actor_id: uuid.UUID | None = None,
    suspend: bool = False,
) -> dict:
    """Erase one account. Caller owns the transaction (call inside
    ``async with session.begin()``). Returns a summary for the data request."""
    now = datetime.now(timezone.utc)
    user = (await session.execute(select(User).where(User.id == user_id).with_for_update())).scalar_one()
    original_email = user.email
    tag = user.id.hex[:12]

    user.name = former_name(user.role)
    user.email = f"erased-{tag}@erased.invalid"
    user.phone = f"erased-{tag}"
    user.password_hash = hash_password(secrets.token_urlsafe(32))
    user.totp_secret_enc = None
    user.totp_enabled_at = None
    user.totp_recovery_hashes = None
    user.must_change_password = False
    user.deleted_at = user.deleted_at or now
    if suspend:
        user.suspended_at = user.suspended_at or now
    user.updated_at = now

    await session.execute(
        update(RefreshToken).where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None)).values(revoked_at=now)
    )
    await session.execute(update(Venue).where(Venue.owner_id == user_id).values(status="archived"))
    # Bookings: keep the financial skeleton, drop what the person wrote.
    await session.execute(update(Booking).where(Booking.customer_id == user_id).values(customer_notes=None))
    # Tickets and their comments written by this person.
    ticket_ids = (await session.execute(select(SupportTicket.id).where(SupportTicket.creator_id == user_id))).scalars().all()
    if ticket_ids:
        await session.execute(update(SupportTicket).where(SupportTicket.id.in_(ticket_ids)).values(subject=ERASED, description=ERASED))
    await session.execute(update(TicketEvent).where(TicketEvent.actor_id == user_id, TicketEvent.comment.is_not(None)).values(comment=ERASED))
    await session.execute(delete(Notification).where(Notification.user_id == user_id))
    await session.execute(delete(Nominee).where(Nominee.user_id == user_id))
    await session.execute(update(HelpFeedback).where(HelpFeedback.user_id == user_id).values(user_id=None))
    await session.execute(delete(IdempotencyKey).where(IdempotencyKey.actor_id == user_id))
    if original_email:
        await session.execute(
            update(GuestEnquiry)
            .where(GuestEnquiry.email == original_email)
            .values(name="Former visitor", email=f"erased-{tag}@erased.invalid", phone=None, message=ERASED)
        )
    # Owner verification: numbers, business name and the document itself.
    verifications = (await session.execute(select(OwnerVerification).where(OwnerVerification.user_id == user_id))).scalars().all()
    for v in verifications:
        await _delete_private_file(v.storage_key)
        v.storage_key = None
        v.document_url = ""
        v.identification_number = None
        v.pan = None
        v.gstin = None
        v.business_name = None
    await session.execute(delete(OwnerBankAccount).where(OwnerBankAccount.owner_id == user_id))
    await session.execute(update(BrokerProfile).where(BrokerProfile.user_id == user_id).values(payout_details=None, notes=None, company_name=None))

    consent_service.add_records(
        session,
        purposes=consent_service.SERVICE_PURPOSES,
        source="erasure",
        user_id=user_id,
        action="withdrawn",
    )
    session.add(
        AuditLog(
            actor_id=actor_id or user_id,
            action="user.erased",
            entity_type="user",
            entity_id=user_id,
            extra_data={"reason": reason, "suspended": suspend},
        )
    )
    return {"status": "completed", "erased_at": now.isoformat(), "kept": KEPT_BY_LAW}


async def erase_guest_booking(session: AsyncSession, booking: Booking, *, reason: str) -> dict:
    now = datetime.now(timezone.utc)
    booking.guest_name = "Former guest"
    booking.guest_email = f"erased-{booking.id.hex[:12]}@erased.invalid"
    booking.guest_phone = None
    booking.customer_notes = None
    booking.manage_token_hash = None
    booking.updated_at = now
    consent_service.add_records(
        session, purposes=consent_service.SERVICE_PURPOSES, source="erasure", booking_id=booking.id, action="withdrawn"
    )
    session.add(AuditLog(action="booking.guest_erased", entity_type="booking", entity_id=booking.id, extra_data={"reason": reason}))
    return {"status": "completed", "erased_at": now.isoformat(), "kept": KEPT_BY_LAW[:2]}
