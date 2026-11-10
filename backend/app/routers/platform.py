"""
Routes for: team (super admin), referral partners, the broker dashboard,
owner referral codes, banners, records & exports, and share pages.

Kept in a router rather than appended to app/main.py so the permission
model for these areas can be read in one screen:

    get_super_admin_actor   team, broker commission terms, code regeneration
    get_admin_actor         brokers (create / contact details / payouts),
                            venue referral corrections, banners, records
    get_broker_actor        a broker's own dashboard — every query is
                            scoped to actor.id, never to an id from the URL
    require_role(owner…)    applying a referral code to one's own venue
"""
from __future__ import annotations

import re
import uuid
from datetime import date

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, Response, UploadFile
from fastapi.responses import HTMLResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import get_db
from app.models.core import BrokerProfile, User, Venue
from app.modules.admin import passwords_service
from app.modules.auth import service as auth_service
from app.modules.auth.dependencies import (
    CurrentUser,
    get_admin_actor,
    get_broker_actor,
    get_super_admin_actor,
    require_role,
)
from app.modules.banners import service as banners_service
from app.modules.partners import service as partners_service
from app.modules.records import service as records_service
from app.modules.share import service as share_service
from app.modules.storage.base import MAX_UPLOAD_SIZE_BYTES
from app.modules.team import service as team_service
from app.schemas.partners import (
    AccountCreatedResponse,
    AdminCreateRequest,
    AdminVenueBrokerRequest,
    BannerCreateRequest,
    BannerUpdateRequest,
    BannerView,
    BookingRegisterRow,
    BrokerCreatedResponse,
    BrokerCreateRequest,
    BrokerPayoutRequest,
    BrokerPayoutView,
    BrokerSelfUpdateRequest,
    BrokerSelfView,
    BrokerUpdateRequest,
    BrokerView,
    CommissionView,
    ExportInfo,
    PublicBannerView,
    ReferralCodeCheckResponse,
    ReferralCodeRequest,
    ReferredBookingView,
    ReferredVenueView,
    TeamMemberView,
    VenueHistoryResponse,
    VenueReferralView,
    VenueRegisterRow,
)
from app.storage_client import get_file_storage

router = APIRouter()


def _csv_response(filename: str, body: str) -> Response:
    return Response(
        content=body,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-store",
        },
    )


# ===========================================================================
# Team — super admin only
# ===========================================================================


@router.get("/api/v1/admin/team", response_model=list[TeamMemberView], tags=["Team"])
async def list_team_route(
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(get_super_admin_actor),
) -> list[TeamMemberView]:
    return [TeamMemberView(**row) for row in await team_service.list_team(db)]


@router.post("/api/v1/admin/team", response_model=AccountCreatedResponse, status_code=201, tags=["Team"])
async def create_admin_route(
    body: AdminCreateRequest,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(get_super_admin_actor),
) -> AccountCreatedResponse:
    user = await team_service.create_admin(db, actor=actor, name=body.name, phone=body.phone, email=body.email)
    setup_url = await passwords_service.admin_generate_reset_link(
        db, actor.id, user.id, "New admin account: set password", "team", str(user.id)
    )
    return AccountCreatedResponse(id=user.id, name=user.name, setup_url=setup_url)


# ===========================================================================
# Referral partners — admin console
# ===========================================================================


@router.get("/api/v1/admin/brokers", response_model=list[BrokerView], tags=["Referral partners"])
async def list_brokers_route(
    search: str | None = Query(default=None, max_length=80),
    status: str | None = Query(default=None, pattern="^(active|paused)$"),
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(get_admin_actor),
) -> list[BrokerView]:
    return [BrokerView(**row) for row in await partners_service.list_brokers(db, search=search, status=status)]


@router.post("/api/v1/admin/brokers", response_model=BrokerCreatedResponse, status_code=201, tags=["Referral partners"])
async def create_broker_route(
    body: BrokerCreateRequest,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(get_admin_actor),
) -> BrokerCreatedResponse:
    """Admins and the super admin can add a broker. A rate or basis sent by
    a regular admin is refused rather than silently replaced by the
    default, so nobody believes they set terms they did not."""
    if not actor.is_super_admin and (body.commission_percent is not None or body.commission_basis is not None):
        raise HTTPException(
            status_code=403,
            detail="Only the super admin can set a broker's commission terms. Leave them blank to use the default rate.",
        )
    user, _profile = await partners_service.create_broker(
        db,
        actor=actor,
        name=body.name,
        phone=body.phone,
        email=body.email,
        commission_percent=body.commission_percent,
        commission_basis=body.commission_basis,
        company_name=body.company_name,
        city=body.city,
        payout_method=body.payout_method,
        payout_details=body.payout_details,
        notes=body.notes,
    )
    setup_url = await passwords_service.admin_generate_reset_link(
        db, actor.id, user.id, "New referral partner account: set password", "broker", str(user.id)
    )
    return BrokerCreatedResponse(broker=BrokerView(**await partners_service.get_broker(db, user.id)), setup_url=setup_url)


@router.get("/api/v1/admin/brokers/{broker_id}", response_model=BrokerView, tags=["Referral partners"])
async def get_broker_route(
    broker_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(get_admin_actor),
) -> BrokerView:
    return BrokerView(**await partners_service.get_broker(db, broker_id))


@router.patch("/api/v1/admin/brokers/{broker_id}", response_model=BrokerView, tags=["Referral partners"])
async def update_broker_route(
    broker_id: uuid.UUID,
    body: BrokerUpdateRequest,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(get_admin_actor),
) -> BrokerView:
    await partners_service.update_broker(
        db, actor=actor, broker_id=broker_id, changes=body.model_dump(exclude_unset=True)
    )
    return BrokerView(**await partners_service.get_broker(db, broker_id))


@router.post("/api/v1/admin/brokers/{broker_id}/regenerate-code", response_model=BrokerView, tags=["Referral partners"])
async def regenerate_broker_code_route(
    broker_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(get_super_admin_actor),
) -> BrokerView:
    await partners_service.regenerate_referral_code(db, actor=actor, broker_id=broker_id)
    return BrokerView(**await partners_service.get_broker(db, broker_id))


@router.post("/api/v1/admin/brokers/{broker_id}/setup-link", response_model=AccountCreatedResponse, tags=["Referral partners"])
async def reissue_broker_setup_link_route(
    broker_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(get_admin_actor),
) -> AccountCreatedResponse:
    """Issue a fresh one-time set-password link — for a broker who lost the
    first one or let it expire. Any earlier link stops working."""
    broker = await partners_service.get_broker(db, broker_id)
    await db.rollback()  # close the read transaction before the write below opens its own
    setup_url = await passwords_service.admin_generate_reset_link(
        db, actor.id, broker_id, "Referral partner access link reissued", "broker", str(broker_id)
    )
    return AccountCreatedResponse(id=broker_id, name=broker["name"], setup_url=setup_url)


@router.get("/api/v1/admin/brokers/{broker_id}/venues", response_model=list[ReferredVenueView], tags=["Referral partners"])
async def admin_broker_venues_route(
    broker_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(get_admin_actor),
) -> list[ReferredVenueView]:
    return [ReferredVenueView(**r) for r in await partners_service.list_referred_venues(db, broker_id)]


@router.get("/api/v1/admin/brokers/{broker_id}/bookings", response_model=list[ReferredBookingView], tags=["Referral partners"])
async def admin_broker_bookings_route(
    broker_id: uuid.UUID,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(get_admin_actor),
) -> list[ReferredBookingView]:
    rows = await partners_service.list_referred_bookings(db, broker_id, limit=limit, offset=offset)
    return [ReferredBookingView(**r) for r in rows]


@router.get("/api/v1/admin/brokers/{broker_id}/commissions", response_model=list[CommissionView], tags=["Referral partners"])
async def admin_broker_commissions_route(
    broker_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(get_admin_actor),
) -> list[CommissionView]:
    return [CommissionView(**r) for r in await partners_service.list_commissions(db, broker_id=broker_id)]


@router.get("/api/v1/admin/brokers/{broker_id}/payouts", response_model=list[BrokerPayoutView], tags=["Referral partners"])
async def admin_broker_payouts_route(
    broker_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(get_admin_actor),
) -> list[BrokerPayoutView]:
    return [BrokerPayoutView(**r) for r in await partners_service.list_payouts(db, broker_id=broker_id)]


@router.post("/api/v1/admin/brokers/{broker_id}/payouts", response_model=BrokerPayoutView, status_code=201, tags=["Referral partners"])
async def record_broker_payout_route(
    broker_id: uuid.UUID,
    body: BrokerPayoutRequest,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(get_admin_actor),
) -> BrokerPayoutView:
    payout = await partners_service.record_payout(
        db,
        actor=actor,
        broker_id=broker_id,
        expected_amount=body.expected_amount,
        method=body.method,
        reference=body.reference,
        notes=body.notes,
    )
    rows = await partners_service.list_payouts(db, broker_id=broker_id)
    match = next((r for r in rows if r["id"] == payout.id), None)
    if match is None:  # pragma: no cover - the row was committed a moment ago
        raise HTTPException(status_code=500, detail="Payout recorded but could not be read back")
    return BrokerPayoutView(**match)


@router.put("/api/v1/admin/venues/{venue_id}/broker", response_model=VenueReferralView, tags=["Referral partners"])
async def admin_set_venue_broker_route(
    venue_id: uuid.UUID,
    body: AdminVenueBrokerRequest,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(get_admin_actor),
) -> VenueReferralView:
    venue = await partners_service.admin_set_venue_broker(db, actor=actor, venue_id=venue_id, broker_id=body.broker_id)
    return await _venue_referral_view(db, venue)


# ===========================================================================
# Broker dashboard — everything scoped to the logged-in broker
# ===========================================================================


def _referral_link(code: str) -> str:
    return f"{settings.public_app_url.rstrip('/')}/owner?ref={code}"


async def _broker_self(db: AsyncSession, actor: User) -> BrokerSelfView:
    data = await partners_service.get_broker(db, actor.id)
    data.pop("notes", None)
    data.pop("suspended_at", None)
    data.pop("created_at", None)
    return BrokerSelfView(**data, referral_link=_referral_link(data["referral_code"]))


@router.get("/api/v1/broker/me", response_model=BrokerSelfView, tags=["Broker"])
async def broker_me_route(
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(get_broker_actor),
) -> BrokerSelfView:
    return await _broker_self(db, actor)


@router.patch("/api/v1/broker/me", response_model=BrokerSelfView, tags=["Broker"])
async def broker_update_me_route(
    body: BrokerSelfUpdateRequest,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(get_broker_actor),
) -> BrokerSelfView:
    """A broker can keep their own business and payout details current.
    Rate, basis, status and code are not in this schema at all, so they
    cannot be sent here."""
    changes = body.model_dump(exclude_unset=True)
    if changes:
        await partners_service.update_broker(db, actor=actor, broker_id=actor.id, changes=changes)
    return await _broker_self(db, actor)


@router.get("/api/v1/broker/venues", response_model=list[ReferredVenueView], tags=["Broker"])
async def broker_venues_route(
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(get_broker_actor),
) -> list[ReferredVenueView]:
    return [ReferredVenueView(**r) for r in await partners_service.list_referred_venues(db, actor.id)]


@router.get("/api/v1/broker/bookings", response_model=list[ReferredBookingView], tags=["Broker"])
async def broker_bookings_route(
    venue_id: uuid.UUID | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(get_broker_actor),
) -> list[ReferredBookingView]:
    rows = await partners_service.list_referred_bookings(db, actor.id, venue_id=venue_id, limit=limit, offset=offset)
    return [ReferredBookingView(**r) for r in rows]


@router.get("/api/v1/broker/commissions", response_model=list[CommissionView], tags=["Broker"])
async def broker_commissions_route(
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(get_broker_actor),
) -> list[CommissionView]:
    return [CommissionView(**r) for r in await partners_service.list_commissions(db, broker_id=actor.id)]


@router.get("/api/v1/broker/payouts", response_model=list[BrokerPayoutView], tags=["Broker"])
async def broker_payouts_route(
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(get_broker_actor),
) -> list[BrokerPayoutView]:
    return [BrokerPayoutView(**r) for r in await partners_service.list_payouts(db, broker_id=actor.id)]


_BROKER_EXPORT_COLUMNS = {
    "venues": [
        ("Venue", "name"),
        ("Category", "category"),
        ("City", "city"),
        ("Status", "status"),
        ("Note from review", "review_note"),
        ("Base price (INR)", "base_price"),
        ("Pricing unit", "unit_type"),
        ("Owner", "owner_name"),
        ("Owner phone", "owner_phone"),
        ("Referred on", "referred_at"),
        ("Bookings (all)", "booking_count"),
        ("Bookings awaiting payment", "awaiting_payment_count"),
        ("Bookings paid", "paid_booking_count"),
        ("Money received (INR)", "amount_received"),
        ("Your commission (INR)", "commission_earned"),
    ],
    "bookings": [
        ("Booking ref", "reference"),
        ("Venue", "venue_name"),
        ("Event date", "event_date"),
        ("Start", "start_time"),
        ("End", "end_time"),
        ("Booking status", "status"),
        ("Booking amount (INR)", "amount"),
        ("Payment", "payment_state"),
        ("Your rate (%)", "commission_rate"),
        ("Your commission (INR)", "commission_amount"),
        ("Commission status", "commission_status"),
        ("Booked on", "created_at"),
    ],
    "commissions": [
        ("Booking ref", "booking_reference"),
        ("Venue", "venue_name"),
        ("Event date", "event_date"),
        ("Rate applies to", "basis"),
        ("Base amount (INR)", "basis_amount"),
        ("Rate (%)", "rate"),
        ("Commission (INR)", "amount"),
        ("Reversed by refund (INR)", "reversed_amount"),
        ("Paid (INR)", "paid_amount"),
        ("Balance due (INR)", "balance_due"),
        ("Status", "status"),
        ("Recorded on", "created_at"),
    ],
    "payouts": [
        ("Amount (INR)", "amount"),
        ("Method", "method"),
        ("Reference", "reference"),
        ("Paid on", "paid_at"),
    ],
}


@router.get("/api/v1/broker/export/{kind}.csv", tags=["Broker"])
async def broker_export_route(
    kind: str,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(get_broker_actor),
) -> Response:
    if kind not in _BROKER_EXPORT_COLUMNS:
        raise HTTPException(status_code=404, detail="Unknown export")
    if kind == "venues":
        rows = await partners_service.list_referred_venues(db, actor.id)
    elif kind == "bookings":
        rows = await partners_service.list_referred_bookings(db, actor.id, limit=5000)
    elif kind == "commissions":
        rows = await partners_service.list_commissions(db, broker_id=actor.id, limit=5000)
    else:
        rows = await partners_service.list_payouts(db, broker_id=actor.id, limit=5000)
    body = records_service.rows_to_csv(rows, _BROKER_EXPORT_COLUMNS[kind])
    return _csv_response(f"groundkart-my-{kind}.csv", body)


# ===========================================================================
# Referral codes — the owner's side
# ===========================================================================


async def _venue_referral_view(db: AsyncSession, venue: Venue) -> VenueReferralView:
    partner_name = None
    if venue.broker_id is not None:
        row = (
            await db.execute(
                select(User.name, BrokerProfile.company_name)
                .join(BrokerProfile, BrokerProfile.user_id == User.id)
                .where(User.id == venue.broker_id)
            )
        ).first()
        if row is not None:
            partner_name = f"{row.name} ({row.company_name})" if row.company_name else row.name
    return VenueReferralView(
        venue_id=venue.id,
        referral_code=venue.referral_code,
        partner_name=partner_name,
        referred_at=venue.referred_at,
        locked=venue.broker_id is not None,
    )


@router.post("/api/v1/referral-codes/check", response_model=ReferralCodeCheckResponse, tags=["Referral codes"])
async def check_referral_code_route(
    body: ReferralCodeRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_role("owner", "admin", "customer")),
) -> ReferralCodeCheckResponse:
    """Lets the listing form confirm a code as the owner types it. Signed-in
    users only, and rate limited per user and per IP — otherwise this would
    be a free way to enumerate every valid code."""
    ip = auth_service.get_client_ip(request)
    await auth_service.check_rate_limit(db, f"ratelimit:refcode:{current_user.id}", max_attempts=20, window_seconds=60)
    await auth_service.check_rate_limit(db, f"ratelimit:refcode:ip:{ip}", max_attempts=40, window_seconds=60)
    found = await partners_service.lookup_code(db, body.code)
    if found is None:
        return ReferralCodeCheckResponse(valid=False)
    user, profile = found
    return ReferralCodeCheckResponse(valid=True, partner_name=profile.company_name or user.name)


@router.get("/api/v1/owner/venues/{venue_id}/referral", response_model=VenueReferralView, tags=["Referral codes"])
async def get_venue_referral_route(
    venue_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_role("owner", "admin")),
) -> VenueReferralView:
    venue = (await db.execute(select(Venue).where(Venue.id == venue_id))).scalar_one_or_none()
    if venue is None or venue.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Venue not found")
    if current_user.role != "admin" and venue.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Venue not found")
    return await _venue_referral_view(db, venue)


@router.put("/api/v1/owner/venues/{venue_id}/referral", response_model=VenueReferralView, tags=["Referral codes"])
async def apply_venue_referral_route(
    venue_id: uuid.UUID,
    body: ReferralCodeRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_role("owner")),
) -> VenueReferralView:
    ip = auth_service.get_client_ip(request)
    await auth_service.check_rate_limit(db, f"ratelimit:refapply:{current_user.id}", max_attempts=10, window_seconds=60)
    await auth_service.check_rate_limit(db, f"ratelimit:refapply:ip:{ip}", max_attempts=30, window_seconds=60)
    venue = await partners_service.owner_apply_referral_code(
        db, venue_id=venue_id, owner_id=current_user.id, raw_code=body.code
    )
    return await _venue_referral_view(db, venue)


# ===========================================================================
# Banners
# ===========================================================================


@router.get("/api/v1/banners", response_model=list[PublicBannerView], tags=["Banners"])
async def list_public_banners_route(
    response: Response,
    placement: str | None = Query(default=None, pattern="^(home_hero|home_strip|search_top)$"),
    db: AsyncSession = Depends(get_db),
) -> list[PublicBannerView]:
    response.headers["Cache-Control"] = "public, max-age=60"
    return [PublicBannerView.model_validate(b) for b in await banners_service.list_public(db, placement)]


@router.get("/api/v1/admin/banners", response_model=list[BannerView], tags=["Banners"])
async def list_admin_banners_route(
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(get_admin_actor),
) -> list[BannerView]:
    return [BannerView.model_validate(b) for b in await banners_service.list_admin(db)]


@router.post("/api/v1/admin/banners", response_model=BannerView, status_code=201, tags=["Banners"])
async def create_banner_route(
    body: BannerCreateRequest,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(get_admin_actor),
) -> BannerView:
    banner = await banners_service.create_banner(db, admin_id=actor.id, data=body.model_dump())
    return BannerView.model_validate(banner)


@router.patch("/api/v1/admin/banners/{banner_id}", response_model=BannerView, tags=["Banners"])
async def update_banner_route(
    banner_id: uuid.UUID,
    body: BannerUpdateRequest,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(get_admin_actor),
) -> BannerView:
    banner = await banners_service.update_banner(
        db, admin_id=actor.id, banner_id=banner_id, changes=body.model_dump(exclude_unset=True)
    )
    return BannerView.model_validate(banner)


@router.post("/api/v1/admin/banners/{banner_id}/image", response_model=BannerView, tags=["Banners"])
async def upload_banner_image_route(
    banner_id: uuid.UUID,
    image: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(get_admin_actor),
    storage=Depends(get_file_storage),
) -> BannerView:
    if image.content_type not in ("image/jpeg", "image/png", "image/webp"):
        raise HTTPException(status_code=422, detail="Upload a JPG, PNG or WebP image")
    if image.size is not None and image.size > MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(status_code=422, detail="Image exceeds the 10MB limit")
    content = await image.read()
    if len(content) > MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(status_code=422, detail="Image exceeds the 10MB limit")
    banner = await banners_service.set_banner_image(
        db, admin_id=actor.id, banner_id=banner_id, content=content, storage=storage
    )
    return BannerView.model_validate(banner)


@router.delete("/api/v1/admin/banners/{banner_id}", status_code=204, tags=["Banners"])
async def delete_banner_route(
    banner_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(get_admin_actor),
) -> Response:
    await banners_service.delete_banner(db, admin_id=actor.id, banner_id=banner_id)
    return Response(status_code=204)


# ===========================================================================
# Records & exports
# ===========================================================================


@router.get("/api/v1/admin/records/exports", response_model=list[ExportInfo], tags=["Records"])
async def list_exports_route(
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(get_admin_actor),
) -> list[ExportInfo]:
    counts = await records_service.summary(db)
    return [
        ExportInfo(kind=kind, title=title, row_count=counts.get(kind, 0), columns=[h for h, _ in columns])
        for kind, (title, _fetch, columns) in records_service.EXPORTS.items()
    ]


@router.get("/api/v1/admin/records/venues", response_model=list[VenueRegisterRow], tags=["Records"])
async def venue_register_route(
    status: str | None = Query(default=None, pattern="^(draft|pending_review|active|suspended|archived)$"),
    city: str | None = Query(default=None, max_length=80),
    broker_id: uuid.UUID | None = Query(default=None),
    referred: bool | None = Query(default=None),
    search: str | None = Query(default=None, max_length=80),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(get_admin_actor),
) -> list[VenueRegisterRow]:
    rows = await records_service.venue_register(
        db,
        status=status,
        city=city,
        broker_id=broker_id,
        referred=referred,
        search=search,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset,
    )
    return [VenueRegisterRow(**r) for r in rows]


@router.get("/api/v1/admin/records/bookings", response_model=list[BookingRegisterRow], tags=["Records"])
async def booking_register_route(
    status: str | None = Query(default=None, max_length=32),
    venue_id: uuid.UUID | None = Query(default=None),
    broker_id: uuid.UUID | None = Query(default=None),
    payment: str | None = Query(default=None, pattern="^(received|awaiting)$"),
    search: str | None = Query(default=None, max_length=80),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    date_basis: str = Query(default="booked", pattern="^(booked|event)$"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(get_admin_actor),
) -> list[BookingRegisterRow]:
    rows = await records_service.booking_register(
        db,
        status=status,
        venue_id=venue_id,
        broker_id=broker_id,
        payment=payment,
        search=search,
        date_from=date_from,
        date_to=date_to,
        date_basis=date_basis,
        limit=limit,
        offset=offset,
    )
    return [BookingRegisterRow(**r) for r in rows]


@router.get("/api/v1/admin/records/export/{kind}.csv", tags=["Records"])
async def export_records_route(
    kind: str,
    status: str | None = Query(default=None, max_length=32),
    city: str | None = Query(default=None, max_length=80),
    venue_id: uuid.UUID | None = Query(default=None),
    broker_id: uuid.UUID | None = Query(default=None),
    search: str | None = Query(default=None, max_length=80),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    date_basis: str = Query(default="booked", pattern="^(booked|event)$"),
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(get_admin_actor),
) -> Response:
    """Every export is itself audited: who downloaded which register, with
    which filters, and how many rows left the system."""
    filename, body, row_count = await records_service.export_csv(
        db,
        kind,
        status=status,
        city=city,
        venue_id=venue_id,
        broker_id=broker_id,
        search=search,
        date_from=date_from,
        date_to=date_to,
        date_basis=date_basis,
    )
    await db.rollback()  # end the read transaction before writing the audit row
    from app.models.core import AuditLog

    async with db.begin():
        db.add(
            AuditLog(
                actor_id=actor.id,
                action="records.exported",
                entity_type="export",
                entity_id=None,
                extra_data={
                    "kind": kind,
                    "rows": row_count,
                    "filters": {
                        k: str(v)
                        for k, v in {
                            "status": status,
                            "city": city,
                            "venue_id": venue_id,
                            "broker_id": broker_id,
                            "search": search,
                            "date_from": date_from,
                            "date_to": date_to,
                        }.items()
                        if v is not None
                    },
                },
            )
        )
    return _csv_response(filename, body)


@router.get("/api/v1/admin/venues/{venue_id}/history", response_model=VenueHistoryResponse, tags=["Records"])
async def venue_history_route(
    venue_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(get_admin_actor),
) -> VenueHistoryResponse:
    return VenueHistoryResponse(**await records_service.venue_history(db, venue_id))


# ===========================================================================
# Share pages (Open Graph) — public, read-only, cacheable
# ===========================================================================

_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,119}$")
_SHARE_HEADERS = {"Cache-Control": "public, max-age=600"}


@router.get("/share/venues/{slug}", response_class=HTMLResponse, include_in_schema=False)
async def share_venue_route(slug: str, db: AsyncSession = Depends(get_db)) -> HTMLResponse:
    if not _SLUG_RE.match(slug):
        return HTMLResponse(share_service.default_page("/"), status_code=404, headers=_SHARE_HEADERS)
    html = await share_service.venue_page(db, slug)
    if html is None:
        return HTMLResponse(share_service.default_page("/"), status_code=404, headers=_SHARE_HEADERS)
    return HTMLResponse(html, headers=_SHARE_HEADERS)


@router.get("/share/categories/{slug}", response_class=HTMLResponse, include_in_schema=False)
async def share_category_route(slug: str) -> HTMLResponse:
    if not _SLUG_RE.match(slug):
        return HTMLResponse(share_service.default_page("/"), status_code=404, headers=_SHARE_HEADERS)
    return HTMLResponse(share_service.category_page(slug), headers=_SHARE_HEADERS)


@router.get("/share", response_class=HTMLResponse, include_in_schema=False)
@router.get("/share/", response_class=HTMLResponse, include_in_schema=False)
async def share_default_route() -> HTMLResponse:
    return HTMLResponse(share_service.default_page("/"), headers=_SHARE_HEADERS)
