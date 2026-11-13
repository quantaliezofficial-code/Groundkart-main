"""Business facts shown on the legal pages, footer and checkout.

The owner enters them once (Admin → Settings → Legal and business details,
super admin only). Anything not entered is returned as null and the
frontend shows the matching ``[[OWNER TO FILL: <label>]]`` placeholder, so
no business fact is ever invented (DECISIONS_NEEDED.md D-01 to D-05,
D-15, D-16, D-22)."""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.core.config_service import get_system_config
from app.modules.privacy.versions import NOTICE_DATE, NOTICE_VERSION, TERMS_VERSION

# Placeholder label (exactly as written in frontend/src/content/legal/*.md)
# -> legal_profile key.
PLACEHOLDER_FIELDS: dict[str, str] = {
    "legal company name": "legal_name",
    "CIN": "cin",
    "registered office address": "registered_address",
    "Grievance Officer name": "grievance_officer_name",
    "designation": "grievance_officer_designation",
    "grievance email": "grievance_email",
    "grievance phone": "grievance_phone",
    "customer care phone": "customer_care_phone",
    "jurisdiction city": "jurisdiction_city",
    "hosting provider and data-centre region": "hosting_provider",
    "accepted payment modes": "payment_modes",
    "tax statement": "tax_statement",
    "refund processing time": "refund_processing_time",
}

FIELDS: tuple[str, ...] = (
    "legal_name",
    "cin",
    "registered_address",
    "grievance_officer_name",
    "grievance_officer_designation",
    "grievance_email",
    "grievance_phone",
    "grievance_hours",
    "customer_care_phone",
    "customer_care_hours",
    "jurisdiction_city",
    "hosting_provider",
    "payment_modes",
    "tax_statement",
    "refund_processing_time",
)


async def public_profile(session: AsyncSession) -> dict:
    config = await get_system_config(session)
    stored = config.legal_profile or {}
    profile = {key: (stored.get(key) or None) for key in FIELDS}
    profile.update(
        notice_version=NOTICE_VERSION,
        terms_version=TERMS_VERSION,
        notice_date=NOTICE_DATE,
        platform_fee=0,
        booking_terms={
            "hold_minutes": config.booking_hold_duration_minutes,
            "full_refund_hours": config.cancellation_full_refund_hours,
            "partial_refund_hours": config.cancellation_partial_refund_hours,
            "partial_refund_percent": config.cancellation_partial_refund_percent,
        },
        placeholders=PLACEHOLDER_FIELDS,
        missing=[key for key in FIELDS if not profile.get(key)],
    )
    return profile


def clean_update(data: dict) -> dict:
    out = {}
    for key, value in data.items():
        if key not in FIELDS:
            continue
        if value is None:
            out[key] = None
            continue
        value = str(value).strip()
        out[key] = value[:500] or None
    return out
