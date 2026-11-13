"""Grievance clocks for support tickets.

| Category | Acknowledge | Resolve | Source |
| content_report | 24 h | 15 days | IT Intermediary Rules 2021 r.3(2) |
| everything else | 48 h | 30 days | E-Commerce Rules 2020 r.4(5); SPDI r.5(9) |
| data_request | 48 h | 30 days | inside DPDP Rules 2025 r.14(3) 90-day ceiling |
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

CLOCKS: dict[str, tuple[timedelta, timedelta]] = {
    "content_report": (timedelta(hours=24), timedelta(days=15)),
}
DEFAULT_CLOCK = (timedelta(hours=48), timedelta(days=30))
DATA_REQUEST_DUE = timedelta(days=30)
DPDP_CEILING = timedelta(days=90)

CONTACT_CATEGORIES = {
    "general": "general",
    "booking": "general",
    "payment": "billing",
    "billing": "billing",
    "venue": "venue_issue",
    "grievance": "grievance",
    "content_report": "content_report",
    "content": "content_report",
    "privacy": "data_request",
    "data_request": "data_request",
    "partnership": "general",
    "other": "general",
}


def due_dates(category: str, created_at: datetime) -> tuple[datetime, datetime]:
    ack, resolve = CLOCKS.get(category, DEFAULT_CLOCK)
    resolve = min(resolve, DPDP_CEILING)
    return created_at + ack, created_at + resolve


SEQUENCES = frozenset({"ticket_number_seq", "data_request_number_seq", "incident_number_seq"})


async def next_number(session: AsyncSession, prefix: str, sequence: str, width: int = 4, at: datetime | None = None) -> str:
    if sequence not in SEQUENCES:  # never build SQL from anything but these names
        raise ValueError(f"unknown sequence {sequence!r}")
    seq = (await session.execute(text("SELECT nextval(CAST(:seq AS regclass))"), {"seq": sequence})).scalar_one()
    stamp = (at or datetime.now(timezone.utc)).strftime("%y%m")
    return f"{prefix}-{stamp}-{int(seq):0{width}d}"


def sla_state(ticket, now: datetime | None = None) -> str:
    now = now or datetime.now(timezone.utc)
    if ticket.status in ("resolved", "closed"):
        return "done"
    if ticket.resolve_due_at and now > ticket.resolve_due_at:
        return "resolve_overdue"
    if ticket.ack_due_at and not ticket.acknowledged_at and now > ticket.ack_due_at:
        return "ack_overdue"
    return "on_track"


async def stamp_new_ticket(session: AsyncSession, ticket) -> None:
    """Gives a freshly created (flushed or not) ticket its number and clocks."""
    now = datetime.now(timezone.utc)
    created = ticket.created_at or now
    if not ticket.ticket_number:
        ticket.ticket_number = await next_number(session, "GK-T", "ticket_number_seq", at=created)
    ticket.ack_due_at, ticket.resolve_due_at = due_dates(ticket.category or "general", created)
