"""Retention jobs (DPDP Act s.8(7); Rules r.6(1)(e), r.8).

``RETENTION_DAYS`` is the code copy of
docs/compliance/drafts/retention-schedule.md; @compliance tests fail if the
two disagree. ``run_retention`` is called once a day by the API process
(app/main.py lifespan) and can be run by hand:

    python -m scripts.run_retention --dry-run
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, delete, func, or_, select, update

from app.models.core import (
    AuditLog,
    Booking,
    ConsentRecord,
    DataRequest,
    GuestEnquiry,
    HelpSearchLog,
    IdempotencyKey,
    InventoryUnit,
    Job,
    LoginRateLimit,
    Notification,
    OutboxEvent,
    OwnerVerification,
    PasswordResetRequest,
    RefreshToken,
    SupportTicket,
    TicketEvent,
    User,
)

log = logging.getLogger("groundkart.retention")

# None = not time-based (kept until an event such as account closure).
RETENTION_DAYS: dict[str, int | None] = {
    "login_rate_limits": 1,
    "idempotency_keys": 0,
    "refresh_tokens": 30,
    "password_reset_requests": 90,
    "help_search_log": 90,
    "jobs_outbox": 30,
    "notifications": 365,
    "guest_enquiries": 365,
    "guest_booking_contact": 365,
    "closed_tickets": 730,
    "verification_documents": 365,
    "consent_records": 365,
    "audit_logs": 365,
    "data_requests": 3 * 365,
    "financial_records": 8 * 365,
    "inactive_account": 3 * 365,
    "verification_numbers": None,
}

# Row label in retention-schedule.md for each key.
SCHEDULE_LABELS: dict[str, str] = {
    "login_rate_limits": "Rate-limit counters",
    "idempotency_keys": "Idempotency keys and cached responses",
    "refresh_tokens": "Refresh tokens (expired or revoked)",
    "password_reset_requests": "Password reset requests",
    "help_search_log": "Help search queries",
    "jobs_outbox": "Completed jobs and delivered outbox events",
    "notifications": "In-app notifications",
    "guest_enquiries": "Guest enquiries (legacy, before tickets)",
    "guest_booking_contact": "Guest booking contact and booking notes",
    "closed_tickets": "Resolved and closed support tickets",
    "verification_documents": "Verification documents",
    "consent_records": "Consent records",
    "audit_logs": "Security and audit logs",
    "data_requests": "Data requests (rights)",
    "financial_records": "Booking, payment, refund, payout, ledger and commission records",
    "inactive_account": "Inactive accounts (no sign-in, no booking)",
    "verification_numbers": "Verification numbers (ID number, PAN, GSTIN) and bank details",
}

INACTIVITY_WARNING = timedelta(hours=48)
ERASED_TEXT = "[removed under the retention schedule]"


def _cut(now: datetime, key: str) -> datetime:
    return now - timedelta(days=RETENTION_DAYS[key])


async def run_retention(session_factory, *, now: datetime | None = None, dry_run: bool = False) -> dict[str, int]:
    """Applies every rule once. Each rule runs in its own transaction so one
    failure does not block the others. Returns rows affected per rule."""
    now = now or datetime.now(timezone.utc)
    counts: dict[str, int] = {}

    async def _apply(name, *stmts):
        async with session_factory() as session:
            trans = await session.begin()
            total = 0
            for stmt in stmts:
                result = await session.execute(stmt)
                total += result.rowcount or 0
            await (trans.rollback() if dry_run else trans.commit())
        counts[name] = total

    await _apply("login_rate_limits", delete(LoginRateLimit).where(LoginRateLimit.window_start < _cut(now, "login_rate_limits")))
    await _apply("idempotency_keys", delete(IdempotencyKey).where(IdempotencyKey.expires_at < _cut(now, "idempotency_keys")))
    await _apply(
        "refresh_tokens",
        delete(RefreshToken).where(
            or_(RefreshToken.expires_at < _cut(now, "refresh_tokens"), RefreshToken.revoked_at < _cut(now, "refresh_tokens"))
        ),
    )
    await _apply("password_reset_requests", delete(PasswordResetRequest).where(PasswordResetRequest.created_at < _cut(now, "password_reset_requests")))
    await _apply("help_search_log", delete(HelpSearchLog).where(HelpSearchLog.created_at < _cut(now, "help_search_log")))
    await _apply(
        "jobs_outbox",
        delete(Job).where(Job.status.in_(["completed", "failed"]), Job.created_at < _cut(now, "jobs_outbox")),
        delete(OutboxEvent).where(OutboxEvent.status == "processed", OutboxEvent.created_at < _cut(now, "jobs_outbox")),
    )
    await _apply("notifications", delete(Notification).where(Notification.created_at < _cut(now, "notifications")))
    await _apply(
        "guest_enquiries",
        update(SupportTicket)
        .where(SupportTicket.guest_enquiry_id.in_(select(GuestEnquiry.id).where(GuestEnquiry.created_at < _cut(now, "guest_enquiries"))))
        .where(SupportTicket.status.in_(["resolved", "closed"]))
        .values(guest_enquiry_id=None),
        delete(GuestEnquiry).where(
            GuestEnquiry.created_at < _cut(now, "guest_enquiries"),
            ~GuestEnquiry.id.in_(select(SupportTicket.guest_enquiry_id).where(SupportTicket.guest_enquiry_id.is_not(None))),
        ),
    )
    counts["guest_booking_contact"] = await _anonymise_old_bookings(session_factory, now, dry_run)
    old_tickets = select(SupportTicket.id).where(
        SupportTicket.status.in_(["resolved", "closed"]),
        func.coalesce(SupportTicket.closed_at, SupportTicket.resolved_at, SupportTicket.updated_at) < _cut(now, "closed_tickets"),
        SupportTicket.description != ERASED_TEXT,
    )
    await _apply(
        "closed_tickets",
        update(TicketEvent).where(TicketEvent.ticket_id.in_(old_tickets), TicketEvent.comment.is_not(None)).values(comment=ERASED_TEXT),
        update(SupportTicket).where(SupportTicket.id.in_(old_tickets)).values(subject=ERASED_TEXT, description=ERASED_TEXT, help_excerpt=None),
    )
    await _apply("audit_logs", delete(AuditLog).where(AuditLog.created_at < _cut(now, "audit_logs")))
    await _apply("data_requests", delete(DataRequest).where(DataRequest.status != "open", DataRequest.updated_at < _cut(now, "data_requests")))
    closed_users = select(User.id).where(User.deleted_at.is_not(None), User.deleted_at < _cut(now, "consent_records"))
    await _apply("consent_records", delete(ConsentRecord).where(ConsentRecord.user_id.in_(closed_users)))

    counts["verification_documents"] = await _purge_verification_documents(session_factory, now, dry_run)
    counts.update(await _inactive_accounts(session_factory, now, dry_run))
    log.info("retention run %s: %s", "dry-run" if dry_run else "applied", counts)
    return counts


async def _anonymise_old_bookings(session_factory, now: datetime, dry_run: bool) -> int:
    """Guest contact details and booking notes, 1 year after the event.
    Amounts, dates and status stay for the financial-records period."""
    event_cutoff = (now - timedelta(days=RETENTION_DAYS["guest_booking_contact"])).date()
    async with session_factory() as session:
        trans = await session.begin()
        rows = (
            await session.execute(
                select(Booking)
                .join(InventoryUnit, InventoryUnit.id == Booking.inventory_unit_id)
                .where(
                    InventoryUnit.date < event_cutoff,
                    or_(
                        and_(Booking.customer_id.is_(None), Booking.guest_name != "Former guest"),
                        Booking.customer_notes.is_not(None),
                    ),
                )
            )
        ).scalars().all()
        for b in rows:
            b.customer_notes = None
            if b.customer_id is None:
                b.guest_name = "Former guest"
                b.guest_email = f"erased-{b.id.hex[:12]}@erased.invalid"
                b.guest_phone = None
                b.manage_token_hash = None
        await (trans.rollback() if dry_run else trans.commit())
        return len(rows)


async def _purge_verification_documents(session_factory, now: datetime, dry_run: bool) -> int:
    from app.modules.privacy.erasure import _delete_private_file

    async with session_factory() as session:
        async with session.begin():
            rows = (
                await session.execute(
                    select(OwnerVerification).where(
                        OwnerVerification.storage_key.is_not(None),
                        OwnerVerification.status != "pending",
                        OwnerVerification.reviewed_at < _cut(now, "verification_documents"),
                    )
                )
            ).scalars().all()
            if dry_run:
                return len(rows)
            for v in rows:
                await _delete_private_file(v.storage_key)
                v.storage_key = None
                v.document_url = ""
            return len(rows)


async def _inactive_accounts(session_factory, now: datetime, dry_run: bool) -> dict[str, int]:
    """Voluntary 3-year inactivity rule (D-08) with a 48-hour warning
    (modelled on DPDP Rules r.8(2)). Admins and partners are excluded."""
    from app.modules.privacy.erasure import erase_user

    days = RETENTION_DAYS["inactive_account"]
    if days is None:
        return {"inactive_warned": 0, "inactive_erased": 0}
    cutoff = now - timedelta(days=days)
    warned = erased = 0
    async with session_factory() as session:
        async with session.begin():
            base = select(User).where(
                User.deleted_at.is_(None),
                User.role.in_(["customer", "owner"]),
                User.is_super_admin.is_(False),
                func.coalesce(User.last_active_at, User.created_at) < cutoff,
            )
            to_warn = (await session.execute(base.where(User.inactivity_warned_at.is_(None)))).scalars().all()
            to_erase = (
                await session.execute(
                    base.where(
                        User.inactivity_warned_at.is_not(None),
                        User.inactivity_warned_at <= now - INACTIVITY_WARNING,
                        func.coalesce(User.last_active_at, User.created_at) < User.inactivity_warned_at,
                    )
                )
            ).scalars().all()
            if dry_run:
                return {"inactive_warned": len(to_warn), "inactive_erased": len(to_erase)}
            for user in to_warn:
                user.inactivity_warned_at = now
                session.add(
                    Notification(
                        user_id=user.id,
                        type="inactive_account_warning",
                        message=(
                            "Your GroundKart account has not been used for 3 years. Sign in within 48 hours to keep it; "
                            "otherwise we will erase your personal data as our Privacy Notice describes."
                        ),
                        entity_type="user",
                        entity_id=user.id,
                    )
                )
                warned += 1
            for user in to_erase:
                await erase_user(session, user.id, reason="inactive_3_years")
                erased += 1
    return {"inactive_warned": warned, "inactive_erased": erased}
