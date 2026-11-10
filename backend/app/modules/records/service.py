"""
Records & exports — the operational register.

Two flat registers answer "what has been listed" and "what has been
booked", one row per venue / per booking, with every related fact already
joined in (owner, referral partner, payment, platform commission, broker
commission). The same rows drive the on-screen tables and the CSV export,
so a download always matches what the admin was looking at.

Every export is a read of source-of-truth tables at the time of the
request. Nothing here writes, and nothing is a cached copy that could
drift.

CSV safety: any cell beginning with = + - @ (or a tab / carriage return)
is prefixed with an apostrophe. Venue names, notes and customer names are
user-supplied; without this, opening an export in Excel could execute a
formula someone typed into a form field.
"""
from __future__ import annotations

import csv
import io
import uuid
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from typing import Any, Awaitable, Callable

from fastapi import HTTPException
from sqlalchemy import Text, and_, case, cast, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.models.core import (
    AuditLog,
    Booking,
    BrokerCommission,
    BrokerPayout,
    BrokerProfile,
    InventoryUnit,
    Payment,
    Payout,
    User,
    Venue,
    VenueMedia,
)
from app.modules.partners.service import commission_status, today_ist

EXPORT_ROW_CAP = 50_000
_PAID = ("success", "refunded")


def _day_start(d: date | None) -> datetime | None:
    return datetime.combine(d, time.min, tzinfo=timezone.utc) if d else None


def _day_end(d: date | None) -> datetime | None:
    return datetime.combine(d + timedelta(days=1), time.min, tzinfo=timezone.utc) if d else None


# ---------------------------------------------------------------------------
# Venue register
# ---------------------------------------------------------------------------


async def venue_register(
    session: AsyncSession,
    *,
    status: str | None = None,
    city: str | None = None,
    broker_id: uuid.UUID | None = None,
    referred: bool | None = None,
    search: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[dict]:
    Owner = aliased(User)
    Broker = aliased(User)

    bookings_sq = (
        select(
            Booking.venue_id.label("venue_id"),
            func.count(Booking.id).label("booking_count"),
            func.count(case((Booking.status.in_(("confirmed", "completed", "upcoming", "in_progress")), 1))).label(
                "confirmed_count"
            ),
        )
        .group_by(Booking.venue_id)
        .subquery()
    )
    money_sq = (
        select(
            Booking.venue_id.label("venue_id"),
            func.coalesce(func.sum(Payment.amount - func.coalesce(Payment.refund_amount, 0)), 0).label("received"),
            func.coalesce(func.sum(Payment.commission_amount), 0).label("platform_commission"),
        )
        .join(Payment, Payment.booking_id == Booking.id)
        .where(Payment.status.in_(_PAID))
        .group_by(Booking.venue_id)
        .subquery()
    )
    approved_sq = (
        select(AuditLog.entity_id.label("venue_id"), func.max(AuditLog.created_at).label("approved_at"))
        .where(AuditLog.entity_type == "venue", AuditLog.action == "venue.approved")
        .group_by(AuditLog.entity_id)
        .subquery()
    )
    media_sq = (
        select(VenueMedia.venue_id.label("venue_id"), func.count(VenueMedia.id).label("media_count"))
        .group_by(VenueMedia.venue_id)
        .subquery()
    )

    query = (
        select(
            Venue,
            Owner.name.label("owner_name"),
            Owner.phone.label("owner_phone"),
            Owner.email.label("owner_email"),
            Broker.name.label("broker_name"),
            bookings_sq.c.booking_count,
            bookings_sq.c.confirmed_count,
            money_sq.c.received,
            money_sq.c.platform_commission,
            approved_sq.c.approved_at,
            media_sq.c.media_count,
        )
        .join(Owner, Owner.id == Venue.owner_id)
        .outerjoin(Broker, Broker.id == Venue.broker_id)
        .outerjoin(bookings_sq, bookings_sq.c.venue_id == Venue.id)
        .outerjoin(money_sq, money_sq.c.venue_id == Venue.id)
        .outerjoin(approved_sq, approved_sq.c.venue_id == Venue.id)
        .outerjoin(media_sq, media_sq.c.venue_id == Venue.id)
        .where(Venue.deleted_at.is_(None))
        .order_by(Venue.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    if status:
        query = query.where(Venue.status == status)
    if city:
        query = query.where(Venue.city.ilike(city.strip()))
    if broker_id is not None:
        query = query.where(Venue.broker_id == broker_id)
    if referred is True:
        query = query.where(Venue.broker_id.is_not(None))
    elif referred is False:
        query = query.where(Venue.broker_id.is_(None))
    if search:
        like = f"%{search.strip()}%"
        query = query.where(
            or_(Venue.name.ilike(like), Venue.city.ilike(like), Owner.name.ilike(like), Owner.phone.ilike(like))
        )
    if date_from:
        query = query.where(Venue.created_at >= _day_start(date_from))
    if date_to:
        query = query.where(Venue.created_at < _day_end(date_to))

    out = []
    for r in (await session.execute(query)).all():
        v = r.Venue
        out.append(
            {
                "id": v.id,
                "name": v.name,
                "slug": v.slug,
                "category": v.category,
                "city": v.city,
                "state": v.state,
                "address": v.address,
                "capacity": v.capacity,
                "unit_type": v.unit_type,
                "base_price": v.base_price,
                "status": v.status,
                "status_note": v.rejection_reason or v.suspension_reason,
                "owner_id": v.owner_id,
                "owner_name": r.owner_name,
                "owner_phone": r.owner_phone,
                "owner_email": r.owner_email,
                "broker_id": v.broker_id,
                "broker_name": r.broker_name,
                "referral_code": v.referral_code,
                "referred_at": v.referred_at,
                "listed_at": v.created_at,
                "approved_at": r.approved_at,
                "updated_at": v.updated_at,
                "media_count": int(r.media_count or 0),
                "booking_count": int(r.booking_count or 0),
                "confirmed_booking_count": int(r.confirmed_count or 0),
                "amount_received": Decimal(r.received or 0),
                "platform_commission": Decimal(r.platform_commission or 0),
                "avg_rating": v.avg_rating,
            }
        )
    return out


# ---------------------------------------------------------------------------
# Booking register
# ---------------------------------------------------------------------------


async def booking_register(
    session: AsyncSession,
    *,
    status: str | None = None,
    venue_id: uuid.UUID | None = None,
    broker_id: uuid.UUID | None = None,
    payment: str | None = None,
    search: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    date_basis: str = "booked",
    limit: int = 100,
    offset: int = 0,
) -> list[dict]:
    """date_basis='booked' filters on when the booking was made (the usual
    accounting question); 'event' filters on the date the venue is used."""
    Customer = aliased(User)
    Owner = aliased(User)
    Broker = aliased(User)
    today = today_ist()

    query = (
        select(
            Booking,
            InventoryUnit,
            Venue.city.label("venue_city"),
            Venue.owner_id.label("owner_id"),
            Venue.broker_id.label("venue_broker_id"),
            Owner.name.label("owner_name"),
            Customer.name.label("customer_name"),
            Customer.phone.label("customer_phone"),
            Customer.email.label("customer_email"),
            Payment,
            BrokerCommission,
            Broker.name.label("broker_name"),
        )
        .join(InventoryUnit, InventoryUnit.id == Booking.inventory_unit_id)
        .join(Venue, Venue.id == Booking.venue_id)
        .join(Owner, Owner.id == Venue.owner_id)
        .outerjoin(Customer, Customer.id == Booking.customer_id)
        .outerjoin(Payment, and_(Payment.booking_id == Booking.id, Payment.status.in_(_PAID)))
        .outerjoin(BrokerCommission, BrokerCommission.booking_id == Booking.id)
        .outerjoin(Broker, Broker.id == func.coalesce(BrokerCommission.broker_id, Venue.broker_id))
        .order_by(Booking.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    if status:
        query = query.where(Booking.status == status)
    if venue_id is not None:
        query = query.where(Booking.venue_id == venue_id)
    if broker_id is not None:
        query = query.where(func.coalesce(BrokerCommission.broker_id, Venue.broker_id) == broker_id)
    if payment == "received":
        query = query.where(Payment.id.is_not(None))
    elif payment == "awaiting":
        query = query.where(Payment.id.is_(None), Booking.status == "pending_payment")
    if search:
        like = f"%{search.strip()}%"
        query = query.where(
            or_(
                Booking.venue_name.ilike(like),
                Customer.name.ilike(like),
                Customer.phone.ilike(like),
                Booking.guest_name.ilike(like),
                Booking.guest_phone.ilike(like),
                cast(Booking.id, Text).ilike(like),
            )
        )
    if date_basis == "event":
        if date_from:
            query = query.where(InventoryUnit.date >= date_from)
        if date_to:
            query = query.where(InventoryUnit.date <= date_to)
    else:
        if date_from:
            query = query.where(Booking.created_at >= _day_start(date_from))
        if date_to:
            query = query.where(Booking.created_at < _day_end(date_to))

    out = []
    for r in (await session.execute(query)).all():
        b: Booking = r.Booking
        u: InventoryUnit = r.InventoryUnit
        p: Payment | None = r.Payment
        c: BrokerCommission | None = r.BrokerCommission
        refunded = Decimal(p.refund_amount or 0) if p else Decimal(0)
        received = (p.amount - refunded) if p else Decimal(0)
        platform_commission = Decimal(p.commission_amount or 0) if p else Decimal(0)
        payload = (p.raw_payload or {}) if p else {}
        out.append(
            {
                "id": b.id,
                "reference": str(b.id).split("-")[0].upper(),
                "status": b.status,
                "booked_at": b.created_at,
                "confirmed_at": b.confirmed_at,
                "cancelled_at": b.cancelled_at,
                "cancellation_reason": b.cancellation_reason,
                "venue_id": b.venue_id,
                "venue_name": b.venue_name,
                "venue_category": b.venue_category,
                "venue_city": r.venue_city,
                "owner_id": r.owner_id,
                "owner_name": r.owner_name,
                "event_date": u.date,
                "start_time": u.start_time,
                "end_time": u.end_time,
                "rental_mode": b.rental_mode,
                "guest_count": b.guest_count,
                "customer_type": "account" if b.customer_id else "guest",
                "customer_name": r.customer_name or b.guest_name,
                "customer_phone": r.customer_phone or b.guest_phone,
                "customer_email": r.customer_email or b.guest_email,
                "amount": b.amount,
                "currency": b.currency,
                "payment_received": p is not None,
                "payment_method": p.method if p else None,
                "payment_gateway": p.gateway if p else None,
                "payment_reference": payload.get("reference"),
                "payment_recorded_at": p.created_at if p else None,
                "refund_amount": refunded,
                "amount_received": received,
                "platform_commission": platform_commission,
                "owner_share": (p.amount - platform_commission) if p else Decimal(0),
                "broker_id": c.broker_id if c else r.venue_broker_id,
                "broker_name": r.broker_name,
                "broker_commission_rate": c.rate if c else None,
                "broker_commission": c.net_amount if c else None,
                "broker_commission_status": commission_status(c, today) if c else None,
            }
        )
    return out


# ---------------------------------------------------------------------------
# History timeline
# ---------------------------------------------------------------------------

_EVENT_LABELS = {
    "venue.created": "Listing created",
    "venue.submitted": "Submitted for review",
    "venue.updated": "Details edited",
    "venue.approved": "Approved and published",
    "venue.rejected": "Sent back with changes requested",
    "venue.suspended": "Suspended",
    "venue.reactivated": "Reactivated",
    "venue.archived": "Removed by owner",
    "venue.blocked": "Dates blocked",
    "venue.referral_applied": "Referral code applied",
    "venue.referral_changed_by_admin": "Referral partner changed by admin",
    "homepage_placement.created": "Added to a homepage section",
    "homepage_placement.deleted": "Removed from a homepage section",
}


async def venue_history(session: AsyncSession, venue_id: uuid.UUID) -> dict:
    """Everything that has happened to a listing, oldest first. Built from
    the append-only audit log, so it cannot be edited after the fact."""
    venue = (await session.execute(select(Venue).where(Venue.id == venue_id))).scalar_one_or_none()
    if venue is None:
        raise HTTPException(status_code=404, detail="Venue not found")

    rows = (
        await session.execute(
            select(AuditLog, User.name.label("actor_name"), User.role.label("actor_role"))
            .outerjoin(User, User.id == AuditLog.actor_id)
            .where(AuditLog.entity_type == "venue", AuditLog.entity_id == venue_id)
            .order_by(AuditLog.created_at.asc())
        )
    ).all()

    timeline = [
        {
            "at": log.created_at,
            "action": log.action,
            "label": _EVENT_LABELS.get(log.action, log.action.replace("_", " ").replace(".", ": ")),
            "actor_name": actor_name,
            "actor_role": actor_role,
            "details": log.extra_data or {},
        }
        for log, actor_name, actor_role in rows
    ]
    # Listings created before creation was audited have no 'venue.created'
    # row. Synthesize one from the row's own timestamp so the timeline
    # always starts at the beginning.
    if not any(t["action"] == "venue.created" for t in timeline):
        timeline.insert(
            0,
            {
                "at": venue.created_at,
                "action": "venue.created",
                "label": _EVENT_LABELS["venue.created"],
                "actor_name": None,
                "actor_role": "owner",
                "details": {},
            },
        )

    stats = (
        await session.execute(
            select(
                func.count(Booking.id).label("bookings"),
                func.min(Booking.created_at).label("first_booking_at"),
                func.max(Booking.created_at).label("last_booking_at"),
            ).where(Booking.venue_id == venue_id)
        )
    ).one()
    return {
        "venue_id": venue.id,
        "venue_name": venue.name,
        "status": venue.status,
        "timeline": timeline,
        "booking_count": int(stats.bookings),
        "first_booking_at": stats.first_booking_at,
        "last_booking_at": stats.last_booking_at,
    }


# ---------------------------------------------------------------------------
# Other export sources
# ---------------------------------------------------------------------------


async def _payments_rows(session: AsyncSession, *, date_from: date | None, date_to: date | None, **_: Any) -> list[dict]:
    query = (
        select(Payment, Booking.venue_name, Booking.id.label("booking_id"))
        .join(Booking, Booking.id == Payment.booking_id)
        .order_by(Payment.created_at.desc())
        .limit(EXPORT_ROW_CAP)
    )
    if date_from:
        query = query.where(Payment.created_at >= _day_start(date_from))
    if date_to:
        query = query.where(Payment.created_at < _day_end(date_to))
    out = []
    for p, venue_name, booking_id in (await session.execute(query)).all():
        payload = p.raw_payload or {}
        out.append(
            {
                "id": p.id,
                "booking_reference": str(booking_id).split("-")[0].upper(),
                "booking_id": booking_id,
                "venue_name": venue_name,
                "recorded_at": p.created_at,
                "status": p.status,
                "gateway": p.gateway,
                "method": p.method,
                "reference": payload.get("reference"),
                "amount": p.amount,
                "refund_amount": Decimal(p.refund_amount or 0),
                "commission_rate": p.commission_rate,
                "commission_amount": p.commission_amount,
                "owner_payout_id": p.payout_id,
            }
        )
    return out


async def _owner_payouts_rows(session: AsyncSession, *, date_from: date | None, date_to: date | None, **_: Any) -> list[dict]:
    query = (
        select(Payout, User.name, User.phone)
        .join(User, User.id == Payout.owner_id)
        .order_by(Payout.created_at.desc())
        .limit(EXPORT_ROW_CAP)
    )
    if date_from:
        query = query.where(Payout.created_at >= _day_start(date_from))
    if date_to:
        query = query.where(Payout.created_at < _day_end(date_to))
    return [
        {
            "id": p.id,
            "owner_name": name,
            "owner_phone": phone,
            "period_start": p.period_start,
            "period_end": p.period_end,
            "gross_amount": p.gross_amount,
            "commission_amount": p.commission_amount,
            "net_amount": p.net_amount,
            "status": p.status,
            "payout_reference": p.payout_reference,
            "paid_at": p.paid_at,
            "created_at": p.created_at,
        }
        for p, name, phone in (await session.execute(query)).all()
    ]


async def _users_rows(session: AsyncSession, *, date_from: date | None, date_to: date | None, **_: Any) -> list[dict]:
    query = select(User).where(User.deleted_at.is_(None)).order_by(User.created_at.desc()).limit(EXPORT_ROW_CAP)
    if date_from:
        query = query.where(User.created_at >= _day_start(date_from))
    if date_to:
        query = query.where(User.created_at < _day_end(date_to))
    return [
        {
            "id": u.id,
            "name": u.name,
            "phone": u.phone,
            "email": u.email,
            "role": "super_admin" if u.is_super_admin else u.role,
            "verified": u.is_verified,
            "suspended": u.suspended_at is not None,
            "suspension_reason": u.suspension_reason,
            "joined_at": u.created_at,
        }
        for u in (await session.execute(query)).scalars().all()
    ]


async def _audit_rows(session: AsyncSession, *, date_from: date | None, date_to: date | None, **_: Any) -> list[dict]:
    query = (
        select(AuditLog, User.name)
        .outerjoin(User, User.id == AuditLog.actor_id)
        .order_by(AuditLog.created_at.desc())
        .limit(EXPORT_ROW_CAP)
    )
    if date_from:
        query = query.where(AuditLog.created_at >= _day_start(date_from))
    if date_to:
        query = query.where(AuditLog.created_at < _day_end(date_to))
    return [
        {
            "at": log.created_at,
            "actor_name": actor_name,
            "action": log.action,
            "entity_type": log.entity_type,
            "entity_id": log.entity_id,
            "details": log.extra_data,
        }
        for log, actor_name in (await session.execute(query)).all()
    ]


async def _brokers_rows(session: AsyncSession, **_: Any) -> list[dict]:
    from app.modules.partners import service as partners_service

    rows = await partners_service.list_brokers(session)
    return [
        {
            **{k: v for k, v in r.items() if k != "wallet"},
            "earned": r["wallet"]["earned"],
            "pending": r["wallet"]["pending"],
            "payable": r["wallet"]["payable"],
            "paid": r["wallet"]["paid"],
            "reversed": r["wallet"]["reversed"],
            "account_suspended": r["suspended_at"] is not None,
        }
        for r in rows
    ]


async def _broker_commissions_rows(
    session: AsyncSession, *, broker_id: uuid.UUID | None = None, date_from: date | None, date_to: date | None, **_: Any
) -> list[dict]:
    from app.modules.partners import service as partners_service

    rows = await partners_service.list_commissions(session, broker_id=broker_id, limit=EXPORT_ROW_CAP)
    if date_from:
        rows = [r for r in rows if r["created_at"] >= _day_start(date_from)]
    if date_to:
        rows = [r for r in rows if r["created_at"] < _day_end(date_to)]
    return rows


async def _broker_payouts_rows(session: AsyncSession, *, broker_id: uuid.UUID | None = None, **_: Any) -> list[dict]:
    from app.modules.partners import service as partners_service

    return await partners_service.list_payouts(session, broker_id=broker_id, limit=EXPORT_ROW_CAP)


async def _venue_rows(session: AsyncSession, **filters: Any) -> list[dict]:
    allowed = {k: filters.get(k) for k in ("status", "city", "broker_id", "search", "date_from", "date_to")}
    return await venue_register(session, **allowed, limit=EXPORT_ROW_CAP, offset=0)


async def _booking_rows(session: AsyncSession, **filters: Any) -> list[dict]:
    allowed = {k: filters.get(k) for k in ("status", "venue_id", "broker_id", "search", "date_from", "date_to")}
    return await booking_register(
        session, **allowed, date_basis=filters.get("date_basis") or "booked", limit=EXPORT_ROW_CAP, offset=0
    )


Column = tuple[str, str]  # (CSV header, row key)

EXPORTS: dict[str, tuple[str, Callable[..., Awaitable[list[dict]]], list[Column]]] = {
    "venues": (
        "Venue register",
        _venue_rows,
        [
            ("Venue ID", "id"),
            ("Venue", "name"),
            ("Category", "category"),
            ("City", "city"),
            ("State", "state"),
            ("Address", "address"),
            ("Capacity", "capacity"),
            ("Pricing unit", "unit_type"),
            ("Base price (INR)", "base_price"),
            ("Status", "status"),
            ("Status note", "status_note"),
            ("Owner", "owner_name"),
            ("Owner phone", "owner_phone"),
            ("Owner email", "owner_email"),
            ("Referral partner", "broker_name"),
            ("Referral code", "referral_code"),
            ("Referred on", "referred_at"),
            ("Listed on", "listed_at"),
            ("Approved on", "approved_at"),
            ("Last updated", "updated_at"),
            ("Photos and videos", "media_count"),
            ("Bookings (all)", "booking_count"),
            ("Bookings (confirmed)", "confirmed_booking_count"),
            ("Amount received (INR)", "amount_received"),
            ("Platform commission (INR)", "platform_commission"),
            ("Average rating", "avg_rating"),
        ],
    ),
    "bookings": (
        "Booking register",
        _booking_rows,
        [
            ("Booking ref", "reference"),
            ("Booking ID", "id"),
            ("Status", "status"),
            ("Booked on", "booked_at"),
            ("Venue", "venue_name"),
            ("Category", "venue_category"),
            ("City", "venue_city"),
            ("Owner", "owner_name"),
            ("Event date", "event_date"),
            ("Start", "start_time"),
            ("End", "end_time"),
            ("Rental mode", "rental_mode"),
            ("Guests", "guest_count"),
            ("Customer type", "customer_type"),
            ("Customer", "customer_name"),
            ("Customer phone", "customer_phone"),
            ("Customer email", "customer_email"),
            ("Booking amount (INR)", "amount"),
            ("Payment received", "payment_received"),
            ("Payment method", "payment_method"),
            ("Payment reference", "payment_reference"),
            ("Payment recorded on", "payment_recorded_at"),
            ("Refunded (INR)", "refund_amount"),
            ("Net received (INR)", "amount_received"),
            ("Platform commission (INR)", "platform_commission"),
            ("Owner share (INR)", "owner_share"),
            ("Referral partner", "broker_name"),
            ("Partner rate (%)", "broker_commission_rate"),
            ("Partner commission (INR)", "broker_commission"),
            ("Partner commission status", "broker_commission_status"),
            ("Confirmed on", "confirmed_at"),
            ("Cancelled on", "cancelled_at"),
            ("Cancellation reason", "cancellation_reason"),
        ],
    ),
    "payments": (
        "Payments",
        _payments_rows,
        [
            ("Payment ID", "id"),
            ("Booking ref", "booking_reference"),
            ("Venue", "venue_name"),
            ("Recorded on", "recorded_at"),
            ("Status", "status"),
            ("Channel", "gateway"),
            ("Method", "method"),
            ("Reference", "reference"),
            ("Amount (INR)", "amount"),
            ("Refunded (INR)", "refund_amount"),
            ("Commission rate (%)", "commission_rate"),
            ("Commission (INR)", "commission_amount"),
            ("Owner payout ID", "owner_payout_id"),
        ],
    ),
    "owner_payouts": (
        "Owner payouts",
        _owner_payouts_rows,
        [
            ("Payout ID", "id"),
            ("Owner", "owner_name"),
            ("Owner phone", "owner_phone"),
            ("Period start", "period_start"),
            ("Period end", "period_end"),
            ("Gross (INR)", "gross_amount"),
            ("Commission (INR)", "commission_amount"),
            ("Net payable (INR)", "net_amount"),
            ("Status", "status"),
            ("Transfer reference", "payout_reference"),
            ("Paid on", "paid_at"),
            ("Created on", "created_at"),
        ],
    ),
    "brokers": (
        "Referral partners",
        _brokers_rows,
        [
            ("Partner ID", "id"),
            ("Name", "name"),
            ("Phone", "phone"),
            ("Email", "email"),
            ("Company", "company_name"),
            ("City", "city"),
            ("Referral code", "referral_code"),
            ("Rate (%)", "commission_percent"),
            ("Rate applies to", "commission_basis"),
            ("Status", "status"),
            ("Account suspended", "account_suspended"),
            ("Venues referred", "venue_count"),
            ("Venues live", "active_venue_count"),
            ("Earned (INR)", "earned"),
            ("Pending (INR)", "pending"),
            ("Payable (INR)", "payable"),
            ("Paid (INR)", "paid"),
            ("Reversed by refunds (INR)", "reversed"),
            ("Added on", "created_at"),
        ],
    ),
    "broker_commissions": (
        "Partner commissions",
        _broker_commissions_rows,
        [
            ("Commission ID", "id"),
            ("Partner", "broker_name"),
            ("Venue", "venue_name"),
            ("Booking ref", "booking_reference"),
            ("Event date", "event_date"),
            ("Rate applies to", "basis"),
            ("Base amount (INR)", "basis_amount"),
            ("Rate (%)", "rate"),
            ("Commission (INR)", "amount"),
            ("Reversed (INR)", "reversed_amount"),
            ("Paid (INR)", "paid_amount"),
            ("Balance due (INR)", "balance_due"),
            ("Status", "status"),
            ("Recorded on", "created_at"),
        ],
    ),
    "broker_payouts": (
        "Partner payouts",
        _broker_payouts_rows,
        [
            ("Payout ID", "id"),
            ("Partner", "broker_name"),
            ("Amount (INR)", "amount"),
            ("Method", "method"),
            ("Reference", "reference"),
            ("Notes", "notes"),
            ("Paid on", "paid_at"),
        ],
    ),
    "users": (
        "Users",
        _users_rows,
        [
            ("User ID", "id"),
            ("Name", "name"),
            ("Phone", "phone"),
            ("Email", "email"),
            ("Role", "role"),
            ("Verified", "verified"),
            ("Suspended", "suspended"),
            ("Suspension reason", "suspension_reason"),
            ("Joined on", "joined_at"),
        ],
    ),
    "audit_log": (
        "Audit log",
        _audit_rows,
        [
            ("When", "at"),
            ("Who", "actor_name"),
            ("Action", "action"),
            ("Record type", "entity_type"),
            ("Record ID", "entity_id"),
            ("Details", "details"),
        ],
    ),
}

_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def _cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, datetime):
        return value.astimezone(timezone(timedelta(hours=5, minutes=30))).strftime("%Y-%m-%d %H:%M")
    if isinstance(value, (date, time)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return f"{value:.2f}"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, dict):
        import json

        text = json.dumps(value, default=str, ensure_ascii=False, sort_keys=True)
    else:
        text = str(value)
    if text.startswith(_FORMULA_PREFIXES):
        text = "'" + text
    return text


def rows_to_csv(rows: list[dict], columns: list[Column]) -> str:
    """UTF-8 with BOM so Excel opens ₹ and Devanagari names correctly.
    Timestamps are written in IST; money as plain two-decimal numbers."""
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\r\n")
    writer.writerow([header for header, _ in columns])
    for row in rows:
        writer.writerow([_cell(row.get(key)) for _, key in columns])
    return "﻿" + buf.getvalue()


async def export_csv(session: AsyncSession, kind: str, **filters: Any) -> tuple[str, str, int]:
    """Returns (filename, csv_text, row_count)."""
    if kind not in EXPORTS:
        raise HTTPException(status_code=404, detail="Unknown export")
    _title, fetch, columns = EXPORTS[kind]
    rows = await fetch(session, **filters)
    stamp = datetime.now(timezone(timedelta(hours=5, minutes=30))).strftime("%Y%m%d-%H%M")
    return f"groundkart-{kind.replace('_', '-')}-{stamp}.csv", rows_to_csv(rows, columns), len(rows)


async def summary(session: AsyncSession) -> dict:
    """Row counts per export, so the Records screen can show what each
    download will contain before it is requested."""
    async def count(model, *where) -> int:
        q = select(func.count()).select_from(model)
        for w in where:
            q = q.where(w)
        return int((await session.execute(q)).scalar_one())

    return {
        "venues": await count(Venue, Venue.deleted_at.is_(None)),
        "bookings": await count(Booking),
        "payments": await count(Payment),
        "owner_payouts": await count(Payout),
        "brokers": await count(BrokerProfile),
        "broker_commissions": await count(BrokerCommission),
        "broker_payouts": await count(BrokerPayout),
        "users": await count(User, User.deleted_at.is_(None)),
        "audit_log": await count(AuditLog),
    }
