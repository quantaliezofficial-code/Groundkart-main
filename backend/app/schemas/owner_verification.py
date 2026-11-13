import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.modules.core.crypto import mask


class OwnerVerificationResponse(BaseModel):
    id: uuid.UUID
    status: str
    business_name: str | None
    identification_type: str | None = None
    identification_number: str | None = None
    pan: str | None = None
    gstin: str | None = None
    rejection_reason: str | None
    created_at: datetime
    reviewed_at: datetime | None

    model_config = {"from_attributes": True}

    # Stored encrypted; only ever returned masked (DPDP Rules r.6(1)(a)).
    @field_validator("identification_number", "pan", "gstin", mode="after")
    @classmethod
    def _mask(cls, v: str | None) -> str | None:
        return mask(v)


class RejectVerificationRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=1000)


class ApproveOwnerVerificationRequest(BaseModel):
    """Optional body for the owner verification approval endpoint.
    When provided, the admin can trigger a password action alongside
    approval (e.g. send a reset link or force a password change so the
    newly approved owner sets a strong password on first login)."""
    password_action: str | None = None  # "link" | "force" | None

