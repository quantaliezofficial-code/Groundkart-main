"""
Referral partners ("brokers").

A broker is a field partner who brings venue owners onto GroundKart. Each
one has a referral code. When an owner enters that code while listing, the
venue is attributed to the broker, and every payment later confirmed for a
booking at that venue earns the broker a commission at the rate the super
admin set for them.

Rules that matter, in one place:

* Brokers are created from the admin console only (admin or super admin).
  There is no self-signup path to this role.
* Only the super admin can set or change a broker's rate and basis. An
  admin adding a broker gets the platform default rate.
* A referral code can be applied by the owner while the venue has never
  been attributed. Once set it is fixed for the owner; only an admin can
  correct it. This stops a commission stream being redirected after the
  fact.
* The rate is snapshotted on each commission row at the moment the payment
  is confirmed. Changing a broker's rate never rewrites history.
* Refunds reverse commission proportionally, on the same row, in a
  separate column. Nothing is overwritten or deleted.
* A commission becomes payable the day after the event date.
"""
from __future__ import annotations

import re
import secrets
import uuid
from datetime import date, datetime, timezone
from decimal import ROUND_HALF_UP, Decimal
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.core import (
    AuditLog,
    Booking,
    BrokerCommission,
    BrokerPayout,
    BrokerPayoutItem,
    BrokerProfile,
    InventoryUnit,
    Payment,
    User,
    Venue,
)
from app.modules.auth.security import hash_password
from app.modules.notifications.service import notify

IST = ZoneInfo("Asia/Kolkata")
ZERO = Decimal("0.00")
CENT = Decimal("0.01")

# No 0/O, 1/I/L — a code gets read out over the phone and typed on a
# mobile keyboard, and those are the characters people get wrong.
_CODE_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
_CODE_RE = re.compile(r"^[A-Z0-9][A-Z0-9-]{3,23}$")

COMMISSION_BASES = ("booking_amount", "platform_commission")


def today_ist() -> date:
    return datetime.now(IST).date()


def normalize_code(raw: str | None) -> str | None:
    """Uppercase, strip whitespace. Returns None for empty input so callers
    can treat "no code" uniformly."""
    if raw is None:
        return None
    cleaned = re.sub(r"\s+", "", raw).upper()
    return cleaned or None


def _generate_code(name: str) -> str:
    letters = re.sub(r"[^A-Za-z]", "", name).upper()
    prefix = (letters[:3] or "GKP").ljust(3, "X")
    suffix = "".join(secrets.choice(_CODE_ALPHABET) for _ in range(4))
    return f"GK-{prefix}-{suffix}"


async def _unique_code(session: AsyncSession, name: str) -> str:
    for _ in range(12):
        code = _generate_code(name)
        exists = (
            await session.execute(select(BrokerProfile.user_id).where(BrokerProfile.referral_code == code))
        ).scalar_one_or_none()
        if exists is None:
            return code
    raise HTTPException(status_code=500, detail="Could not generate a unique referral code. Try again.")


def _money(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def commission_status(row: BrokerCommission, today: date | None = None) -> str:
    """Derived, never stored — so it can't drift from the amounts.

    reversed   the whole commission was taken back by a refund
    paid       settled in full
    adjustment the broker was paid and a later refund took some back;
               the shortfall comes off the next settlement
    payable    the event has happened and money is due
    pending    payment received, event has not happened yet
    """
    today = today or today_ist()
    balance = row.amount - row.reversed_amount - row.paid_amount
    if row.amount > ZERO and row.reversed_amount >= row.amount and row.paid_amount == ZERO:
        return "reversed"
    if balance < ZERO:
        return "adjustment"
    if balance == ZERO:
        return "paid" if row.paid_amount > ZERO else ("reversed" if row.reversed_amount > ZERO else "paid")
    if row.event_date < today:
        return "payable"
    return "pending"


# ---------------------------------------------------------------------------
# Broker accounts
# ---------------------------------------------------------------------------


async def create_broker(
    session: AsyncSession,
    *,
    actor: User,
    name: str,
    phone: str,
    email: str | None,
    commission_percent: Decimal | None = None,
    commission_basis: str | None = None,
    company_name: str | None = None,
    city: str | None = None,
    payout_method: str | None = None,
    payout_details: str | None = None,
    notes: str | None = None,
) -> tuple[User, BrokerProfile]:
    """Creates the login and the broker profile together. The account gets
    an unusable random password; the caller issues a one-time set-password
    link (the same mechanism as an admin-initiated reset) so no password is
    ever chosen or seen by staff."""
    from app.modules.core.config_service import get_system_config

    if commission_basis is not None and commission_basis not in COMMISSION_BASES:
        raise HTTPException(status_code=422, detail="Unknown commission basis")

    try:
        async with session.begin():
            config = await get_system_config(session)
            conditions = [User.phone == phone]
            if email:
                conditions.append(User.email == email)
            existing = (await session.execute(select(User).where(or_(*conditions)))).scalars().first()
            if existing is not None:
                raise HTTPException(
                    status_code=409, detail="An account with this phone or email already exists"
                )

            # Rate: an admin always gets the platform default. Only the super
            # admin's explicit value is honoured.
            if actor.is_super_admin and commission_percent is not None:
                rate = commission_percent
            else:
                rate = Decimal(config.default_broker_commission_percent)
            basis = commission_basis if (actor.is_super_admin and commission_basis) else "booking_amount"

            user = User(
                name=name,
                email=email,
                phone=phone,
                password_hash=hash_password(secrets.token_urlsafe(32)),
                role="broker",
                is_verified=True,
                must_change_password=True,
                created_by=actor.id,
            )
            session.add(user)
            await session.flush()

            profile = BrokerProfile(
                user_id=user.id,
                referral_code=await _unique_code(session, name),
                commission_percent=rate,
                commission_basis=basis,
                status="active",
                company_name=company_name,
                city=city,
                payout_method=payout_method,
                payout_details=payout_details,
                notes=notes,
                created_by=actor.id,
            )
            session.add(profile)
            session.add(
                AuditLog(
                    actor_id=actor.id,
                    action="broker.created",
                    entity_type="broker",
                    entity_id=user.id,
                    extra_data={
                        "name": name,
                        "referral_code": profile.referral_code,
                        "commission_percent": str(rate),
                        "commission_basis": basis,
                    },
                )
            )
            await session.flush()
    except IntegrityError:
        raise HTTPException(status_code=409, detail="An account with this phone or email already exists")
    return user, profile


async def _load_broker(session: AsyncSession, broker_id: uuid.UUID, *, lock: bool = False) -> tuple[User, BrokerProfile]:
    query = (
        select(User, BrokerProfile)
        .join(BrokerProfile, BrokerProfile.user_id == User.id)
        .where(User.id == broker_id, User.deleted_at.is_(None))
    )
    if lock:
        query = query.with_for_update(of=BrokerProfile)
    row = (await session.execute(query)).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Broker not found")
    return row[0], row[1]


async def update_broker(
    session: AsyncSession, *, actor: User, broker_id: uuid.UUID, changes: dict
) -> tuple[User, BrokerProfile]:
    """Contact and payout details: any admin. Rate, basis and status: super
    admin only — attempting them as a regular admin is a 403, not a silent
    ignore, so the UI can never appear to have saved a rate it didn't."""
    restricted = {"commission_percent", "commission_basis", "status"}
    touched_restricted = restricted.intersection(k for k, v in changes.items() if v is not None)
    if touched_restricted and not actor.is_super_admin:
        raise HTTPException(
            status_code=403,
            detail="Only the super admin can change a broker's commission terms or status",
        )
    if changes.get("commission_basis") is not None and changes["commission_basis"] not in COMMISSION_BASES:
        raise HTTPException(status_code=422, detail="Unknown commission basis")
    if changes.get("status") is not None and changes["status"] not in ("active", "paused"):
        raise HTTPException(status_code=422, detail="Status must be 'active' or 'paused'")

    async with session.begin():
        user, profile = await _load_broker(session, broker_id, lock=True)
        before: dict = {}
        after: dict = {}

        if changes.get("name") is not None and changes["name"] != user.name:
            before["name"], after["name"] = user.name, changes["name"]
            user.name = changes["name"]

        for field in (
            "commission_percent",
            "commission_basis",
            "status",
            "company_name",
            "city",
            "payout_method",
            "payout_details",
            "notes",
        ):
            if field not in changes or changes[field] is None:
                continue
            new_value = changes[field]
            old_value = getattr(profile, field)
            if isinstance(old_value, Decimal):
                new_value = Decimal(str(new_value))
            if old_value != new_value:
                before[field] = str(old_value) if old_value is not None else None
                after[field] = str(new_value)
                setattr(profile, field, new_value)

        if after:
            profile.updated_at = datetime.now(timezone.utc)
            # payout_details can hold a UPI id / account note — record THAT
            # it changed, not the value itself.
            for sensitive in ("payout_details",):
                if sensitive in after:
                    before[sensitive], after[sensitive] = "(changed)", "(changed)"
            session.add(
                AuditLog(
                    actor_id=actor.id,
                    action="broker.updated",
                    entity_type="broker",
                    entity_id=user.id,
                    extra_data={"before": before, "after": after},
                )
            )
            if "commission_percent" in after or "commission_basis" in after:
                session.add_all(
                    notify(
                        user.id,
                        "broker_terms_updated",
                        "Your referral commission terms were updated. New bookings will use the new terms.",
                        entity_type="broker",
                        entity_id=user.id,
                    )
                )
    return user, profile


async def regenerate_referral_code(session: AsyncSession, *, actor: User, broker_id: uuid.UUID) -> BrokerProfile:
    """Super admin only. Existing venue attributions are untouched — they
    point at the broker, not at the code text — so this only changes what
    new owners must type."""
    if not actor.is_super_admin:
        raise HTTPException(status_code=403, detail="Only the super admin can regenerate a referral code")
    async with session.begin():
        user, profile = await _load_broker(session, broker_id, lock=True)
        old = profile.referral_code
        profile.referral_code = await _unique_code(session, user.name)
        profile.updated_at = datetime.now(timezone.utc)
        session.add(
            AuditLog(
                actor_id=actor.id,
                action="broker.code_regenerated",
                entity_type="broker",
                entity_id=user.id,
                extra_data={"old_code": old, "new_code": profile.referral_code},
            )
        )
    return profile


def _wallet_columns(today: date):
    balance = BrokerCommission.amount - BrokerCommission.reversed_amount - BrokerCommission.paid_amount
    matured = BrokerCommission.event_date < today
    return dict(
        earned=func.coalesce(func.sum(BrokerCommission.amount - BrokerCommission.reversed_amount), 0),
        reversed=func.coalesce(func.sum(BrokerCommission.reversed_amount), 0),
        paid=func.coalesce(func.sum(BrokerCommission.paid_amount), 0),
        payable=func.coalesce(func.sum(case((matured, balance), else_=0)), 0),
        pending=func.coalesce(func.sum(case((matured, 0), else_=balance)), 0),
        bookings=func.count(BrokerCommission.id),
    )


async def get_wallet(session: AsyncSession, broker_id: uuid.UUID) -> dict:
    cols = _wallet_columns(today_ist())
    row = (
        await session.execute(
            select(*[v.label(k) for k, v in cols.items()]).where(BrokerCommission.broker_id == broker_id)
        )
    ).one()
    return {
        "earned": _money(Decimal(row.earned)),
        "reversed": _money(Decimal(row.reversed)),
        "paid": _money(Decimal(row.paid)),
        "payable": _money(Decimal(row.payable)),
        "pending": _money(Decimal(row.pending)),
        "commission_count": int(row.bookings),
    }


async def list_brokers(
    session: AsyncSession, *, search: str | None = None, status: str | None = None
) -> list[dict]:
    """Every broker with the numbers an admin needs to scan the list: how
    many venues they brought, and where their money stands."""
    query = (
        select(User, BrokerProfile)
        .join(BrokerProfile, BrokerProfile.user_id == User.id)
        .where(User.deleted_at.is_(None))
        .order_by(User.created_at.desc())
    )
    if status in ("active", "paused"):
        query = query.where(BrokerProfile.status == status)
    if search:
        like = f"%{search.strip()}%"
        query = query.where(
            or_(
                User.name.ilike(like),
                User.phone.ilike(like),
                User.email.ilike(like),
                BrokerProfile.referral_code.ilike(like),
                BrokerProfile.company_name.ilike(like),
            )
        )
    rows = (await session.execute(query)).all()
    if not rows:
        return []

    broker_ids = [u.id for u, _ in rows]
    venue_counts = {
        r.broker_id: (int(r.total), int(r.active))
        for r in (
            await session.execute(
                select(
                    Venue.broker_id,
                    func.count(Venue.id).label("total"),
                    func.count(case((Venue.status == "active", 1))).label("active"),
                )
                .where(Venue.broker_id.in_(broker_ids), Venue.deleted_at.is_(None))
                .group_by(Venue.broker_id)
            )
        ).all()
    }
    cols = _wallet_columns(today_ist())
    wallets = {
        r.broker_id: r
        for r in (
            await session.execute(
                select(BrokerCommission.broker_id, *[v.label(k) for k, v in cols.items()])
                .where(BrokerCommission.broker_id.in_(broker_ids))
                .group_by(BrokerCommission.broker_id)
            )
        ).all()
    }

    out: list[dict] = []
    for user, profile in rows:
        total, active = venue_counts.get(user.id, (0, 0))
        w = wallets.get(user.id)
        out.append(
            _broker_dict(
                user,
                profile,
                venue_count=total,
                active_venue_count=active,
                wallet={
                    "earned": _money(Decimal(w.earned)) if w else ZERO,
                    "reversed": _money(Decimal(w.reversed)) if w else ZERO,
                    "paid": _money(Decimal(w.paid)) if w else ZERO,
                    "payable": _money(Decimal(w.payable)) if w else ZERO,
                    "pending": _money(Decimal(w.pending)) if w else ZERO,
                    "commission_count": int(w.bookings) if w else 0,
                },
            )
        )
    return out


def _broker_dict(user: User, profile: BrokerProfile, *, venue_count: int, active_venue_count: int, wallet: dict) -> dict:
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "phone": user.phone,
        "suspended_at": user.suspended_at,
        "referral_code": profile.referral_code,
        "commission_percent": profile.commission_percent,
        "commission_basis": profile.commission_basis,
        "status": profile.status,
        "company_name": profile.company_name,
        "city": profile.city,
        "payout_method": profile.payout_method,
        "payout_details": profile.payout_details,
        "notes": profile.notes,
        "created_at": profile.created_at,
        "venue_count": venue_count,
        "active_venue_count": active_venue_count,
        "wallet": wallet,
    }


async def get_broker(session: AsyncSession, broker_id: uuid.UUID) -> dict:
    user, profile = await _load_broker(session, broker_id)
    counts = (
        await session.execute(
            select(
                func.count(Venue.id).label("total"),
                func.count(case((Venue.status == "active", 1))).label("active"),
            ).where(Venue.broker_id == broker_id, Venue.deleted_at.is_(None))
        )
    ).one()
    wallet = await get_wallet(session, broker_id)
    return _broker_dict(
        user, profile, venue_count=int(counts.total), active_venue_count=int(counts.active), wallet=wallet
    )


# ---------------------------------------------------------------------------
# Referral codes and venue attribution
# ---------------------------------------------------------------------------


async def lookup_code(session: AsyncSession, raw_code: str) -> tuple[User, BrokerProfile] | None:
    """Returns the broker for a usable code, or None. "Usable" = the code
    exists, the broker is active, and the account is neither suspended nor
    deleted. Deliberately one undifferentiated None for every failure so a
    caller can't distinguish "no such code" from "paused broker"."""
    code = normalize_code(raw_code)
    if code is None or not _CODE_RE.match(code):
        return None
    row = (
        await session.execute(
            select(User, BrokerProfile)
            .join(BrokerProfile, BrokerProfile.user_id == User.id)
            .where(
                BrokerProfile.referral_code == code,
                BrokerProfile.status == "active",
                User.deleted_at.is_(None),
                User.suspended_at.is_(None),
            )
        )
    ).first()
    return (row[0], row[1]) if row else None


async def apply_referral_code_in_tx(
    session: AsyncSession, venue: Venue, raw_code: str | None, actor_id: uuid.UUID
) -> None:
    """Attach a referral code to a venue. Must be called inside an open
    transaction that already holds the venue. No-op for an empty code.
    Raises 422 for an unusable code and 409 if the venue is already
    attributed — an owner can set this once, not change it."""
    code = normalize_code(raw_code)
    if code is None:
        return
    if venue.broker_id is not None:
        if venue.referral_code == code:
            return
        raise HTTPException(
            status_code=409,
            detail="This venue already has a referral partner. Contact support to change it.",
        )
    found = await lookup_code(session, code)
    if found is None:
        raise HTTPException(status_code=422, detail="That referral code isn't valid. Check it and try again.")
    broker_user, profile = found
    if broker_user.id == venue.owner_id:
        raise HTTPException(status_code=422, detail="You can't use your own referral code")

    venue.broker_id = broker_user.id
    venue.referral_code = profile.referral_code
    venue.referred_at = datetime.now(timezone.utc)
    session.add(
        AuditLog(
            actor_id=actor_id,
            action="venue.referral_applied",
            entity_type="venue",
            entity_id=venue.id,
            extra_data={"broker_id": str(broker_user.id), "referral_code": profile.referral_code},
        )
    )
    session.add_all(
        notify(
            broker_user.id,
            "referral_venue_added",
            f"'{venue.name}' was listed with your referral code.",
            entity_type="venue",
            entity_id=venue.id,
        )
    )


async def owner_apply_referral_code(
    session: AsyncSession, *, venue_id: uuid.UUID, owner_id: uuid.UUID, raw_code: str
) -> Venue:
    async with session.begin():
        venue = (
            await session.execute(select(Venue).where(Venue.id == venue_id).with_for_update())
        ).scalar_one_or_none()
        if venue is None or venue.deleted_at is not None or venue.owner_id != owner_id:
            raise HTTPException(status_code=404, detail="Venue not found")
        if normalize_code(raw_code) is None:
            raise HTTPException(status_code=422, detail="Enter a referral code")
        await apply_referral_code_in_tx(session, venue, raw_code, owner_id)
    return venue


async def admin_set_venue_broker(
    session: AsyncSession, *, actor: User, venue_id: uuid.UUID, broker_id: uuid.UUID | None
) -> Venue:
    """Admin correction: attach, change or remove a venue's referral
    partner. Affects commissions on payments confirmed from now on; rows
    already recorded stay with whoever earned them."""
    async with session.begin():
        venue = (
            await session.execute(select(Venue).where(Venue.id == venue_id).with_for_update())
        ).scalar_one_or_none()
        if venue is None or venue.deleted_at is not None:
            raise HTTPException(status_code=404, detail="Venue not found")

        previous = venue.broker_id
        if broker_id is None:
            venue.broker_id = None
            venue.referral_code = None
            venue.referred_at = None
            new_code = None
        else:
            user, profile = await _load_broker(session, broker_id)
            if user.id == venue.owner_id:
                raise HTTPException(status_code=422, detail="A broker can't be the referral partner for their own venue")
            venue.broker_id = user.id
            venue.referral_code = profile.referral_code
            venue.referred_at = datetime.now(timezone.utc)
            new_code = profile.referral_code
            if previous != user.id:
                session.add_all(
                    notify(
                        user.id,
                        "referral_venue_added",
                        f"'{venue.name}' was added to your referred venues.",
                        entity_type="venue",
                        entity_id=venue.id,
                    )
                )

        if previous != venue.broker_id:
            session.add(
                AuditLog(
                    actor_id=actor.id,
                    action="venue.referral_changed_by_admin",
                    entity_type="venue",
                    entity_id=venue.id,
                    extra_data={
                        "previous_broker_id": str(previous) if previous else None,
                        "broker_id": str(venue.broker_id) if venue.broker_id else None,
                        "referral_code": new_code,
                    },
                )
            )
    return venue


# ---------------------------------------------------------------------------
# Commission ledger — called from inside the booking transactions
# ---------------------------------------------------------------------------


async def record_commission_for_payment_in_tx(
    session: AsyncSession, booking: Booking, payment: Payment
) -> BrokerCommission | None:
    """Called by the payment-confirmation path, inside its transaction, so a
    confirmed payment and the commission it earns commit or roll back
    together. Returns None when the venue has no (active) referral
    partner. Idempotent per payment via uq_broker_commission_per_payment."""
    venue = (
        await session.execute(select(Venue.broker_id, Venue.id).where(Venue.id == booking.venue_id))
    ).first()
    if venue is None or venue.broker_id is None:
        return None

    profile = (
        await session.execute(select(BrokerProfile).where(BrokerProfile.user_id == venue.broker_id))
    ).scalar_one_or_none()
    if profile is None or profile.status != "active":
        return None

    already = (
        await session.execute(select(BrokerCommission).where(BrokerCommission.payment_id == payment.id))
    ).scalar_one_or_none()
    if already is not None:
        return already

    if profile.commission_basis == "platform_commission":
        basis_amount = payment.commission_amount or ZERO
    else:
        basis_amount = payment.amount
    amount = _money(basis_amount * (profile.commission_percent / Decimal(100)))

    row = BrokerCommission(
        broker_id=profile.user_id,
        venue_id=booking.venue_id,
        booking_id=booking.id,
        payment_id=payment.id,
        event_date=booking.inventory_unit.date,
        basis=profile.commission_basis,
        basis_amount=basis_amount,
        rate=profile.commission_percent,
        amount=amount,
    )
    session.add(row)
    if amount > ZERO:
        session.add_all(
            notify(
                profile.user_id,
                "referral_commission_earned",
                f"You earned ₹{amount} on a booking at {booking.venue_name}.",
                entity_type="booking",
                entity_id=booking.id,
            )
        )
    return row


async def record_refund_reversal_in_tx(
    session: AsyncSession, payment: Payment, refund_amount: Decimal
) -> BrokerCommission | None:
    """Called by the refund paths, inside their transaction. Takes back the
    same proportion of the commission as the refund is of the payment."""
    row = (
        await session.execute(
            select(BrokerCommission).where(BrokerCommission.payment_id == payment.id).with_for_update()
        )
    ).scalar_one_or_none()
    if row is None or payment.amount <= ZERO or refund_amount <= ZERO:
        return row
    share = _money(row.amount * (refund_amount / payment.amount))
    row.reversed_amount = min(row.amount, row.reversed_amount + share)
    row.updated_at = datetime.now(timezone.utc)
    return row


# ---------------------------------------------------------------------------
# What a broker (or an admin looking at a broker) can see
# ---------------------------------------------------------------------------


async def list_referred_venues(session: AsyncSession, broker_id: uuid.UUID) -> list[dict]:
    """Each referred venue with its review status, pricing and money so far.
    Owner contact details are included: the broker brought this owner on
    and already has that relationship."""
    venues = (
        await session.execute(
            select(Venue, User.name.label("owner_name"), User.phone.label("owner_phone"))
            .join(User, User.id == Venue.owner_id)
            .where(Venue.broker_id == broker_id, Venue.deleted_at.is_(None))
            .order_by(Venue.referred_at.desc().nullslast(), Venue.created_at.desc())
        )
    ).all()
    if not venues:
        return []
    venue_ids = [v.Venue.id for v in venues]

    booking_stats = {
        r.venue_id: r
        for r in (
            await session.execute(
                select(
                    Booking.venue_id,
                    func.count(Booking.id).label("total"),
                    func.count(case((Booking.status == "pending_payment", 1))).label("awaiting_payment"),
                )
                .where(Booking.venue_id.in_(venue_ids))
                .group_by(Booking.venue_id)
            )
        ).all()
    }
    money_stats = {
        r.venue_id: r
        for r in (
            await session.execute(
                select(
                    BrokerCommission.venue_id,
                    func.count(BrokerCommission.id).label("paid_bookings"),
                    func.coalesce(func.sum(BrokerCommission.basis_amount), 0).label("basis_total"),
                    func.coalesce(
                        func.sum(BrokerCommission.amount - BrokerCommission.reversed_amount), 0
                    ).label("commission"),
                )
                .where(BrokerCommission.venue_id.in_(venue_ids), BrokerCommission.broker_id == broker_id)
                .group_by(BrokerCommission.venue_id)
            )
        ).all()
    }
    received = {
        r.venue_id: Decimal(r.received)
        for r in (
            await session.execute(
                select(
                    Booking.venue_id,
                    func.coalesce(
                        func.sum(Payment.amount - func.coalesce(Payment.refund_amount, 0)), 0
                    ).label("received"),
                )
                .join(Payment, Payment.booking_id == Booking.id)
                .where(Booking.venue_id.in_(venue_ids), Payment.status.in_(("success", "refunded")))
                .group_by(Booking.venue_id)
            )
        ).all()
    }

    out = []
    for row in venues:
        v = row.Venue
        b = booking_stats.get(v.id)
        m = money_stats.get(v.id)
        out.append(
            {
                "id": v.id,
                "name": v.name,
                "slug": v.slug,
                "category": v.category,
                "city": v.city,
                "status": v.status,
                "review_note": v.rejection_reason or v.suspension_reason,
                "base_price": v.base_price,
                "unit_type": v.unit_type,
                "owner_name": row.owner_name,
                "owner_phone": row.owner_phone,
                "referral_code": v.referral_code,
                "referred_at": v.referred_at,
                "created_at": v.created_at,
                "booking_count": int(b.total) if b else 0,
                "awaiting_payment_count": int(b.awaiting_payment) if b else 0,
                "paid_booking_count": int(m.paid_bookings) if m else 0,
                "amount_received": _money(received.get(v.id, ZERO)),
                "commission_earned": _money(Decimal(m.commission)) if m else ZERO,
            }
        )
    return out


async def list_referred_bookings(
    session: AsyncSession,
    broker_id: uuid.UUID,
    *,
    venue_id: uuid.UUID | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[dict]:
    """Bookings at the broker's referred venues, with whether money has been
    received and what the broker earns on each.

    Deliberately no customer name, phone or email: a broker has a
    relationship with the venue owner, not with the venue's customers, and
    has no need for their personal details to understand their earnings."""
    today = today_ist()
    query = (
        select(Booking, InventoryUnit, BrokerCommission)
        .join(Venue, Venue.id == Booking.venue_id)
        .join(InventoryUnit, InventoryUnit.id == Booking.inventory_unit_id)
        .outerjoin(
            BrokerCommission,
            and_(BrokerCommission.booking_id == Booking.id, BrokerCommission.broker_id == broker_id),
        )
        .where(Venue.broker_id == broker_id, Venue.deleted_at.is_(None))
        .order_by(Booking.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    if venue_id is not None:
        query = query.where(Booking.venue_id == venue_id)

    out = []
    for booking, unit, commission in (await session.execute(query)).all():
        if commission is not None:
            payment_state = "received"
            if commission.reversed_amount >= commission.amount and commission.amount > ZERO:
                payment_state = "refunded"
            elif commission.reversed_amount > ZERO:
                payment_state = "partly_refunded"
        elif booking.status == "pending_payment":
            payment_state = "awaiting"
        elif booking.status in ("confirmed", "completed", "upcoming", "in_progress"):
            # Paid, but no commission row: the venue was attributed to this
            # broker after the payment was confirmed, or the broker was
            # paused at the time.
            payment_state = "received_not_eligible"
        else:
            payment_state = "not_received"
        out.append(
            {
                "id": booking.id,
                "reference": str(booking.id).split("-")[0].upper(),
                "venue_id": booking.venue_id,
                "venue_name": booking.venue_name,
                "event_date": unit.date,
                "start_time": unit.start_time,
                "end_time": unit.end_time,
                "status": booking.status,
                "amount": booking.amount,
                "payment_state": payment_state,
                "created_at": booking.created_at,
                "confirmed_at": booking.confirmed_at,
                "commission_rate": commission.rate if commission else None,
                "commission_amount": commission.net_amount if commission else None,
                "commission_status": commission_status(commission, today) if commission else None,
            }
        )
    return out


async def list_commissions(
    session: AsyncSession,
    *,
    broker_id: uuid.UUID | None = None,
    limit: int = 200,
    offset: int = 0,
) -> list[dict]:
    today = today_ist()
    query = (
        select(BrokerCommission, Venue.name.label("venue_name"), User.name.label("broker_name"))
        .join(Venue, Venue.id == BrokerCommission.venue_id)
        .join(User, User.id == BrokerCommission.broker_id)
        .order_by(BrokerCommission.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    if broker_id is not None:
        query = query.where(BrokerCommission.broker_id == broker_id)
    out = []
    for c, venue_name, broker_name in (await session.execute(query)).all():
        out.append(
            {
                "id": c.id,
                "broker_id": c.broker_id,
                "broker_name": broker_name,
                "venue_id": c.venue_id,
                "venue_name": venue_name,
                "booking_id": c.booking_id,
                "booking_reference": str(c.booking_id).split("-")[0].upper(),
                "event_date": c.event_date,
                "basis": c.basis,
                "basis_amount": c.basis_amount,
                "rate": c.rate,
                "amount": c.amount,
                "reversed_amount": c.reversed_amount,
                "paid_amount": c.paid_amount,
                "net_amount": c.net_amount,
                "balance_due": c.balance_due,
                "status": commission_status(c, today),
                "created_at": c.created_at,
            }
        )
    return out


# ---------------------------------------------------------------------------
# Settlements
# ---------------------------------------------------------------------------


async def record_payout(
    session: AsyncSession,
    *,
    actor: User,
    broker_id: uuid.UUID,
    expected_amount: Decimal | None = None,
    method: str | None = None,
    reference: str | None = None,
    notes: str | None = None,
) -> BrokerPayout:
    """Settles the broker's entire payable balance in one batch: every
    matured commission row with a non-zero balance, including negative
    adjustment rows, which is how an earlier over-payment gets netted off.

    expected_amount is the figure the admin saw on screen. If the real
    balance has moved since (a refund landed, another admin already paid),
    this refuses with 409 rather than paying an amount nobody approved."""
    today = today_ist()
    async with session.begin():
        user, _profile = await _load_broker(session, broker_id, lock=True)
        rows = list(
            (
                await session.execute(
                    select(BrokerCommission)
                    .where(
                        BrokerCommission.broker_id == broker_id,
                        BrokerCommission.event_date < today,
                        (BrokerCommission.amount - BrokerCommission.reversed_amount - BrokerCommission.paid_amount) != 0,
                    )
                    .order_by(BrokerCommission.event_date.asc(), BrokerCommission.created_at.asc())
                    .with_for_update()
                )
            )
            .scalars()
            .all()
        )
        total = sum((r.balance_due for r in rows), ZERO)
        if total <= ZERO:
            raise HTTPException(status_code=409, detail="This broker has no payable balance right now")
        if expected_amount is not None and _money(expected_amount) != _money(total):
            raise HTTPException(
                status_code=409,
                detail=f"The payable balance is now ₹{_money(total)}. Review it and try again.",
            )

        payout = BrokerPayout(
            broker_id=broker_id,
            amount=_money(total),
            method=method,
            reference=reference,
            notes=notes,
            paid_by=actor.id,
        )
        session.add(payout)
        await session.flush()

        now = datetime.now(timezone.utc)
        for r in rows:
            due = r.balance_due
            session.add(BrokerPayoutItem(payout_id=payout.id, commission_id=r.id, amount=due))
            r.paid_amount = r.paid_amount + due
            r.updated_at = now

        session.add(
            AuditLog(
                actor_id=actor.id,
                action="broker.payout_recorded",
                entity_type="broker",
                entity_id=broker_id,
                extra_data={
                    "payout_id": str(payout.id),
                    "amount": str(payout.amount),
                    "method": method,
                    "reference": reference,
                    "commission_rows": len(rows),
                },
            )
        )
        session.add_all(
            notify(
                user.id,
                "referral_payout_paid",
                f"A payout of ₹{payout.amount} was recorded for your referral earnings.",
                entity_type="broker",
                entity_id=user.id,
            )
        )
    return payout


async def list_payouts(session: AsyncSession, *, broker_id: uuid.UUID | None = None, limit: int = 200) -> list[dict]:
    query = (
        select(BrokerPayout, User.name.label("broker_name"))
        .join(User, User.id == BrokerPayout.broker_id)
        .order_by(BrokerPayout.paid_at.desc())
        .limit(limit)
    )
    if broker_id is not None:
        query = query.where(BrokerPayout.broker_id == broker_id)
    return [
        {
            "id": p.id,
            "broker_id": p.broker_id,
            "broker_name": broker_name,
            "amount": p.amount,
            "method": p.method,
            "reference": p.reference,
            "notes": p.notes,
            "paid_at": p.paid_at,
        }
        for p, broker_name in (await session.execute(query)).all()
    ]
