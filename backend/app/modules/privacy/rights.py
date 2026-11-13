"""Data Principal rights (DPDP Act s.11-14; Rules r.14): summary export,
correction, erasure, consent withdrawal and nominee, with numbered requests
and due dates."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.core import (
    Booking,
    BrokerProfile,
    ConsentRecord,
    DataRequest,
    Nominee,
    Notification,
    OwnerBankAccount,
    OwnerVerification,
    Payment,
    Review,
    SupportTicket,
    TicketEvent,
    User,
    Venue,
)
from app.modules.core.crypto import mask
from app.modules.privacy import consent as consent_service
from app.modules.support import sla

REQUEST_TYPES = ("summary", "correction", "erasure", "withdraw_consent", "nominee", "other")


async def _new_request(session: AsyncSession, user_id: uuid.UUID | None, type_: str, details: str | None, booking_id=None) -> DataRequest:
    now = datetime.now(timezone.utc)
    number = await sla.next_number(session, "GK-D", "data_request_number_seq", at=now)
    req = DataRequest(
        request_number=number,
        user_id=user_id,
        booking_id=booking_id,
        type=type_,
        details=details,
        due_at=now + sla.DATA_REQUEST_DUE,
        created_at=now,
        updated_at=now,
    )
    session.add(req)
    await session.flush()
    return req


async def open_request(session: AsyncSession, user_id: uuid.UUID, type_: str, details: str | None) -> DataRequest:
    """A request a person makes that needs the team (e.g. a correction we
    cannot do automatically). Opens a linked data_request ticket so it shows
    in the admin SLA views. Caller owns the transaction."""
    req = await _new_request(session, user_id, type_, details)
    ticket = SupportTicket(
        subject=f"Data request {req.request_number}: {type_.replace('_', ' ')}",
        description=details or type_,
        status="open",
        category="data_request",
        priority="high",
        creator_id=user_id,
    )
    session.add(ticket)
    await session.flush()
    await sla.stamp_new_ticket(session, ticket)
    ticket.resolve_due_at = req.due_at
    session.add(TicketEvent(ticket_id=ticket.id, event_type="created", actor_id=user_id, new_status="open", comment=details))
    req.ticket_id = ticket.id
    return req


async def record_completed_request(session: AsyncSession, user_id: uuid.UUID | None, type_: str, result: dict, booking_id=None) -> DataRequest:
    req = await _new_request(session, user_id, type_, None, booking_id=booking_id)
    req.status = "completed"
    req.completed_at = datetime.now(timezone.utc)
    req.result = result
    return req


def request_view(req: DataRequest) -> dict:
    return {
        "request_number": req.request_number,
        "type": req.type,
        "status": req.status,
        "details": req.details,
        "due_at": req.due_at.isoformat() if req.due_at else None,
        "completed_at": req.completed_at.isoformat() if req.completed_at else None,
        "created_at": req.created_at.isoformat() if req.created_at else None,
        "result": req.result,
    }


RECIPIENTS = [
    {"recipient": "Venue owners of the venues you booked", "what": "Your name, phone, email, booking details and notes", "why": "To host your booking"},
    {"recipient": "Hosting provider (processor)", "what": "All data in this file", "why": "Stores GroundKart's database, files and logs"},
    {"recipient": "Banks and UPI providers", "what": "Payment and refund amounts and references", "why": "To move money you pay or receive"},
]


def _iso(value):
    return value.isoformat() if hasattr(value, "isoformat") else value


async def export(session: AsyncSession, user_id: uuid.UUID) -> dict:
    user = (await session.execute(select(User).where(User.id == user_id))).scalar_one()
    bookings = (
        await session.execute(
            select(Booking).where(Booking.customer_id == user_id).options(selectinload(Booking.inventory_unit)).order_by(Booking.created_at)
        )
    ).scalars().all()
    booking_ids = [b.id for b in bookings]
    payments = (await session.execute(select(Payment).where(Payment.booking_id.in_(booking_ids)))).scalars().all() if booking_ids else []
    tickets = (
        await session.execute(select(SupportTicket).where(SupportTicket.creator_id == user_id).options(selectinload(SupportTicket.events)))
    ).scalars().all()
    reviews = (await session.execute(select(Review).where(Review.user_id == user_id))).scalars().all()
    notes = (await session.execute(select(Notification).where(Notification.user_id == user_id).order_by(Notification.created_at))).scalars().all()
    consents = await consent_service.list_for_user(session, user_id)
    nominee = (await session.execute(select(Nominee).where(Nominee.user_id == user_id))).scalar_one_or_none()
    requests = (await session.execute(select(DataRequest).where(DataRequest.user_id == user_id))).scalars().all()
    verifications = (await session.execute(select(OwnerVerification).where(OwnerVerification.user_id == user_id))).scalars().all()
    banks = (await session.execute(select(OwnerBankAccount).where(OwnerBankAccount.owner_id == user_id))).scalars().all()
    venues = (await session.execute(select(Venue).where(Venue.owner_id == user_id))).scalars().all()
    broker = (await session.execute(select(BrokerProfile).where(BrokerProfile.user_id == user_id))).scalar_one_or_none()

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "about": "Everything GroundKart holds about you, as required by the Digital Personal Data Protection Act, 2023 (s.11). "
        "Identity and bank numbers are shown masked; ask the Grievance Officer if you need them in full.",
        "profile": {
            "id": str(user.id),
            "name": user.name,
            "email": user.email,
            "phone": user.phone,
            "role": user.role,
            "created_at": _iso(user.created_at),
            "last_active_at": _iso(user.last_active_at),
            "two_factor_enabled": user.totp_enabled_at is not None,
        },
        "bookings": [
            {
                "id": str(b.id),
                "venue_name": b.venue_name,
                "status": b.status,
                "date": _iso(b.inventory_unit.date) if b.inventory_unit else None,
                "amount": str(b.amount),
                "guest_count": b.guest_count,
                "customer_notes": b.customer_notes,
                "created_at": _iso(b.created_at),
            }
            for b in bookings
        ],
        "payments": [{"booking_id": str(p.booking_id), "amount": str(p.amount), "status": p.status, "created_at": _iso(p.created_at)} for p in payments],
        "support_tickets": [
            {
                "ticket_number": t.ticket_number,
                "subject": t.subject,
                "description": t.description,
                "status": t.status,
                "created_at": _iso(t.created_at),
                "messages": [{"comment": e.comment, "at": _iso(e.created_at)} for e in t.events if not e.internal and e.comment],
            }
            for t in tickets
        ],
        "reviews": [{"venue_id": str(r.venue_id), "rating": r.rating, "content": r.content, "created_at": _iso(r.created_at)} for r in reviews],
        "notifications": [{"message": n.message, "created_at": _iso(n.created_at), "read_at": _iso(n.read_at)} for n in notes],
        "consents": [consent_service.view(c) for c in consents],
        "nominee": None if nominee is None else {"name": nominee.name, "relationship": nominee.relationship_to_user, "email": nominee.email, "phone": nominee.phone},
        "data_requests": [request_view(r) for r in requests],
        "owner_verifications": [
            {
                "status": v.status,
                "business_name": v.business_name,
                "identification_type": v.identification_type,
                "identification_number": mask(v.identification_number),
                "pan": mask(v.pan),
                "gstin": mask(v.gstin),
                "submitted_at": _iso(v.created_at),
            }
            for v in verifications
        ],
        "bank_accounts": [{"holder": a.account_holder_name, "account_number": mask(a.account_number), "ifsc": a.ifsc_code, "upi_id": a.upi_id} for a in banks],
        "venues": [{"id": str(v.id), "name": v.name, "status": v.status, "address": v.address, "city": v.city} for v in venues],
        "referral_partner": None if broker is None else {"referral_code": broker.referral_code, "company_name": broker.company_name, "payout_method": broker.payout_method},
        "recipients": RECIPIENTS,
    }
