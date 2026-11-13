"""Consent and agreement records (DPDP s.6, s.6(10); E-Commerce r.4(9))."""
from __future__ import annotations

import uuid

from fastapi import Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.core import ConsentRecord
from app.modules.core.crypto import keyed_hash
from app.modules.privacy.versions import NOTICE_VERSION, TERMS_VERSION

# What GroundKart asks people to agree to. There is deliberately no
# marketing purpose (owner decision D-11).
SERVICE_PURPOSES = ("terms", "privacy_notice", "age_18_plus")

AGE_REQUIRED_MESSAGE = "Please confirm you are 18 years or older. GroundKart is for adults only."


def client_ip_hash(request: Request | None) -> str | None:
    if request is None:
        return None
    from app.modules.auth.service import get_client_ip

    ip = get_client_ip(request)
    return keyed_hash(ip, "consent-ip") if ip else None


def add_records(
    session: AsyncSession,
    *,
    purposes: tuple[str, ...] | list[str],
    source: str,
    request: Request | None = None,
    user_id: uuid.UUID | None = None,
    booking_id: uuid.UUID | None = None,
    action: str = "given",
    notice_version: str | None = None,
    terms_version: str | None = None,
) -> list[ConsentRecord]:
    ip_hash = client_ip_hash(request)
    rows = [
        ConsentRecord(
            user_id=user_id,
            booking_id=booking_id,
            purpose=purpose,
            action=action,
            notice_version=notice_version or NOTICE_VERSION,
            terms_version=terms_version or TERMS_VERSION,
            source=source,
            ip_hash=ip_hash,
        )
        for purpose in purposes
    ]
    session.add_all(rows)
    return rows


async def list_for_user(session: AsyncSession, user_id: uuid.UUID) -> list[ConsentRecord]:
    result = await session.execute(
        select(ConsentRecord).where(ConsentRecord.user_id == user_id).order_by(ConsentRecord.created_at)
    )
    return list(result.scalars().all())


def view(row: ConsentRecord) -> dict:
    return {
        "id": str(row.id),
        "purpose": row.purpose,
        "action": row.action,
        "notice_version": row.notice_version,
        "terms_version": row.terms_version,
        "source": row.source,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }
