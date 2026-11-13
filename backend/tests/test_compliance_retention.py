"""@compliance beyond-8 B.2/B.3/B.4: retention jobs and records
(DPDP s.8(7), Rules r.6(e), r.8, Third Schedule; CERT-In 180 days)."""
import re
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select, text

from app.models.core import AuditLog, Booking, IdempotencyKey, LoginRateLimit, Notification, SupportTicket, User
from app.modules.privacy import retention
from tests.compliance_support import REPO_ROOT, auth, client, fetch, make_booking, make_user, make_venue_with_unit  # noqa: F401

pytestmark = pytest.mark.compliance

NOW = datetime.now(timezone.utc)


def test_B3_retention_table_in_code_matches_published_schedule():
    md = (REPO_ROOT / "docs" / "compliance" / "drafts" / "retention-schedule.md").read_text()
    for key, days in retention.RETENTION_DAYS.items():
        label = retention.SCHEDULE_LABELS[key]
        row = next((line for line in md.splitlines() if line.startswith(f"| {label} |")), None)
        assert row, f"schedule has no row for {label}"
        cells = [c.strip() for c in row.strip("|").split("|")]
        if days is None:
            continue
        assert re.match(rf"^{days} days|^{days // 365} years?", cells[2]) or str(days) in cells[2], (label, cells[2], days)


async def test_B2_retention_job_purges_expired_infrastructure_rows(test_session_factory):
    async with test_session_factory() as s:
        async with s.begin():
            s.add(LoginRateLimit(key="ratelimit:old", window_start=NOW - timedelta(days=3), attempt_count=1))
            s.add(LoginRateLimit(key="ratelimit:new", window_start=NOW, attempt_count=1))
            s.add(IdempotencyKey(key="k1", operation="op", expires_at=NOW - timedelta(hours=1)))
            s.add(IdempotencyKey(key="k2", operation="op", expires_at=NOW + timedelta(hours=1)))
    counts = await retention.run_retention(test_session_factory, now=NOW)
    assert counts["login_rate_limits"] == 1 and counts["idempotency_keys"] == 1
    keys = {r.key for r in await fetch(test_session_factory, LoginRateLimit)}
    assert keys == {"ratelimit:new"}


async def test_B2_old_guest_booking_contacts_are_anonymised_but_amounts_kept(test_session_factory):
    owner = await make_user(test_session_factory, "owner", verified=True)
    venue_id, unit_id = await make_venue_with_unit(test_session_factory, owner.id, days_ahead=-400)
    bid = await make_booking(test_session_factory, venue_id, unit_id, None, status="completed",
                             guest_name="Old Guest", guest_email="old@example.com", guest_phone="9800000000", customer_notes="note")
    await retention.run_retention(test_session_factory, now=NOW)
    b = (await fetch(test_session_factory, Booking, id=bid))[0]
    assert b.guest_name == "Former guest" and b.guest_phone is None and b.customer_notes is None
    assert b.guest_email.endswith("@erased.invalid") and b.amount == 1500


async def test_B3_audit_logs_younger_than_a_year_are_kept(test_session_factory):
    async with test_session_factory() as s:
        async with s.begin():
            s.add(AuditLog(action="a.recent", entity_type="x", created_at=NOW - timedelta(days=300)))
            s.add(AuditLog(action="a.old", entity_type="x", created_at=NOW - timedelta(days=400)))
    await retention.run_retention(test_session_factory, now=NOW)
    actions = {r.action for r in await fetch(test_session_factory, AuditLog)}
    assert "a.recent" in actions and "a.old" not in actions


async def test_B2_closed_tickets_past_two_years_are_anonymised(test_session_factory):
    user = await make_user(test_session_factory)
    async with test_session_factory() as s:
        async with s.begin():
            s.add(SupportTicket(subject="Old", description="my secret detail", creator_id=user.id, status="closed",
                                closed_at=NOW - timedelta(days=800), created_at=NOW - timedelta(days=801)))
    await retention.run_retention(test_session_factory, now=NOW)
    t = (await fetch(test_session_factory, SupportTicket))[0]
    assert "secret" not in t.description


async def test_B4_inactive_accounts_get_a_48_hour_warning_before_erasure(test_session_factory):
    user = await make_user(test_session_factory)
    async with test_session_factory() as s:
        async with s.begin():
            await s.execute(text("UPDATE users SET last_active_at = :t WHERE id = :id"), {"t": NOW - timedelta(days=3 * 365 + 1), "id": user.id})
    await retention.run_retention(test_session_factory, now=NOW)
    notes = await fetch(test_session_factory, Notification, user_id=user.id)
    assert any(n.type == "inactive_account_warning" for n in notes)
    u = (await fetch(test_session_factory, User, id=user.id))[0]
    assert u.deleted_at is None, "not erased before the 48 hours pass"
    await retention.run_retention(test_session_factory, now=NOW + timedelta(hours=49))
    u = (await fetch(test_session_factory, User, id=user.id))[0]
    assert u.deleted_at is not None


async def test_B3_rate_limit_keys_do_not_store_phone_numbers_in_clear(client, test_session_factory):
    await client.post("/api/v1/auth/login", json={"login_id": "9876501234", "password": "wrong-password"})
    keys = [r.key for r in await fetch(test_session_factory, LoginRateLimit)]
    assert keys and not any("9876501234" in k or "203.0.113.7" in k for k in keys)
