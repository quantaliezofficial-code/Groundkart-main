"""Request/response shapes for team, referral partners, banners and records."""
from __future__ import annotations

import re
import uuid
from datetime import date, datetime, time
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


def _clean_phone(value: str) -> str:
    raw = str(value).strip()
    cleaned = re.sub(r"[\s\-\(\)]", "", raw)
    digits = cleaned.lstrip("+")
    if not digits.isdigit():
        raise ValueError("Phone number can only contain digits, spaces, hyphens and a leading +")
    national = digits[2:] if (len(digits) == 12 and digits.startswith("91")) else digits
    if len(national) < 10:
        raise ValueError("Phone number must have at least 10 digits")
    if len(digits) > 15:
        raise ValueError("Phone number cannot exceed 15 digits")
    return cleaned


class _StaffAccountBase(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    phone: str
    email: EmailStr | None = None

    @field_validator("name")
    @classmethod
    def _name(cls, v: str) -> str:
        v = " ".join(v.split())
        if len(v) < 2:
            raise ValueError("Enter the person's full name")
        return v

    @field_validator("phone")
    @classmethod
    def _phone(cls, v: str) -> str:
        return _clean_phone(v)

    @field_validator("email")
    @classmethod
    def _email(cls, v):
        return str(v).strip().lower() if v else None


# ----- Team ----------------------------------------------------------------


class AdminCreateRequest(_StaffAccountBase):
    pass


class TeamMemberView(BaseModel):
    id: uuid.UUID
    name: str
    email: str | None
    phone: str
    is_super_admin: bool
    suspended_at: datetime | None
    suspension_reason: str | None
    created_at: datetime
    created_by: uuid.UUID | None
    action_count: int
    last_action_at: datetime | None


class AccountCreatedResponse(BaseModel):
    """setup_url is a one-time bearer link (valid 24h) the creator hands to
    the new account holder so they can choose their own password. It is
    returned once, in this response only, and is never stored or logged."""

    id: uuid.UUID
    name: str
    setup_url: str
    setup_url_expires_in_hours: int = 24


# ----- Referral partners ----------------------------------------------------

CommissionBasis = Literal["booking_amount", "platform_commission"]


class BrokerCreateRequest(_StaffAccountBase):
    commission_percent: Decimal | None = Field(default=None, ge=0, le=100, decimal_places=2)
    commission_basis: CommissionBasis | None = None
    company_name: str | None = Field(default=None, max_length=160)
    city: str | None = Field(default=None, max_length=80)
    payout_method: str | None = Field(default=None, max_length=40)
    payout_details: str | None = Field(default=None, max_length=300)
    notes: str | None = Field(default=None, max_length=1000)


class BrokerUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    commission_percent: Decimal | None = Field(default=None, ge=0, le=100, decimal_places=2)
    commission_basis: CommissionBasis | None = None
    status: Literal["active", "paused"] | None = None
    company_name: str | None = Field(default=None, max_length=160)
    city: str | None = Field(default=None, max_length=80)
    payout_method: str | None = Field(default=None, max_length=40)
    payout_details: str | None = Field(default=None, max_length=300)
    notes: str | None = Field(default=None, max_length=1000)


class WalletView(BaseModel):
    earned: Decimal
    pending: Decimal
    payable: Decimal
    paid: Decimal
    reversed: Decimal
    commission_count: int


class BrokerView(BaseModel):
    id: uuid.UUID
    name: str
    email: str | None
    phone: str
    suspended_at: datetime | None
    referral_code: str
    commission_percent: Decimal
    commission_basis: str
    status: str
    company_name: str | None
    city: str | None
    payout_method: str | None
    payout_details: str | None
    notes: str | None
    created_at: datetime
    venue_count: int
    active_venue_count: int
    wallet: WalletView


class BrokerCreatedResponse(BaseModel):
    broker: BrokerView
    setup_url: str
    setup_url_expires_in_hours: int = 24


class BrokerSelfView(BaseModel):
    """What a broker sees about their own account. No internal notes."""

    id: uuid.UUID
    name: str
    email: str | None
    phone: str
    referral_code: str
    referral_link: str
    commission_percent: Decimal
    commission_basis: str
    status: str
    company_name: str | None
    city: str | None
    payout_method: str | None
    payout_details: str | None
    venue_count: int
    active_venue_count: int
    wallet: WalletView


class BrokerSelfUpdateRequest(BaseModel):
    company_name: str | None = Field(default=None, max_length=160)
    city: str | None = Field(default=None, max_length=80)
    payout_method: str | None = Field(default=None, max_length=40)
    payout_details: str | None = Field(default=None, max_length=300)


class ReferredVenueView(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    category: str
    city: str
    status: str
    review_note: str | None
    base_price: Decimal
    unit_type: str
    owner_name: str
    owner_phone: str | None
    referral_code: str | None
    referred_at: datetime | None
    created_at: datetime
    booking_count: int
    awaiting_payment_count: int
    paid_booking_count: int
    amount_received: Decimal
    commission_earned: Decimal


class ReferredBookingView(BaseModel):
    id: uuid.UUID
    reference: str
    venue_id: uuid.UUID
    venue_name: str
    event_date: date
    start_time: time | None
    end_time: time | None
    status: str
    amount: Decimal
    payment_state: str
    created_at: datetime
    confirmed_at: datetime | None
    commission_rate: Decimal | None
    commission_amount: Decimal | None
    commission_status: str | None


class CommissionView(BaseModel):
    id: uuid.UUID
    broker_id: uuid.UUID
    broker_name: str
    venue_id: uuid.UUID
    venue_name: str
    booking_id: uuid.UUID
    booking_reference: str
    event_date: date
    basis: str
    basis_amount: Decimal
    rate: Decimal
    amount: Decimal
    reversed_amount: Decimal
    paid_amount: Decimal
    net_amount: Decimal
    balance_due: Decimal
    status: str
    created_at: datetime


class BrokerPayoutRequest(BaseModel):
    expected_amount: Decimal = Field(gt=0, decimal_places=2)
    method: str | None = Field(default=None, max_length=40)
    reference: str | None = Field(default=None, max_length=120)
    notes: str | None = Field(default=None, max_length=500)


class BrokerPayoutView(BaseModel):
    id: uuid.UUID
    broker_id: uuid.UUID
    broker_name: str
    amount: Decimal
    method: str | None
    reference: str | None
    notes: str | None
    paid_at: datetime


class ReferralCodeRequest(BaseModel):
    code: str = Field(min_length=4, max_length=24)


class ReferralCodeCheckResponse(BaseModel):
    valid: bool
    partner_name: str | None = None


class VenueReferralView(BaseModel):
    venue_id: uuid.UUID
    referral_code: str | None
    partner_name: str | None
    referred_at: datetime | None
    locked: bool


class AdminVenueBrokerRequest(BaseModel):
    broker_id: uuid.UUID | None = None


# ----- Banners ---------------------------------------------------------------

BannerPlacement = Literal["home_hero", "home_strip", "search_top"]


class BannerCreateRequest(BaseModel):
    placement: BannerPlacement = "home_hero"
    title: str = Field(min_length=2, max_length=90)
    subtitle: str | None = Field(default=None, max_length=180)
    cta_label: str | None = Field(default=None, max_length=32)
    cta_url: str | None = Field(default=None, max_length=300)
    enabled: bool = True
    priority: int = Field(default=0, ge=0, le=999)
    start_at: datetime | None = None
    end_at: datetime | None = None


class BannerUpdateRequest(BaseModel):
    placement: BannerPlacement | None = None
    title: str | None = Field(default=None, min_length=2, max_length=90)
    subtitle: str | None = Field(default=None, max_length=180)
    cta_label: str | None = Field(default=None, max_length=32)
    cta_url: str | None = Field(default=None, max_length=300)
    enabled: bool | None = None
    priority: int | None = Field(default=None, ge=0, le=999)
    start_at: datetime | None = None
    end_at: datetime | None = None


class BannerView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    placement: str
    title: str
    subtitle: str | None
    image_url: str | None
    cta_label: str | None
    cta_url: str | None
    enabled: bool
    priority: int
    start_at: datetime | None
    end_at: datetime | None
    created_at: datetime
    updated_at: datetime


class PublicBannerView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    placement: str
    title: str
    subtitle: str | None
    image_url: str | None
    cta_label: str | None
    cta_url: str | None


# ----- Records ---------------------------------------------------------------


class VenueRegisterRow(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    category: str
    city: str
    state: str | None
    address: str
    capacity: int | None
    unit_type: str
    base_price: Decimal
    status: str
    status_note: str | None
    owner_id: uuid.UUID
    owner_name: str
    owner_phone: str | None
    owner_email: str | None
    broker_id: uuid.UUID | None
    broker_name: str | None
    referral_code: str | None
    referred_at: datetime | None
    listed_at: datetime
    approved_at: datetime | None
    updated_at: datetime
    media_count: int
    booking_count: int
    confirmed_booking_count: int
    amount_received: Decimal
    platform_commission: Decimal
    avg_rating: Decimal


class BookingRegisterRow(BaseModel):
    id: uuid.UUID
    reference: str
    status: str
    booked_at: datetime
    confirmed_at: datetime | None
    cancelled_at: datetime | None
    cancellation_reason: str | None
    venue_id: uuid.UUID
    venue_name: str
    venue_category: str
    venue_city: str
    owner_id: uuid.UUID
    owner_name: str
    event_date: date
    start_time: time | None
    end_time: time | None
    rental_mode: str | None
    guest_count: int | None
    customer_type: str
    customer_name: str | None
    customer_phone: str | None
    customer_email: str | None
    amount: Decimal
    currency: str
    payment_received: bool
    payment_method: str | None
    payment_gateway: str | None
    payment_reference: str | None
    payment_recorded_at: datetime | None
    refund_amount: Decimal
    amount_received: Decimal
    platform_commission: Decimal
    owner_share: Decimal
    broker_id: uuid.UUID | None
    broker_name: str | None
    broker_commission_rate: Decimal | None
    broker_commission: Decimal | None
    broker_commission_status: str | None


class HistoryEvent(BaseModel):
    at: datetime
    action: str
    label: str
    actor_name: str | None
    actor_role: str | None
    details: dict


class VenueHistoryResponse(BaseModel):
    venue_id: uuid.UUID
    venue_name: str
    status: str
    timeline: list[HistoryEvent]
    booking_count: int
    first_booking_at: datetime | None
    last_booking_at: datetime | None


class ExportInfo(BaseModel):
    kind: str
    title: str
    row_count: int
    columns: list[str]
