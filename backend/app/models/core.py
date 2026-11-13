"""
The five safety-critical tables from 06_Backend_Schema.md §3, as typed
SQLAlchemy 2.0 models (Mapped/mapped_column, not legacy Column-only style —
per TRD §2's stated rationale: catches type mismatches at dev time).

Two deliberate deviations from the doc's literal DDL, both flagged in
PHASE_B_SUMMARY.md — search for "Decision Point" there for the full
reasoning. Everything else here is a direct, unmodified translation of the
hand-written DDL.
"""
from __future__ import annotations

import uuid
from datetime import date as date_, datetime, time
from decimal import Decimal

from sqlalchemy import Text, event
from sqlalchemy import (
    CheckConstraint,
    Column,
    ForeignKey,
    Index,
    Numeric,
    Table,
    UniqueConstraint,
    text,
    Text,
    String,
    FetchedValue,
)
from sqlalchemy.dialects.postgresql import ARRAY, CITEXT, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.modules.core.crypto import EncryptedText

from app.models.base import (
    Base,
    BookingStatus,
    InventoryStatus,
    OwnerVerificationStatus,
    PaymentStatus,
    PayoutStatus,
    UnitType,
    UserRole,
    VenueStatus,
    IdempotencyStatus,
    BlockStatus,
    OutboxEventStatus,
    NotificationChannel,
    DeliveryStatus,
    JobStatus,
    TicketStatus,
    TicketCategory,
    TicketPriority,
    PricingRuleType,
    PricingAdjustmentType,
    ActionType,
    RequestStatus,
    ActionReasonCode,
)


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    name: Mapped[str]
    email: Mapped[str | None] = mapped_column(CITEXT, unique=True, nullable=True)
    phone: Mapped[str] = mapped_column(unique=True, nullable=False)
    password_hash: Mapped[str]
    role: Mapped[str] = mapped_column(UserRole, default="customer")
    is_verified: Mapped[bool] = mapped_column(default=False)
    # Decision Point C-14 (see the phase summary doc for this slice): a new
    # field, not a reuse of deleted_at just above/below — deleted_at is
    # explicitly documented (06_Backend_Schema.md §1: "soft deletes where
    # it matters... a venue with booking history should never be
    # hard-deleted") as being about preserving referential integrity on
    # permanent-ish removal, a different concern from a temporary,
    # admin-reversible dispute suspension (01_PRD.md §5's "suspend a
    # listing or user"). login() below treats this exactly like
    # deleted_at — same generic "incorrect email or password" 401, not a
    # distinct "account suspended" message, for the same enumeration
    # reason deleted_at's own check is already merged with the
    # wrong-password case: a distinct message would let an attacker probe
    # which emails belong to suspended accounts.
    suspended_at: Mapped[datetime | None]
    suspension_reason: Mapped[str | None]
    must_change_password: Mapped[bool] = mapped_column(default=False)
    password_changed_at: Mapped[datetime | None]
    # The single platform owner account. A flag on top of role='admin'
    # rather than a separate role, so every existing require_role("admin")
    # check keeps working; uq_single_super_admin (partial unique index)
    # guarantees there is never more than one.
    is_super_admin: Mapped[bool] = mapped_column(default=False, server_default=text("false"))
    # Who created this account from the admin console (admins and brokers
    # are never self-registered). NULL for self-signup customers/owners.
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL", name="fk_users_created_by"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"))
    updated_at: Mapped[datetime] = mapped_column(server_default=text("now()"))
    deleted_at: Mapped[datetime | None]
    # Compliance additions (alembic j1_compliance_core).
    # last_active_at drives the voluntary 3-year inactivity erasure (D-08).
    last_active_at: Mapped[datetime | None]
    inactivity_warned_at: Mapped[datetime | None]
    # Seed scripts set this; production refuses to start while any demo
    # row exists (app/modules/privacy/demo.py).
    is_demo: Mapped[bool] = mapped_column(default=False, server_default=text("false"))
    # Admin two-step sign-in (app/modules/auth/totp.py). Secret is stored
    # encrypted; recovery codes as Argon2 hashes; last step blocks replay.
    totp_secret_enc: Mapped[str | None] = mapped_column(EncryptedText, nullable=True)
    totp_enabled_at: Mapped[datetime | None]
    totp_recovery_hashes: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    totp_last_used_step: Mapped[int | None]

    venues: Mapped[list["Venue"]] = relationship(back_populates="owner", foreign_keys="Venue.owner_id")
    broker_profile: Mapped["BrokerProfile | None"] = relationship(
        back_populates="user", uselist=False, foreign_keys="BrokerProfile.user_id"
    )
    bookings: Mapped[list["Booking"]] = relationship(back_populates="customer")
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(back_populates="user")
    owner_verifications: Mapped[list["OwnerVerification"]] = relationship(
        back_populates="user", foreign_keys="OwnerVerification.user_id"
    )
    payouts: Mapped[list["Payout"]] = relationship(back_populates="owner")
    bank_accounts: Mapped[list["OwnerBankAccount"]] = relationship(back_populates="owner")
    reviews: Mapped[list["Review"]] = relationship(back_populates="user", foreign_keys="Review.user_id")
    support_tickets: Mapped[list["SupportTicket"]] = relationship(
        back_populates="creator", foreign_keys="SupportTicket.creator_id"
    )


class Venue(Base):
    __tablename__ = "venues"
    __table_args__ = (
        CheckConstraint("capacity > 0", name="chk_capacity_positive"),
        CheckConstraint("base_price >= 0", name="chk_base_price_nonneg"),
        CheckConstraint("avg_rating BETWEEN 0 AND 5", name="chk_avg_rating_range"),
        Index(
            "idx_venues_city_category",
            "city",
            "category",
            postgresql_where=text("deleted_at IS NULL AND status = 'active'"),
        ),
        Index(
            "idx_venues_owner_active",
            "owner_id",
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    name: Mapped[str]
    display_name: Mapped[str | None]
    tagline: Mapped[str | None]
    slug: Mapped[str] = mapped_column(unique=True)
    category: Mapped[str] = mapped_column(Text)
    category_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("categories.id", ondelete="RESTRICT"))
    venue_type_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("venue_types.id", ondelete="RESTRICT"))
    description: Mapped[str | None]
    address: Mapped[str]
    city: Mapped[str]
    state: Mapped[str | None]
    pincode: Mapped[str | None]
    latitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    longitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    capacity: Mapped[int | None]
    # Decision #2 (per-category pricing, resolved 2026-06-24): this column is
    # the entire fix — see 06_Backend_Schema.md §9. It already existed in the
    # schema; the gap was ReviewPay.tsx ignoring it, not a missing column.
    unit_type: Mapped[str] = mapped_column(UnitType)
    base_price: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    status: Mapped[str] = mapped_column(VenueStatus, default="draft")
    # Decision Point C-3 (see PHASE_C4_SUMMARY.md): not in
    # 06_Backend_Schema.md — venue_status has no 'rejected' value at all
    # (only draft/pending_review/active/suspended), and there's nowhere to
    # record *why* an admin rejected a listing, even though
    # 05_App_Flow.md §3/§4 explicitly requires "Owner notified with reason,
    # can edit & resubmit." Rejection targets 'draft' (editable, not
    # publicly visible) rather than a new enum value — editing a draft and
    # having PATCH re-enter 'pending_review' on a real content change *is*
    # the resubmission flow, with no separate endpoint needed for it.
    rejection_reason: Mapped[str | None]
    # Decision Point C-15 (see the phase summary doc for this slice):
    # venue_status already has 'suspended' as a valid value (line 118's
    # comment above notes it, quoting the original enum) — it's been
    # sitting there unused since the very first migration. A separate
    # column from rejection_reason, not a reuse of it: rejection is a
    # content-review outcome that clears on resubmission (PATCH re-entering
    # pending_review), suspension is an admin dispute action with its own,
    # independent lifecycle (suspend/reactivate, no content review
    # involved) — conflating the two reason fields would make either
    # action's audit trail ambiguous about which flow produced it.
    suspension_reason: Mapped[str | None]
    # Captures the field-level diff from the most recent owner edit that
    # caused the venue to re-enter 'pending_review'. Shape:
    #   {"field": {"old": <old_value>, "new": <new_value>}, ...}
    # for scalar content fields, plus an "amenities" key when amenity
    # names changed. NULL for venues entering pending_review for the first
    # time (nothing to diff against). Cleared back to NULL by approve_venue/
    # reject_venue once the admin acts — the pending state is resolved.
    pending_changes: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    # Referral attribution: the broker whose code the owner entered while
    # listing (or that an admin attached afterwards). referral_code keeps
    # the code exactly as it was applied, so the record still reads
    # correctly even if the broker's code is later regenerated.
    broker_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL", name="fk_venues_broker_id"), nullable=True
    )
    referral_code: Mapped[str | None]
    referred_at: Mapped[datetime | None]
    avg_rating: Mapped[Decimal] = mapped_column(Numeric(3, 2), default=0)
    is_demo: Mapped[bool] = mapped_column(default=False, server_default=text("false"))
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"))
    updated_at: Mapped[datetime] = mapped_column(server_default=text("now()"))
    deleted_at: Mapped[datetime | None]

    owner: Mapped["User"] = relationship(back_populates="venues", foreign_keys=[owner_id])
    broker: Mapped["User | None"] = relationship(foreign_keys=[broker_id])
    venue_category_rel: Mapped["Category | None"] = relationship(foreign_keys=[category_id])
    venue_type: Mapped["VenueType | None"] = relationship(foreign_keys=[venue_type_id])
    use_cases: Mapped[list["UseCase"]] = relationship(secondary="venue_use_cases", back_populates="venues")
    media: Mapped[list["VenueMedia"]] = relationship(
        back_populates="venue", order_by="VenueMedia.sort_order", cascade="all, delete-orphan"
    )
    content_blocks: Mapped[list["VenueContentBlock"]] = relationship(
        back_populates="venue", order_by="VenueContentBlock.sort_order", cascade="all, delete-orphan"
    )
    amenities: Mapped[list["Amenity"]] = relationship(
        secondary="venue_amenities", back_populates="venues"
    )
    inventory_units: Mapped[list["InventoryUnit"]] = relationship(back_populates="venue")
    reviews: Mapped[list["Review"]] = relationship(
        back_populates="venue", cascade="all, delete-orphan", order_by="desc(Review.created_at)"
    )
    pricing_rules: Mapped[list["PricingRule"]] = relationship(
        back_populates="venue", cascade="all, delete-orphan"
    )
    homepage_placements: Mapped[list["HomepagePlacement"]] = relationship(
        back_populates="venue", cascade="all, delete-orphan"
    )
    rental_options: Mapped[list["VenueRentalOption"]] = relationship(
        back_populates="venue", cascade="all, delete-orphan"
    )
    purposes: Mapped[list["VenuePurpose"]] = relationship(
        back_populates="venue", cascade="all, delete-orphan"
    )


class InventoryUnit(Base):
    __tablename__ = "inventory_units"
    __table_args__ = (
        CheckConstraint(
            "start_time IS NULL OR end_time IS NULL OR start_time < end_time",
            name="chk_time_range",
        ),
        UniqueConstraint("venue_id", "date", "start_time", "end_time", name="uq_unit_slot"),
        Index(
            "uq_inventory_unit_slot_nullsafe",
            "venue_id",
            "date",
            text("COALESCE(start_time, '00:00:00'::time)"),
            text("COALESCE(end_time, '23:59:59'::time)"),
            unique=True,
        ),
        CheckConstraint("price >= 0", name="chk_price_nonneg"),
        Index(
            "idx_inventory_venue_date",
            "venue_id",
            "date",
            postgresql_where=text("status = 'available'"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    venue_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("venues.id", ondelete="CASCADE"))
    date: Mapped[date_]
    # NULL for half_day/full_day units (the whole day is the block) — see
    # Decision Point B-1 in PHASE_B_SUMMARY.md for why this matters to the
    # grace-period calculation specifically.
    start_time: Mapped[time | None]
    end_time: Mapped[time | None]
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    status: Mapped[str] = mapped_column(InventoryStatus, default="available")
    hold_expires_at: Mapped[datetime | None]
    starts_at: Mapped[datetime | None] = mapped_column(server_default=FetchedValue())
    ends_at: Mapped[datetime | None] = mapped_column(server_default=FetchedValue())
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"))
    updated_at: Mapped[datetime] = mapped_column(server_default=text("now()"))

    venue: Mapped["Venue"] = relationship(back_populates="inventory_units")
    bookings: Mapped[list["Booking"]] = relationship(back_populates="inventory_unit")


class Booking(Base):
    __tablename__ = "bookings"
    __table_args__ = (
        CheckConstraint(
            "customer_id IS NOT NULL OR (guest_name IS NOT NULL AND guest_email IS NOT NULL)",
            name="chk_customer_or_guest",
        ),
        CheckConstraint("amount >= 0", name="chk_amount_nonneg"),
        # The hard backstop against double-booking — enforced by the
        # database, independent of whatever the application code does or
        # fails to do. See 06_Backend_Schema.md §3/§6.
        Index(
            "uq_active_booking_per_unit",
            "inventory_unit_id",
            unique=True,
            postgresql_where=text("status IN ('pending_payment', 'confirmed')"),
        ),
        Index("idx_bookings_customer_id", "customer_id"),
        Index("idx_bookings_venue_status", "venue_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )

    # Decision #3 (guest checkout, resolved 2026-06-24): customer_id is
    # nullable. A logged-in customer gets customer_id; a guest gets
    # guest_name/guest_email instead.
    customer_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    guest_name: Mapped[str | None]
    guest_email: Mapped[str | None] = mapped_column(CITEXT)
    guest_phone: Mapped[str | None]

    # Decision Point B-2 (flagged in PHASE_B_SUMMARY.md): the doc specifies
    # `manage_token TEXT UNIQUE` storing the raw token. This stores a SHA-256
    # hash instead — same pattern as password_hash, for the same reason: the
    # token IS this guest's entire authentication (07_design.md §5.6), so it
    # shouldn't sit in the database in a form that's directly usable if the
    # DB is ever read by anyone who shouldn't have it. The raw token exists
    # only in the emailed link, never persisted. See
    # app/modules/booking/service.py for the hash/lookup functions.
    manage_token_hash: Mapped[str | None] = mapped_column(unique=True)

    venue_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("venues.id", ondelete="RESTRICT"))
    # Snapshotted at creation time so booking history is unaffected by a
    # venue being renamed/recategorized/deleted later.
    venue_name: Mapped[str]
    venue_category: Mapped[str] = mapped_column(Text)
    inventory_unit_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("inventory_units.id", ondelete="RESTRICT")
    )
    purpose_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("venue_purposes.id", ondelete="SET NULL"), nullable=True
    )
    rental_mode: Mapped[str | None] = mapped_column(String(20), nullable=True)
    guest_count: Mapped[int | None] = mapped_column(nullable=True)
    customer_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    status: Mapped[str] = mapped_column(BookingStatus, default="pending_payment")
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    base_amount: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    currency: Mapped[str] = mapped_column(default="INR", server_default="INR")
    pricing_snapshot: Mapped[dict | None] = mapped_column(JSONB)

    # Decision #1 (instant confirm + owner grace window, resolved
    # 2026-06-24): set together when payment succeeds. See
    # app/modules/booking/service.py for how grace_period_ends_at is
    # computed — including Decision Point B-1's resolution for
    # half_day/full_day units with no start_time.
    confirmed_at: Mapped[datetime | None]
    grace_period_ends_at: Mapped[datetime | None]
    owner_flagged_at: Mapped[datetime | None]

    cancellation_reason: Mapped[str | None]
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"))
    updated_at: Mapped[datetime] = mapped_column(server_default=text("now()"))
    cancelled_at: Mapped[datetime | None]

    customer: Mapped["User | None"] = relationship(back_populates="bookings")
    venue: Mapped["Venue"] = relationship()
    inventory_unit: Mapped["InventoryUnit"] = relationship(back_populates="bookings")
    purpose: Mapped["VenuePurpose | None"] = relationship()
    payments: Mapped[list["Payment"]] = relationship(back_populates="booking")
    events: Mapped[list["BookingEvent"]] = relationship(
        back_populates="booking", cascade="all, delete-orphan", order_by="BookingEvent.created_at"
    )
    action_requests: Mapped[list["BookingActionRequest"]] = relationship(
        back_populates="booking", cascade="all, delete-orphan", order_by="BookingActionRequest.created_at"
    )
    review: Mapped["Review | None"] = relationship(back_populates="booking", uselist=False)
    refunds: Mapped[list["Refund"]] = relationship(back_populates="booking", cascade="all, delete-orphan")

    # A real gap found while starting frontend integration (Phase D):
    # BookingDetail had no way to show *when* a booking is actually for —
    # unlike venue_name/venue_category, the slot date/time was never
    # snapshotted onto Booking itself, only reachable via inventory_unit.
    # These properties, not new columns, since the slot is immutable once
    # a booking exists against it (no rescheduling flow exists anywhere
    # in this codebase) — a live join reflects reality exactly as well as
    # a snapshot would, without a second copy of the same fact to keep in
    # sync. Callers MUST eager-load inventory_unit first (selectinload/
    # joinedload) — accessing these without it would lazy-load outside an
    # async greenlet context, the exact MissingGreenlet shape
    # PHASE_C4_SUMMARY.md already found and fixed once for venue.images.
    @property
    def slot_date(self) -> date_:
        return self.inventory_unit.date

    @property
    def slot_start_time(self) -> time | None:
        return self.inventory_unit.start_time

    @property
    def reviewed_at(self) -> datetime | None:
        # Requires eager-loading self.review
        return self.review.created_at if self.review else None

    @property
    def slot_end_time(self) -> time | None:
        return self.inventory_unit.end_time

    @property
    def hold_expires_at(self) -> datetime | None:
        """Added for the Admin dashboard's Bookings screen: without this, an
        admin has no way to see which pending_payment bookings are already
        past their hold window (they'd otherwise just sit there forever —
        there's no sweep job that clears them automatically). None once the
        booking is confirmed/cancelled (inventory_unit.hold_expires_at is
        cleared at that point, same lifecycle as everywhere else it's set)."""
        return self.inventory_unit.hold_expires_at


class BookingEvent(Base):
    """Event history for the booking lifecycle (what happened to this booking?)."""

    __tablename__ = "booking_events"
    __table_args__ = (
        Index("idx_booking_events_booking_id_created_at", "booking_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    booking_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("bookings.id", ondelete="CASCADE"))
    event_type: Mapped[str]
    correlation_id: Mapped[str | None] = mapped_column(Text)
    actor_type: Mapped[str | None]
    actor_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    extra_data: Mapped[dict | None] = mapped_column("metadata", JSONB)
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"))

    booking: Mapped["Booking"] = relationship(back_populates="events")
    actor: Mapped["User | None"] = relationship()


class BookingActionRequest(Base):
    """Admin control lifecycle request for important booking state changes."""
    __tablename__ = "booking_action_requests"
    __table_args__ = (
        Index("idx_booking_actions_booking", "booking_id", "status"),
        Index("idx_booking_actions_requested_at", "requested_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    booking_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("bookings.id", ondelete="CASCADE"))
    action_type: Mapped[str] = mapped_column(ActionType)
    requested_by_type: Mapped[str] = mapped_column(UserRole)
    requested_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    requested_at: Mapped[datetime] = mapped_column(server_default=text("now()"))
    reason: Mapped[str | None] = mapped_column(ActionReasonCode)
    notes: Mapped[str | None]
    metadata_json: Mapped[dict | None] = mapped_column("metadata", JSONB)
    status: Mapped[str] = mapped_column(RequestStatus, default="pending")
    assigned_admin_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    reviewed_by_admin_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    reviewed_at: Mapped[datetime | None]
    admin_decision: Mapped[str | None]
    decision_reason: Mapped[str | None]
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"))
    updated_at: Mapped[datetime] = mapped_column(server_default=text("now()"))

    booking: Mapped["Booking"] = relationship(back_populates="action_requests")
    requested_by_user: Mapped["User | None"] = relationship(foreign_keys=[requested_by_user_id])
    assigned_admin: Mapped["User | None"] = relationship(foreign_keys=[assigned_admin_id])
    reviewed_by_admin: Mapped["User | None"] = relationship(foreign_keys=[reviewed_by_admin_id])


class Payment(Base):
    __tablename__ = "payments"
    __table_args__ = (
        Index("idx_payments_booking_id", "booking_id"),
        Index("idx_payments_payout_id", "payout_id"),
        Index(
            "uq_one_successful_payment_per_booking",
            "booking_id",
            unique=True,
            postgresql_where=text("status IN ('success', 'refunded')"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    booking_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("bookings.id", ondelete="RESTRICT"))
    gateway: Mapped[str] = mapped_column(default="razorpay")
    gateway_payment_id: Mapped[str | None] = mapped_column(unique=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    currency: Mapped[str] = mapped_column(default="INR")
    method: Mapped[str | None]
    status: Mapped[str] = mapped_column(PaymentStatus, default="initiated")
    # Decision Point C-9 (see the phase summary doc for this slice): no doc
    # models a partial refund anywhere - payment_status is binary
    # (success/refunded) and `amount` is fixed at collection time. Added so
    # "refunded" can mean anything from 0% to 100% of `amount`, populated
    # by both flag_booking (always == amount, for consistency - see the
    # same summary) and the new customer-initiated cancellation path
    # (Decision Point C-7's tiers). NULL until a refund is actually
    # recorded against this payment.
    refund_amount: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    commission_rate: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    commission_amount: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    # Decision Point C-12 (see the phase summary doc for this slice): the
    # ERD in 06_Backend_Schema.md §2 has no relationship at all from
    # payments/bookings to payouts — a payout is modeled purely as an
    # owner-level aggregate. NULL until this payment has been included in
    # a payout run; set once, never cleared, so a payment can never be
    # double-counted across payout runs regardless of what period dates an
    # admin types in — a structural backstop, not reliance on the caller
    # choosing non-overlapping periods correctly (same "backstop, not just
    # trusting application logic" philosophy as uq_active_booking_per_unit).
    payout_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("payouts.id", ondelete="RESTRICT"))
    raw_payload: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"))
    updated_at: Mapped[datetime] = mapped_column(server_default=text("now()"))

    booking: Mapped["Booking"] = relationship(back_populates="payments")
    payout: Mapped["Payout | None"] = relationship(back_populates="payments")
    refunds: Mapped[list["Refund"]] = relationship(back_populates="payment", cascade="all, delete-orphan")



class PasswordResetRequest(Base):
    __tablename__ = "password_reset_requests"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    token_hash: Mapped[str | None] = mapped_column(unique=True, nullable=True)
    status: Mapped[str] = mapped_column(String(32), server_default="pending", default="pending")
    expires_at: Mapped[datetime | None] = mapped_column(nullable=True)
    used_at: Mapped[datetime | None]
    requested_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    reason: Mapped[str | None]
    source_type: Mapped[str | None]
    source_id: Mapped[str | None]
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"))
    
    user: Mapped["User"] = relationship(foreign_keys=[user_id])
    requester: Mapped["User | None"] = relationship(foreign_keys=[requested_by])

class RefreshToken(Base):
    """
    Decision Point C-1 (flag for sign-off — see PHASE_C2_SUMMARY.md):
    06_Backend_Schema.md §3/§4 never specifies a table for this.
    TRD §4 requires "every refresh issues a new refresh token and
    invalidates the old one" and reuse-detection — that needs *some*
    persistent, queryable record of issued tokens; a stateless JWT-only
    refresh token can't be individually revoked or checked for reuse.

    Resolved here as a real table rather than a Redis key for the same
    reason 06_Backend_Schema.md §6 already gives for bookings: "Postgres is
    the source of truth, Redis is the UX layer." Applying that same
    principle to auth sessions — Redis eviction under memory pressure would
    force-logout every user with no warning, which is a worse failure mode
    than one extra indexed table. This also naturally supports multiple
    concurrent sessions per user (phone + desktop), which a single
    current-token-on-the-user-row design would not.
    """

    __tablename__ = "refresh_tokens"
    __table_args__ = (
        Index(
            "idx_refresh_tokens_active_by_user",
            "user_id",
            postgresql_where=text("revoked_at IS NULL"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    token_hash: Mapped[str] = mapped_column(unique=True)
    expires_at: Mapped[datetime]
    revoked_at: Mapped[datetime | None]
    # Self-referential: when a token is rotated, the new token's id is
    # recorded on the old one. If a revoked token is ever presented again
    # (replay of a stolen token), that's the reuse-detection signal — see
    # app/modules/auth/service.py's rotate_refresh_token().
    replaced_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("refresh_tokens.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"))

    user: Mapped["User"] = relationship(back_populates="refresh_tokens", foreign_keys=[user_id])


class OwnerVerification(Base):
    """
    Decision Point C-2 (flag for sign-off — see PHASE_C3_SUMMARY.md):
    06_Backend_Schema.md has only `users.is_verified BOOLEAN`. That's
    enough to gate "can this user list a venue," but not enough to
    represent the actual workflow 05_App_Flow.md §3 / PRD §5 describe:
    pending review, rejection with a reason, and resubmission after a
    rejection. A boolean can't distinguish "never applied" from "applied
    and waiting" from "rejected, fix this and try again."

    Resolved as a new table rather than extra columns on `users`: a
    resubmission after rejection should create a NEW row, not overwrite
    the old one — the rejection history (who reviewed it, what the reason
    was, when) is exactly the kind of thing an admin reviewing a second
    attempt needs to see, and exactly the kind of thing TRD §7's audit
    requirements care about.

    `users.is_verified` is left as-is and unmodified — it stays the simple
    "is this user currently allowed to list venues" gate. This table is
    the history/workflow behind it; approval here is what flips that flag.
    """

    __tablename__ = "owner_verifications"
    __table_args__ = (
        # At most one PENDING submission per user at a time — same pattern
        # as uq_active_booking_per_unit, applied here so a double-click on
        # "submit" can't create two pending rows for an admin to
        # accidentally review inconsistently.
        Index(
            "uq_one_pending_verification_per_user",
            "user_id",
            unique=True,
            postgresql_where=text("status = 'pending'"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    document_url: Mapped[str | None] = mapped_column(Text, nullable=True, default="")
    storage_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    identification_type: Mapped[str | None]
    identification_number: Mapped[str | None] = mapped_column(EncryptedText, nullable=True)
    # identification_number, pan and gstin hold AES-GCM ciphertext
    # ("enc:v1:..."), see app/modules/core/crypto.py.
    pan: Mapped[str | None] = mapped_column(EncryptedText, nullable=True)
    gstin: Mapped[str | None] = mapped_column(EncryptedText, nullable=True)
    business_name: Mapped[str | None]
    status: Mapped[str] = mapped_column(OwnerVerificationStatus, default="pending")
    rejection_reason: Mapped[str | None]
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    reviewed_at: Mapped[datetime | None]
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"))

    user: Mapped["User"] = relationship(back_populates="owner_verifications", foreign_keys=[user_id])
    reviewer: Mapped["User | None"] = relationship(foreign_keys=[reviewed_by])


class Notification(Base):
    """New table, added for the Admin dashboard's follow-up work: an
    in-app notification so an owner/user finds out when an admin acts on
    something of theirs (venue approved/rejected/suspended/reactivated,
    verification approved/rejected, their own account suspended/
    reactivated) without asking support or happening to notice it
    themselves. Deliberately in-app only, not email/SMS — this sandbox has
    no route to any external delivery service (handoff.md's environment
    notes), and a real email pipeline (provider, templates,
    deliverability) is a separate, larger decision than this pass covers.
    `type` is a free-form string identifying which action triggered this
    (e.g. 'venue_approved', 'user_suspended') rather than an enum — new
    notification types are expected to be added over time as more admin
    actions get wired up, without a schema migration each time."""

    __tablename__ = "notifications"
    __table_args__ = (Index("ix_notifications_user_id_created_at", "user_id", "created_at"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    type: Mapped[str]
    message: Mapped[str]
    entity_type: Mapped[str | None]
    entity_id: Mapped[uuid.UUID | None]
    read_at: Mapped[datetime | None]
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"))

    user: Mapped["User"] = relationship()
    deliveries: Mapped[list["NotificationDelivery"]] = relationship(back_populates="notification", cascade="all, delete-orphan")


class NotificationDelivery(Base):
    __tablename__ = "notification_deliveries"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    notification_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("notifications.id", ondelete="CASCADE"))
    channel: Mapped[str] = mapped_column(NotificationChannel)
    status: Mapped[str] = mapped_column(DeliveryStatus, default="queued")
    provider_response: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"))
    updated_at: Mapped[datetime] = mapped_column(server_default=text("now()"))

    notification: Mapped["Notification"] = relationship(back_populates="deliveries")


class AuditLog(Base):
    """06_Backend_Schema.md §4 (summary table, no full DDL given) — TRD §7:
    'sensitive actions (listing approval/rejection, payouts, role changes)
    are written to an audit_logs table.' Immutable by convention: no
    `updated_at`, no update path anywhere in this codebase — a row, once
    written, is never changed, only ever read."""

    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("idx_audit_logs_entity", "entity_type", "entity_id", "created_at"),
        Index("idx_audit_logs_actor", "actor_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    actor_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    action: Mapped[str]
    correlation_id: Mapped[str | None] = mapped_column(Text)
    entity_type: Mapped[str]
    entity_id: Mapped[uuid.UUID | None]
    # Python attribute is `extra_data`, not `metadata` — SQLAlchemy's
    # DeclarativeBase already reserves `metadata` for Base.metadata (the
    # MetaData object itself); using it as a column attribute name would
    # shadow that. The actual database column is still named `metadata`,
    # matching 06_Backend_Schema.md §4's literal field name.
    extra_data: Mapped[dict | None] = mapped_column("metadata", JSONB)
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"))


# Plain Table, not a mapped class — 06_Backend_Schema.md §4 describes this
# as a composite-PK join table with no columns of its own beyond the two
# FKs, so there's no row identity worth giving its own ORM class.
venue_amenities = Table(
    "venue_amenities",
    Base.metadata,
    Column("venue_id", ForeignKey("venues.id", ondelete="CASCADE"), primary_key=True),
    Column("amenity_id", ForeignKey("amenities.id", ondelete="CASCADE"), primary_key=True),
)


class Amenity(Base):
    """06_Backend_Schema.md §4 (summary only, no full DDL). Phase 1 doesn't
    have an admin-curated master list anywhere in the docs, so amenities
    are get-or-created by name when a venue references one — see
    app/modules/catalog/service.py. That's a deliberate simplicity choice,
    not a doc requirement; a fixed taxonomy is one migration away if
    free-text tags turn out to fragment too much in practice (e.g. "wifi"
    vs "WiFi" vs "Wi-Fi" becoming three different rows)."""

    __tablename__ = "amenities"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    name: Mapped[str] = mapped_column(unique=True)

    venues: Mapped[list["Venue"]] = relationship(secondary=venue_amenities, back_populates="amenities")


class VenueMedia(Base):
    """06_Backend_Schema.md §4: 'partial unique index ensures only one
    is_cover = true per venue' — implemented exactly as the doc's summary
    describes, same partial-unique-index pattern used everywhere else in
    this schema (uq_active_booking_per_unit, uq_one_pending_verification_per_user).

    media_type / thumbnail_url added by migration 48fc1eaeba4f (add_video_support).
    Index was renamed from uq_one_cover_image_per_venue → uq_one_cover_media_per_venue
    in that same migration."""

    __tablename__ = "venue_media"
    __table_args__ = (
        Index(
            "uq_one_cover_media_per_venue",
            "venue_id",
            unique=True,
            postgresql_where=text("is_cover = true"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    venue_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("venues.id", ondelete="CASCADE"))
    url: Mapped[str]
    storage_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    media_type: Mapped[str] = mapped_column(default="image", server_default="image")
    thumbnail_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_cover: Mapped[bool] = mapped_column(default=False)
    sort_order: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"))

    venue: Mapped["Venue"] = relationship(back_populates="media")


class VenueContentBlock(Base):
    """
    Phase 14: Custom block model for presentation layer.
    Allows owners to build rich presentation pages without rigid schema columns for every possible field.
    """
    __tablename__ = "venue_content_blocks"
    __table_args__ = (
        Index("idx_venue_content_blocks_venue_id_sort", "venue_id", "sort_order"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    venue_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("venues.id", ondelete="CASCADE"))
    type: Mapped[str]
    title: Mapped[str | None]
    subtitle: Mapped[str | None]
    body: Mapped[str | None]
    media_reference: Mapped[str | None]
    settings: Mapped[dict | None] = mapped_column(JSONB)
    sort_order: Mapped[int] = mapped_column(default=0)
    enabled: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"))
    updated_at: Mapped[datetime] = mapped_column(server_default=text("now()"))

    venue: Mapped["Venue"] = relationship(back_populates="content_blocks")


class VenueRentalOption(Base):
    """Guide 11: Multi-mode rental configuration per venue.
    Modes: 'hour', 'half_day', 'full_day'.
    """
    __tablename__ = "venue_rental_options"
    __table_args__ = (
        CheckConstraint("mode IN ('hour', 'half_day', 'full_day')", name="chk_rental_mode"),
        CheckConstraint("price >= 0", name="chk_rental_price_non_negative"),
        UniqueConstraint("venue_id", "mode", name="uq_venue_rental_mode"),
        Index("idx_venue_rental_options_venue_id", "venue_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    venue_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("venues.id", ondelete="CASCADE"))
    mode: Mapped[str] = mapped_column(String(20))
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    open_time: Mapped[time | None]
    close_time: Mapped[time | None]
    slot_minutes: Mapped[int | None]
    min_minutes: Mapped[int | None]
    max_minutes: Mapped[int | None]
    buffer_minutes: Mapped[int] = mapped_column(default=0, server_default="0")
    enabled: Mapped[bool] = mapped_column(default=True, server_default="true")
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"))
    updated_at: Mapped[datetime] = mapped_column(server_default=text("now()"))

    venue: Mapped["Venue"] = relationship(back_populates="rental_options")


class VenuePurpose(Base):
    """Guide 11: Purpose / Event types a venue can host."""
    __tablename__ = "venue_purposes"
    __table_args__ = (
        CheckConstraint(
            "use_case_id IS NOT NULL OR custom_name IS NOT NULL",
            name="chk_purpose_has_name",
        ),
        CheckConstraint(
            "price_override IS NULL OR price_override >= 0",
            name="chk_purpose_price_override_non_negative",
        ),
        Index("idx_venue_purposes_venue_id", "venue_id"),
        Index("idx_venue_purposes_use_case_id", "use_case_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    venue_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("venues.id", ondelete="CASCADE"))
    use_case_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("use_cases.id", ondelete="SET NULL"), nullable=True
    )
    custom_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    is_custom_approved: Mapped[bool | None] = mapped_column(nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    max_guests: Mapped[int | None] = mapped_column(nullable=True)
    allowed_modes: Mapped[list[str] | None] = mapped_column(ARRAY(String(20)), nullable=True)
    price_override: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    rules: Mapped[str | None] = mapped_column(Text, nullable=True)
    enabled: Mapped[bool] = mapped_column(default=True, server_default="true")
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"))
    updated_at: Mapped[datetime] = mapped_column(server_default=text("now()"))

    venue: Mapped["Venue"] = relationship(back_populates="purposes")
    use_case: Mapped["UseCase | None"] = relationship()


class LoginRateLimit(Base):
    """Replaces the original Redis INCR+EXPIRE fixed-window counter (see
    the phase summary doc for this slice — Redis removed from the project
    entirely per explicit client direction, Postgres-only going forward).
    One row per rate-limited key (today: f"ratelimit:login:{email}"),
    upserted atomically by check_login_rate_limit() in
    app/modules/auth/service.py — see that function's docstring for the
    UPSERT itself. No relationship to any other table; this is pure
    infrastructure bookkeeping, not domain data, which is also why it's a
    plain primary-key-on-the-key-string table rather than a UUID id."""

    __tablename__ = "login_rate_limits"

    key: Mapped[str] = mapped_column(primary_key=True)
    window_start: Mapped[datetime]
    attempt_count: Mapped[int] = mapped_column(default=1)


class Payout(Base):
    """06_Backend_Schema.md §4/§2: listed only as a one-line summary
    (`owner_id`, `period_start/end`, `gross_amount`, `commission_amount`,
    `net_amount`, `status`) plus an ERD edge (`USERS ||--o{ PAYOUTS :
    receives`) — no full DDL, no status enum, no commission rate, and
    critically no relationship at all back to bookings/payments, even
    though "one row per owner per settlement period" (07_design.md §4)
    necessarily aggregates many of them. Built out exactly the way
    owner_verifications/audit_logs were before this same gap in each of
    them (see PHASE_C3_SUMMARY.md). Decision Points C-10/C-11/C-12 in the
    phase summary doc for this slice cover the reasoning in full —
    gross_amount is defined here as the amount actually *retained* by the
    platform per payment (amount minus any refund_amount), not the
    pre-refund booking price, which is what makes a partially-refunded
    booking contribute the right, non-zero amount without any special-case
    branching.
    """

    __tablename__ = "payouts"
    __table_args__ = (
        CheckConstraint("period_start <= period_end", name="chk_payout_period_valid"),
        CheckConstraint("gross_amount >= 0", name="chk_payout_gross_nonneg"),
        Index("idx_payouts_owner_period", "owner_id", "period_start"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    period_start: Mapped[date_]
    period_end: Mapped[date_]
    gross_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    commission_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    net_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    status: Mapped[str] = mapped_column(PayoutStatus, default="pending")
    payout_reference: Mapped[str | None] = mapped_column(String(128), nullable=True)
    bank_account_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("owner_bank_accounts.id", ondelete="SET NULL"), nullable=True)
    paid_at: Mapped[datetime | None]
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"))
    updated_at: Mapped[datetime] = mapped_column(server_default=text("now()"))

    owner: Mapped["User"] = relationship(back_populates="payouts")
    bank_account: Mapped["OwnerBankAccount | None"] = relationship(back_populates="payouts")
    payments: Mapped[list["Payment"]] = relationship(back_populates="payout")


class Review(Base):
    """User-submitted review for a venue. Any authenticated user may submit
    a review — no booking-verified restriction in Phase 1. Admins can delete
    inappropriate reviews via DELETE /api/v1/admin/reviews/{id}.

    avg_rating on Venue is recalculated in-app (not a DB trigger) every time
    a review is created or deleted — a simple AVG query is fast enough for
    Phase 1 volumes and avoids the trigger-maintenance overhead."""

    __tablename__ = "reviews"
    __table_args__ = (
        CheckConstraint("rating BETWEEN 1 AND 5", name="chk_review_rating_range"),
        Index("idx_reviews_venue_id_created_at", "venue_id", "created_at"),
        UniqueConstraint("booking_id", name="uq_reviews_booking_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    venue_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("venues.id", ondelete="CASCADE"))
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    booking_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("bookings.id", ondelete="SET NULL"))
    rating: Mapped[int]
    content: Mapped[str]
    # True only when the review is tied to the author's own completed
    # booking at this venue. Public listings show verified reviews only.
    verified: Mapped[bool] = mapped_column(default=False, server_default=text("false"))
    is_demo: Mapped[bool] = mapped_column(default=False, server_default=text("false"))
    # Super admin moderation. The text and rating a customer wrote are never
    # edited; a review can only be hidden (with a reason) or featured.
    hidden_at: Mapped[datetime | None] = mapped_column(nullable=True)
    hidden_reason: Mapped[str | None] = mapped_column(nullable=True)
    hidden_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    featured: Mapped[bool] = mapped_column(default=False, server_default=text("false"))
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"))

    venue: Mapped["Venue"] = relationship(back_populates="reviews")
    user: Mapped["User"] = relationship(back_populates="reviews", foreign_keys=[user_id])
    booking: Mapped["Booking"] = relationship(back_populates="review")


class IdempotencyKey(Base):
    """Stores information for ensuring operations are idempotent."""
    __tablename__ = "idempotency_keys"
    __table_args__ = (
        UniqueConstraint("key", "actor_id", "operation", name="uq_idemp_key_actor_op"),
        Index("idx_idempotency_keys_expires_at", "expires_at"),
        Index("uq_idemp_key_null_actor_op", "key", "operation", unique=True, postgresql_where=text("actor_id IS NULL")),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    key: Mapped[str]
    actor_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    operation: Mapped[str]
    request_hash: Mapped[str | None]
    status: Mapped[str] = mapped_column(IdempotencyStatus, default="in_progress")
    response_code: Mapped[int | None]
    response_body: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"))
    updated_at: Mapped[datetime] = mapped_column(server_default=text("now()"))
    expires_at: Mapped[datetime]


class SystemConfiguration(Base):
    """
    Singleton typed settings table for core business values previously hardcoded.
    Preserves exact production behavior with seed values.
    """
    __tablename__ = "system_configuration"
    __table_args__ = (
        CheckConstraint("id = 1", name="chk_singleton_config"),
        CheckConstraint("booking_hold_duration_minutes > 0", name="chk_hold_duration_positive"),
        CheckConstraint("booking_grace_period_hours >= 0", name="chk_grace_period_nonneg"),
        CheckConstraint("cancellation_full_refund_hours >= cancellation_partial_refund_hours", name="chk_refund_hours_order"),
        CheckConstraint("cancellation_partial_refund_percent BETWEEN 0 AND 100", name="chk_refund_percent_range"),
        CheckConstraint("platform_commission_percent BETWEEN 0 AND 100", name="chk_commission_percent_range"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    booking_hold_duration_minutes: Mapped[int] = mapped_column(default=30)
    booking_grace_period_hours: Mapped[int] = mapped_column(default=2)
    cancellation_full_refund_hours: Mapped[int] = mapped_column(default=48)
    cancellation_partial_refund_hours: Mapped[int] = mapped_column(default=24)
    cancellation_partial_refund_percent: Mapped[int] = mapped_column(default=50)
    platform_commission_percent: Mapped[int] = mapped_column(default=10)
    payout_holdback_days: Mapped[int] = mapped_column(default=3)
    # Rate pre-filled when an admin adds a broker. Only the super admin can
    # change an individual broker's rate afterwards.
    # Business facts the owner supplies once (legal name, Grievance Officer,
    # jurisdiction...). Keys: app/modules/privacy/legal_profile.py. Unset
    # keys render as [[OWNER TO FILL: ...]] placeholders, never invented.
    legal_profile: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    default_broker_commission_percent: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), default=Decimal("2.00"), server_default="2"
    )

    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"))
    updated_at: Mapped[datetime] = mapped_column(server_default=text("now()"))


class Block(Base):
    """Temporary or maintenance blocking windows for a venue or specific inventory unit."""
    __tablename__ = "blocks"
    __table_args__ = (
        CheckConstraint("start_time < end_time", name="chk_block_time_range"),
        Index(
            "idx_blocks_venue_active",
            "venue_id",
            postgresql_where=text("status = 'active'"),
        ),
        Index("idx_blocks_venue_time", "venue_id", "start_time"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    venue_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("venues.id", ondelete="CASCADE"))
    inventory_unit_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("inventory_units.id", ondelete="CASCADE"))
    start_time: Mapped[datetime]
    end_time: Mapped[datetime]
    reason: Mapped[str]
    status: Mapped[str] = mapped_column(BlockStatus, default="active")
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"))
    updated_at: Mapped[datetime] = mapped_column(server_default=text("now()"))

    venue: Mapped["Venue"] = relationship()
    inventory_unit: Mapped["InventoryUnit | None"] = relationship()
    creator: Mapped["User"] = relationship()

class OutboxEvent(Base):
    """Transactional outbox pattern for reliable side-effects"""
    __tablename__ = "outbox_events"
    __table_args__ = (
        Index(
            "idx_outbox_events_pending",
            "status",
            "next_attempt_at",
            postgresql_where=text("status = 'pending'"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    event_type: Mapped[str]
    correlation_id: Mapped[str | None] = mapped_column(Text)
    aggregate_type: Mapped[str]
    aggregate_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    payload: Mapped[dict] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(OutboxEventStatus, default="pending")
    attempts: Mapped[int] = mapped_column(default=0)
    next_attempt_at: Mapped[datetime] = mapped_column(server_default=text("now()"))
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"))
    processed_at: Mapped[datetime | None]
    error_details: Mapped[str | None]


class Job(Base):
    """Unified background jobs model."""
    __tablename__ = "jobs"
    __table_args__ = (
        Index(
            "idx_jobs_pending",
            "status",
            "next_attempt_at",
            postgresql_where=text("status IN ('pending', 'running')"),
        ),
        Index(
            "idx_jobs_correlation",
            "job_type",
            "correlation_id",
            unique=True,
            postgresql_where=text("status IN ('pending', 'running')"),
        ),
    )
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    job_type: Mapped[str] = mapped_column(Text)
    correlation_id: Mapped[str | None] = mapped_column(Text)
    payload: Mapped[dict | None] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(JobStatus, default="pending")
    attempts: Mapped[int] = mapped_column(default=0)
    max_attempts: Mapped[int] = mapped_column(default=3)
    error_details: Mapped[str | None] = mapped_column(Text)
    next_attempt_at: Mapped[datetime] = mapped_column(server_default=text("now()"))
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"))
    started_at: Mapped[datetime | None]
    completed_at: Mapped[datetime | None]

class SupportTicket(Base):
    """Lightweight support/dispute model — reuses existing bookings, users,
    venues, audit logs, and notifications rather than building a separate CRM.

    category="dispute" requires a non-null booking_id. Dispute resolution
    records outcomes in TicketEvent metadata but cannot bypass booking/payment
    invariants — any refund or status change on the booking itself must go
    through the existing booking service endpoints."""

    __tablename__ = "support_tickets"
    __table_args__ = (
        Index("idx_support_tickets_creator", "creator_id", "created_at"),
        Index(
            "idx_support_tickets_venue_status",
            "venue_id",
            "status",
            postgresql_where=text("venue_id IS NOT NULL"),
        ),
        Index("idx_support_tickets_status", "status", "created_at"),
        Index("idx_support_tickets_help_article", "help_article_id", "help_section"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    subject: Mapped[str]
    description: Mapped[str]
    status: Mapped[str] = mapped_column(TicketStatus, default="open")
    category: Mapped[str] = mapped_column(TicketCategory, default="general")
    priority: Mapped[str] = mapped_column(TicketPriority, default="medium")
    # Nullable since j1_compliance_core: guest Contact-form tickets have no
    # account; their contact details stay in guest_enquiries.
    creator_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    guest_enquiry_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("guest_enquiries.id", ondelete="SET NULL"), nullable=True
    )
    # Human-facing reference, e.g. GK-T-2611-0042 (shown on the Contact form).
    ticket_number: Mapped[str | None] = mapped_column(unique=True, nullable=True)
    # Grievance clocks (app/modules/support/sla.py): content complaints
    # 24 h / 15 days (Intermediary Rules), others 48 h / 30 days
    # (E-Commerce Rules r.4(5)), never more than 90 days (DPDP Rules r.14).
    ack_due_at: Mapped[datetime | None]
    resolve_due_at: Mapped[datetime | None]
    acknowledged_at: Mapped[datetime | None]
    assignee_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    booking_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("bookings.id", ondelete="SET NULL")
    )
    venue_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("venues.id", ondelete="SET NULL")
    )
    help_article_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("help_articles.id", ondelete="SET NULL")
    )
    help_article_version: Mapped[int | None]
    help_section: Mapped[str | None]
    help_excerpt: Mapped[str | None]
    resolved_at: Mapped[datetime | None]
    closed_at: Mapped[datetime | None]
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"))
    updated_at: Mapped[datetime] = mapped_column(server_default=text("now()"))

    creator: Mapped["User"] = relationship(
        back_populates="support_tickets", foreign_keys=[creator_id]
    )
    assignee: Mapped["User | None"] = relationship(foreign_keys=[assignee_id])
    booking: Mapped["Booking | None"] = relationship()
    venue: Mapped["Venue | None"] = relationship()
    help_article: Mapped["HelpArticle | None"] = relationship()
    events: Mapped[list["TicketEvent"]] = relationship(
        back_populates="ticket",
        cascade="all, delete-orphan",
        order_by="TicketEvent.created_at",
    )


class TicketEvent(Base):
    """Immutable event log for a support ticket — mirrors BookingEvent's
    pattern. Rows with internal=True are admin-only notes hidden from
    customers and venue owners."""

    __tablename__ = "ticket_events"
    __table_args__ = (
        Index("idx_ticket_events_ticket", "ticket_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    ticket_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("support_tickets.id", ondelete="CASCADE")
    )
    event_type: Mapped[str]
    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    old_status: Mapped[str | None]
    new_status: Mapped[str | None]
    comment: Mapped[str | None]
    internal: Mapped[bool] = mapped_column(default=False)
    extra_data: Mapped[dict | None] = mapped_column("metadata", JSONB)
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"))

    ticket: Mapped["SupportTicket"] = relationship(back_populates="events")
    actor: Mapped["User | None"] = relationship()


from app.modules.core.logging import request_id_ctx  # noqa: E402

@event.listens_for(BookingEvent, "before_insert")
def receive_before_insert_booking_event(mapper, connection, target):
    if target.correlation_id is None:
        target.correlation_id = request_id_ctx.get()

@event.listens_for(AuditLog, "before_insert")
def receive_before_insert_audit_log(mapper, connection, target):
    if target.correlation_id is None:
        target.correlation_id = request_id_ctx.get()
class PricingRule(Base):
    __tablename__ = "pricing_rules"
    __table_args__ = (
        Index("idx_pricing_rules_venue_active", "venue_id", postgresql_where=text("is_active = true")),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    venue_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("venues.id", ondelete="CASCADE"))
    name: Mapped[str]
    rule_type: Mapped[str] = mapped_column(PricingRuleType)
    adjustment_type: Mapped[str] = mapped_column(PricingAdjustmentType)
    adjustment_value: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    
    start_date: Mapped[date_ | None]
    end_date: Mapped[date_ | None]
    start_time: Mapped[time | None]
    end_time: Mapped[time | None]
    days_of_week: Mapped[list[int] | None] = mapped_column(JSONB)
    
    priority: Mapped[int] = mapped_column(default=0)
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"))
    updated_at: Mapped[datetime] = mapped_column(server_default=text("now()"))

    venue: Mapped["Venue"] = relationship(back_populates="pricing_rules")


class HomepagePlacement(Base):
    """Admin-curated homepage section placement.

    Each row says "venue X should appear in section Y at position Z."
    The homepage API enforces venue.status='active' + scheduling at query
    time — this table only stores the admin's intent, not a visibility
    guarantee. The client never decides which venues appear publicly; all
    filtering is server-side.

    Sections (fixed string set, no enum — avoids a migration per new section):
      featured | trending | popular | recommended | new

    Scheduling:
      start_at IS NULL  → show immediately
      end_at   IS NULL  → no expiry
      Both set          → only visible within that UTC window
    """

    __tablename__ = "homepage_placements"
    __table_args__ = (
        # A venue appears at most once per section — prevents duplicate cards.
        UniqueConstraint("venue_id", "section", name="uq_venue_section"),
        # Primary query index: homepage API fetches by section + enabled,
        # ordered by priority ASC. Partial on enabled keeps the index tiny.
        Index(
            "idx_hp_section_priority",
            "section",
            "priority",
            postgresql_where=text("enabled = TRUE"),
        ),
        # Secondary index for venue-level admin queries.
        Index("idx_hp_venue_id", "venue_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    venue_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("venues.id", ondelete="CASCADE", name="fk_homepage_placements_venue_id")
    )
    section: Mapped[str] = mapped_column(nullable=False)
    enabled: Mapped[bool] = mapped_column(default=True)
    priority: Mapped[int] = mapped_column(default=0)
    badge: Mapped[str | None] = mapped_column(nullable=True)
    custom_title: Mapped[str | None] = mapped_column(nullable=True)
    custom_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Scheduling — UTC datetimes. NULL = show immediately / no expiry.
    start_at: Mapped[datetime | None] = mapped_column(nullable=True)
    end_at: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"))
    updated_at: Mapped[datetime] = mapped_column(server_default=text("now()"))

    venue: Mapped["Venue"] = relationship(back_populates="homepage_placements")


class Category(Base):
    __tablename__ = "categories"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    name: Mapped[str] = mapped_column(unique=True)

class VenueType(Base):
    __tablename__ = "venue_types"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    category_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("categories.id", ondelete="CASCADE"))
    name: Mapped[str]
    category: Mapped["Category"] = relationship()

class UseCase(Base):
    __tablename__ = "use_cases"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    name: Mapped[str] = mapped_column(unique=True)
    venues: Mapped[list["Venue"]] = relationship(secondary="venue_use_cases", back_populates="use_cases")

venue_use_cases = Table(
    "venue_use_cases",
    Base.metadata,
    Column("venue_id", ForeignKey("venues.id", ondelete="CASCADE"), primary_key=True),
    Column("use_case_id", ForeignKey("use_cases.id", ondelete="CASCADE"), primary_key=True),
)


class OwnerBankAccount(Base):
    """Structured beneficiary account for venue owners to receive payout disbursements."""
    __tablename__ = "owner_bank_accounts"
    __table_args__ = (
        Index("idx_owner_bank_accounts_owner", "owner_id", "is_primary"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    account_holder_name: Mapped[str] = mapped_column(String(255))
    account_number: Mapped[str] = mapped_column(EncryptedText)  # see core/crypto.py
    ifsc_code: Mapped[str] = mapped_column(String(16))
    bank_name: Mapped[str | None] = mapped_column(String(128))
    upi_id: Mapped[str | None] = mapped_column(String(128))
    is_verified: Mapped[bool] = mapped_column(server_default=text("false"), default=False)
    is_primary: Mapped[bool] = mapped_column(server_default=text("true"), default=True)
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"))
    updated_at: Mapped[datetime] = mapped_column(server_default=text("now()"))

    owner: Mapped["User"] = relationship(back_populates="bank_accounts")
    payouts: Mapped[list["Payout"]] = relationship(back_populates="bank_account")


class Refund(Base):
    """Structured refund record capturing mode, status, reference, and approval audit."""
    __tablename__ = "refunds"
    __table_args__ = (
        Index("idx_refunds_payment_id", "payment_id"),
        Index("idx_refunds_booking_id", "booking_id"),
        Index(
            "uq_one_processed_refund_per_booking",
            "booking_id",
            unique=True,
            postgresql_where=text("status = 'processed'"),
        ),
        Index(
            "uq_one_processed_refund_per_payment",
            "payment_id",
            unique=True,
            postgresql_where=text("status = 'processed'"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    payment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("payments.id", ondelete="RESTRICT"))
    booking_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("bookings.id", ondelete="RESTRICT"))
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    currency: Mapped[str] = mapped_column(default="INR", server_default="INR")
    reason: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default="pending", server_default="pending")
    mode: Mapped[str] = mapped_column(String(32), default="offline_manual", server_default="offline_manual")
    reference: Mapped[str | None] = mapped_column(String(128))
    requested_by_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    processed_by_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    processed_at: Mapped[datetime | None]
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"))
    updated_at: Mapped[datetime] = mapped_column(server_default=text("now()"))

    payment: Mapped["Payment"] = relationship(back_populates="refunds")
    booking: Mapped["Booking"] = relationship(back_populates="refunds")
    requested_by: Mapped["User | None"] = relationship(foreign_keys=[requested_by_id])
    processed_by: Mapped["User | None"] = relationship(foreign_keys=[processed_by_id])


class LedgerEntry(Base):
    """
    Append-only double-entry financial ledger recording every rupee movement:
    debited accounts, credited accounts, amounts, references, and balance invariants.
    """
    __tablename__ = "ledger_entries"
    __table_args__ = (
        Index("idx_ledger_transaction_id", "transaction_id"),
        Index("idx_ledger_account", "account"),
        Index("idx_ledger_booking_id", "booking_id"),
        Index("idx_ledger_payout_id", "payout_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    transaction_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    entry_type: Mapped[str] = mapped_column(String(64))
    account: Mapped[str] = mapped_column(String(64))
    direction: Mapped[str] = mapped_column(String(10))
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    currency: Mapped[str] = mapped_column(default="INR", server_default="INR")
    booking_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("bookings.id", ondelete="SET NULL"))
    payment_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("payments.id", ondelete="SET NULL"))
    payout_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("payouts.id", ondelete="SET NULL"))
    refund_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("refunds.id", ondelete="SET NULL"))
    actor_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    description: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"))


class HelpCategory(Base):
    """Categorization for help articles (e.g. Booking, Venue Listing, Payments)."""
    __tablename__ = "help_categories"
    __table_args__ = (
        Index("idx_help_categories_audience", "audience", "sort_order"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    slug: Mapped[str] = mapped_column(unique=True)
    name: Mapped[str]
    icon: Mapped[str] = mapped_column(default="help-circle", server_default="help-circle")
    audience: Mapped[str] = mapped_column(default="all", server_default="all")
    sort_order: Mapped[int] = mapped_column(default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"))
    updated_at: Mapped[datetime] = mapped_column(server_default=text("now()"))

    articles: Mapped[list["HelpArticle"]] = relationship(
        back_populates="category",
        order_by="HelpArticle.sort_order",
    )


class HelpArticle(Base):
    """Knowledge base article supporting versioning, translations, and Know More tickets."""
    __tablename__ = "help_articles"
    __table_args__ = (
        Index("idx_help_articles_category_status", "category_id", "status"),
        Index("idx_help_articles_audience_status_lang", "audience", "status", "language"),
        Index("idx_help_articles_group_lang", "group_id", "language"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    slug: Mapped[str] = mapped_column(unique=True)
    title: Mapped[str]
    summary: Mapped[str]
    body_markdown: Mapped[str]
    audience: Mapped[str] = mapped_column(default="all", server_default="all")
    category_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("help_categories.id", ondelete="SET NULL")
    )
    language: Mapped[str] = mapped_column(default="en", server_default="en")
    group_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), server_default=text("gen_random_uuid()")
    )
    status: Mapped[str] = mapped_column(default="draft", server_default="draft")
    sort_order: Mapped[int] = mapped_column(default=0, server_default="0")
    video_url: Mapped[str | None]
    version: Mapped[int] = mapped_column(default=1, server_default="1")
    author_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"))
    updated_at: Mapped[datetime] = mapped_column(server_default=text("now()"))

    category: Mapped["HelpCategory | None"] = relationship(back_populates="articles")
    author: Mapped["User | None"] = relationship()
    revisions: Mapped[list["HelpArticleRevision"]] = relationship(
        back_populates="article",
        cascade="all, delete-orphan",
        order_by="HelpArticleRevision.version.desc()",
    )
    feedbacks: Mapped[list["HelpFeedback"]] = relationship(
        back_populates="article",
        cascade="all, delete-orphan",
    )


class HelpArticleRevision(Base):
    """Historical snapshot of article versions to accurately ground tickets."""
    __tablename__ = "help_article_revisions"
    __table_args__ = (
        Index("idx_help_revisions_article_version", "article_id", "version"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    article_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("help_articles.id", ondelete="CASCADE")
    )
    version: Mapped[int]
    title: Mapped[str]
    summary: Mapped[str]
    body_markdown: Mapped[str]
    editor_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"))

    article: Mapped["HelpArticle"] = relationship(back_populates="revisions")
    editor: Mapped["User | None"] = relationship()


class HelpFeedback(Base):
    """User feedback on articles and sections (Was this helpful? yes/no)."""
    __tablename__ = "help_feedback"
    __table_args__ = (
        Index("idx_help_feedback_article", "article_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    article_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("help_articles.id", ondelete="CASCADE")
    )
    section: Mapped[str | None]
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    helpful: Mapped[bool]
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"))

    article: Mapped["HelpArticle"] = relationship(back_populates="feedbacks")
    user: Mapped["User | None"] = relationship()


class HelpSearchLog(Base):
    """Search queries logged to surface zero-result searches and gaps in documentation."""
    __tablename__ = "help_search_log"
    __table_args__ = (
        Index("idx_help_search_log_created", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    query: Mapped[str]
    result_count: Mapped[int] = mapped_column(default=0, server_default="0")
    role: Mapped[str | None]
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"))


class GuestEnquiry(Base):
    """Guest contact form submissions from unauthenticated users."""
    __tablename__ = "guest_enquiries"
    __table_args__ = (
        Index("idx_guest_enquiries_status", "status", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    name: Mapped[str]
    email: Mapped[str]
    phone: Mapped[str | None]
    subject: Mapped[str]
    message: Mapped[str]
    status: Mapped[str] = mapped_column(default="new", server_default="new")
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"))




class BrokerProfile(Base):
    """A referral partner ("broker"): a field agent who brings venue owners
    onto the platform. Created only from the admin console, never by
    self-signup. The commission terms live here, per broker, and are set by
    the super admin."""

    __tablename__ = "broker_profiles"
    __table_args__ = (
        UniqueConstraint("referral_code", name="uq_broker_referral_code"),
        CheckConstraint("commission_percent BETWEEN 0 AND 100", name="chk_broker_commission_range"),
        CheckConstraint(
            "commission_basis IN ('booking_amount', 'platform_commission')",
            name="chk_broker_commission_basis",
        ),
        CheckConstraint("status IN ('active', 'paused')", name="chk_broker_status"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    referral_code: Mapped[str]
    commission_percent: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("0.00"))
    # 'booking_amount'      -> rate applies to the money received for the booking
    # 'platform_commission' -> rate applies to GroundKart's own commission on it
    commission_basis: Mapped[str] = mapped_column(default="booking_amount", server_default="booking_amount")
    # 'paused' stops NEW attributions and NEW commissions; history and any
    # balance already earned stay exactly as they are.
    status: Mapped[str] = mapped_column(default="active", server_default="active")
    company_name: Mapped[str | None]
    city: Mapped[str | None]
    payout_method: Mapped[str | None]
    payout_details: Mapped[str | None] = mapped_column(EncryptedText, nullable=True)
    notes: Mapped[str | None]
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"))
    updated_at: Mapped[datetime] = mapped_column(server_default=text("now()"))

    user: Mapped["User"] = relationship(back_populates="broker_profile", foreign_keys=[user_id])


class BrokerPayout(Base):
    """One settlement to a broker. Immutable once written: a correction is a
    new row, never an edit."""

    __tablename__ = "broker_payouts"
    __table_args__ = (
        CheckConstraint("amount > 0", name="chk_broker_payout_positive"),
        Index("idx_broker_payouts_broker", "broker_id", "paid_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    broker_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    method: Mapped[str | None]
    reference: Mapped[str | None]
    notes: Mapped[str | None]
    paid_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    paid_at: Mapped[datetime] = mapped_column(server_default=text("now()"))
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"))

    items: Mapped[list["BrokerPayoutItem"]] = relationship(
        back_populates="payout", cascade="all, delete-orphan"
    )


class BrokerCommission(Base):
    """One row per confirmed payment at a referred venue.

    Three amounts, never overwritten into one another:
      amount          what the broker earned when the payment was confirmed
      reversed_amount what refunds have since taken back
      paid_amount     what has actually been settled to the broker
    Balance due on a row = amount - reversed_amount - paid_amount. It can be
    negative (a refund after the broker was already paid); that shortfall is
    carried and netted off the next settlement.

    A row becomes payable once event_date has passed — the same idea as the
    owner payout holdback: nobody is paid for an event that has not happened.
    """

    __tablename__ = "broker_commissions"
    __table_args__ = (
        UniqueConstraint("payment_id", name="uq_broker_commission_per_payment"),
        CheckConstraint("amount >= 0", name="chk_broker_commission_nonneg"),
        CheckConstraint(
            "reversed_amount >= 0 AND reversed_amount <= amount",
            name="chk_broker_commission_reversal_range",
        ),
        Index("idx_broker_commissions_broker", "broker_id", "event_date"),
        Index("idx_broker_commissions_venue", "venue_id"),
        Index("idx_broker_commissions_booking", "booking_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    broker_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    venue_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("venues.id", ondelete="RESTRICT"))
    booking_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("bookings.id", ondelete="RESTRICT"))
    payment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("payments.id", ondelete="RESTRICT"))
    event_date: Mapped[date_]
    basis: Mapped[str]
    basis_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    rate: Mapped[Decimal] = mapped_column(Numeric(5, 2))
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    reversed_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0.00"), server_default="0")
    paid_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0.00"), server_default="0")
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"))
    updated_at: Mapped[datetime] = mapped_column(server_default=text("now()"))

    venue: Mapped["Venue"] = relationship()
    booking: Mapped["Booking"] = relationship()

    @property
    def net_amount(self) -> Decimal:
        return self.amount - self.reversed_amount

    @property
    def balance_due(self) -> Decimal:
        return self.amount - self.reversed_amount - self.paid_amount


class BrokerPayoutItem(Base):
    """Which commission rows a settlement covered, and for how much each."""

    __tablename__ = "broker_payout_items"

    payout_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("broker_payouts.id", ondelete="CASCADE"), primary_key=True
    )
    commission_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("broker_commissions.id", ondelete="RESTRICT"), primary_key=True
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))

    payout: Mapped["BrokerPayout"] = relationship(back_populates="items")


class SiteBanner(Base):
    """Admin-managed promotional banner. Several can be live at once in the
    same placement; the site rotates through them in priority order.

    Scheduling follows HomepagePlacement: NULL start = show immediately,
    NULL end = no expiry."""

    __tablename__ = "site_banners"
    __table_args__ = (
        CheckConstraint(
            "placement IN ('home_hero', 'home_strip', 'search_top')", name="chk_banner_placement"
        ),
        CheckConstraint(
            "start_at IS NULL OR end_at IS NULL OR start_at < end_at", name="chk_banner_window"
        ),
        Index(
            "idx_site_banners_placement",
            "placement",
            "priority",
            postgresql_where=text("enabled = TRUE"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    placement: Mapped[str] = mapped_column(default="home_hero", server_default="home_hero")
    title: Mapped[str]
    subtitle: Mapped[str | None]
    image_url: Mapped[str | None]
    image_storage_key: Mapped[str | None]
    cta_label: Mapped[str | None]
    cta_url: Mapped[str | None]
    enabled: Mapped[bool] = mapped_column(default=True, server_default=text("true"))
    priority: Mapped[int] = mapped_column(default=0, server_default="0")
    start_at: Mapped[datetime | None]
    end_at: Mapped[datetime | None]
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"))
    updated_at: Mapped[datetime] = mapped_column(server_default=text("now()"))


class ConsentRecord(Base):
    """Proof of what a person agreed to, which version, and when (DPDP
    s.6(10) puts the burden of proof on the Data Fiduciary). Append-only:
    a withdrawal is a new row with action='withdrawn'. ip_hash is a keyed
    HMAC of the client IP, never the IP itself."""

    __tablename__ = "consent_records"
    __table_args__ = (
        Index("idx_consent_records_user", "user_id", "created_at"),
        Index("idx_consent_records_booking", "booking_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    booking_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("bookings.id", ondelete="SET NULL"), nullable=True)
    purpose: Mapped[str]  # terms | privacy_notice | age_18_plus | external_media
    action: Mapped[str] = mapped_column(default="given", server_default="given")  # given | withdrawn
    notice_version: Mapped[str | None]
    terms_version: Mapped[str | None]
    source: Mapped[str | None]  # signup | guest_checkout | checkout | my_data | admin
    ip_hash: Mapped[str | None]
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"))


class DataRequest(Base):
    """A Data Principal rights request (DPDP s.11-14): summary, correction,
    erasure, withdrawal, nominee. Every request has a number and a due
    date (30 days, inside the 90-day ceiling of DPDP Rules r.14(3)), and
    opens a linked support ticket so it shows up in the admin SLA views."""

    __tablename__ = "data_requests"
    __table_args__ = (Index("idx_data_requests_status_due", "status", "due_at"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    request_number: Mapped[str] = mapped_column(unique=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    booking_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("bookings.id", ondelete="SET NULL"), nullable=True)
    type: Mapped[str]  # summary | correction | erasure | withdraw_consent | nominee | other
    status: Mapped[str] = mapped_column(default="open", server_default="open")  # open | completed | rejected
    details: Mapped[str | None]
    result: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    ticket_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("support_tickets.id", ondelete="SET NULL"), nullable=True)
    due_at: Mapped[datetime]
    completed_at: Mapped[datetime | None]
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"))
    updated_at: Mapped[datetime] = mapped_column(server_default=text("now()"))


class Nominee(Base):
    """DPDP s.14: a person the user names to exercise their rights after
    death or incapacity. One per user."""

    __tablename__ = "nominees"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    name: Mapped[str]
    relationship_to_user: Mapped[str | None] = mapped_column("relationship")
    email: Mapped[str | None]
    phone: Mapped[str | None]
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"))
    updated_at: Mapped[datetime] = mapped_column(server_default=text("now()"))


class BreachIncident(Base):
    """Incident register (docs/compliance/drafts/breach-response-plan.md).
    Deadlines are computed from detected_at when the row is created:
    CERT-In 6 hours (Directions 2022), Board detailed report 72 hours (DPDP
    Rules r.7(2)(b)). Never deleted."""

    __tablename__ = "breach_incidents"
    __table_args__ = (Index("idx_breach_incidents_status", "status", "detected_at"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    reference: Mapped[str] = mapped_column(unique=True)
    title: Mapped[str]
    description: Mapped[str]
    detected_at: Mapped[datetime]
    occurred_at: Mapped[datetime | None]
    data_categories: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    affected_count: Mapped[int | None]
    is_cyber_incident: Mapped[bool] = mapped_column(default=True, server_default=text("true"))
    is_personal_data_breach: Mapped[bool] = mapped_column(default=True, server_default=text("true"))
    status: Mapped[str] = mapped_column(default="open", server_default="open")  # open | contained | closed
    cert_in_due_at: Mapped[datetime]
    board_report_due_at: Mapped[datetime]
    cert_in_reported_at: Mapped[datetime | None]
    board_initial_reported_at: Mapped[datetime | None]
    board_report_submitted_at: Mapped[datetime | None]
    users_notified_at: Mapped[datetime | None]
    containment_notes: Mapped[str | None]
    remediation_notes: Mapped[str | None]
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    closed_at: Mapped[datetime | None]
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"))
    updated_at: Mapped[datetime] = mapped_column(server_default=text("now()"))


class SiteContent(Base):
    """Published website copy, as partial overrides of the defaults in
    frontend/src/lib/homepageContent.ts. Super admin only."""

    __tablename__ = "site_content"

    key: Mapped[str] = mapped_column(primary_key=True)
    data: Mapped[dict] = mapped_column(JSONB, default=dict, server_default=text("'{}'::jsonb"))
    version: Mapped[int] = mapped_column(default=0, server_default=text("0"))
    updated_at: Mapped[datetime] = mapped_column(server_default=text("now()"))
    updated_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)


class SiteContentRevision(Base):
    __tablename__ = "site_content_revisions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    key: Mapped[str]
    version: Mapped[int]
    data: Mapped[dict] = mapped_column(JSONB)
    note: Mapped[str | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"))
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)


class SiteAsset(Base):
    """An image the super admin uploaded for the website (hero, occasion
    cards, sections). Stored as optimised WebP through the file storage."""

    __tablename__ = "site_assets"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    url: Mapped[str] = mapped_column(unique=True)
    storage_key: Mapped[str]
    label: Mapped[str]
    alt_text: Mapped[str] = mapped_column(default="", server_default=text("''"))
    width: Mapped[int | None] = mapped_column(nullable=True)
    height: Mapped[int | None] = mapped_column(nullable=True)
    size_bytes: Mapped[int]
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"))
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

