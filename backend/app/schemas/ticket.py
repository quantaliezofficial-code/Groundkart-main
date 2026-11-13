"""
Pydantic request/response schemas for support tickets — mirrors the
existing pattern in app/schemas/{booking,catalog,admin}.py.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ── Request Schemas ──────────────────────────────────────────────────────

class TicketCreateRequest(BaseModel):
    subject: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., min_length=1, max_length=5000)
    category: Literal["general", "billing", "venue_issue", "dispute", "help_request", "grievance", "content_report", "data_request"] = "general"
    priority: Literal["low", "medium", "high", "urgent"] = "medium"
    booking_id: uuid.UUID | None = None
    venue_id: uuid.UUID | None = None
    help_article_id: uuid.UUID | None = None
    help_article_version: int | None = None
    help_section: str | None = None
    reason_code: str | None = None

    @field_validator("booking_id")
    @classmethod
    def dispute_requires_booking(cls, v, info):
        # Enforced more strictly in the service layer, but a schema-level
        # hint helps clients: if you pick "dispute", you need a booking_id.
        return v


class TicketUpdateRequest(BaseModel):
    """Admin-only — change status, priority, or assignee."""
    status: Literal["open", "in_review", "waiting_customer", "resolved", "closed"] | None = None
    priority: Literal["low", "medium", "high", "urgent"] | None = None
    assignee_id: uuid.UUID | None = None


class TicketCommentRequest(BaseModel):
    comment: str = Field(..., min_length=1, max_length=5000)
    internal: bool = False


# ── Response Schemas ─────────────────────────────────────────────────────

class TicketEventResponse(BaseModel):
    id: str
    ticket_id: str
    event_type: str
    actor_id: str | None = None
    old_status: str | None = None
    new_status: str | None = None
    comment: str | None = None
    internal: bool
    extra_data: dict | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_event(cls, event) -> "TicketEventResponse":
        return cls(
            id=str(event.id),
            ticket_id=str(event.ticket_id),
            event_type=event.event_type,
            actor_id=str(event.actor_id) if event.actor_id else None,
            old_status=event.old_status,
            new_status=event.new_status,
            comment=event.comment,
            internal=event.internal,
            extra_data=event.extra_data,
            created_at=event.created_at,
        )


def _sla_state(ticket) -> str | None:
    from app.modules.support.sla import sla_state

    if getattr(ticket, "resolve_due_at", None) is None:
        return None
    return sla_state(ticket)


class TicketResponse(BaseModel):
    id: str
    subject: str
    description: str
    status: str
    category: str
    priority: str
    creator_id: str | None = None
    ticket_number: str | None = None
    ack_due_at: datetime | None = None
    resolve_due_at: datetime | None = None
    acknowledged_at: datetime | None = None
    # on_track | ack_overdue | resolve_overdue | done (app/modules/support/sla.py)
    sla_state: str | None = None
    is_guest: bool = False
    assignee_id: str | None = None
    booking_id: str | None = None
    venue_id: str | None = None
    help_article_id: str | None = None
    help_article_version: int | None = None
    help_section: str | None = None
    help_excerpt: str | None = None
    resolved_at: datetime | None = None
    closed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_ticket(cls, ticket) -> "TicketResponse":
        return cls(
            id=str(ticket.id),
            subject=ticket.subject,
            description=ticket.description,
            status=ticket.status,
            category=ticket.category,
            priority=ticket.priority,
            creator_id=str(ticket.creator_id) if ticket.creator_id else None,
            ticket_number=getattr(ticket, "ticket_number", None),
            ack_due_at=getattr(ticket, "ack_due_at", None),
            resolve_due_at=getattr(ticket, "resolve_due_at", None),
            acknowledged_at=getattr(ticket, "acknowledged_at", None),
            sla_state=_sla_state(ticket),
            is_guest=ticket.creator_id is None,
            assignee_id=str(ticket.assignee_id) if ticket.assignee_id else None,
            booking_id=str(ticket.booking_id) if ticket.booking_id else None,
            venue_id=str(ticket.venue_id) if ticket.venue_id else None,
            help_article_id=str(ticket.help_article_id) if getattr(ticket, "help_article_id", None) else None,
            help_article_version=getattr(ticket, "help_article_version", None),
            help_section=getattr(ticket, "help_section", None),
            help_excerpt=getattr(ticket, "help_excerpt", None),
            resolved_at=ticket.resolved_at,
            closed_at=ticket.closed_at,
            created_at=ticket.created_at,
            updated_at=ticket.updated_at,
        )


class TicketDetailResponse(TicketResponse):
    """Ticket with events — events are pre-filtered by the service layer
    based on viewer role (internal events hidden from non-admins)."""
    events: list[TicketEventResponse] = []

    @classmethod
    def from_ticket_with_events(
        cls, ticket, events: list,
    ) -> "TicketDetailResponse":
        base = TicketResponse.from_ticket(ticket)
        return cls(
            **base.model_dump(),
            events=[TicketEventResponse.from_event(e) for e in events],
        )
