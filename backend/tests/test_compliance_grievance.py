"""@compliance check 3: Grievance Officer and complaint handling
(DPDP s.8(9)-(10), Rules r.9, r.14; E-Commerce r.4(4)-(5); IT Rules 2011 r.5(9);
Intermediary Rules 2021 r.3(2))."""
import re
from datetime import timedelta

import pytest

from app.models.core import SupportTicket
from tests.compliance_support import auth, client, fetch, make_user  # noqa: F401

pytestmark = pytest.mark.compliance

GUEST = {
    "name": "Meera Iyer",
    "email": "meera@example.com",
    "phone": "9811100011",
    "subject": "Refund not received",
    "message": "I cancelled 3 days before and have not received my refund.",
}


async def test_3_2_guest_contact_form_creates_a_ticket_with_a_number(client, test_session_factory):
    resp = await client.post("/api/v1/contact", json=GUEST)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert re.fullmatch(r"GK-T-\d{4}-\d{4,}", data["ticket_number"])
    assert data["ticket_id"]
    tickets = await fetch(test_session_factory, SupportTicket, ticket_number=data["ticket_number"])
    assert len(tickets) == 1 and tickets[0].creator_id is None and tickets[0].guest_enquiry_id is not None


async def test_3_3_shopping_complaints_due_in_48h_and_one_month(client, test_session_factory):
    resp = await client.post("/api/v1/contact", json={**GUEST, "category": "grievance"})
    t = (await fetch(test_session_factory, SupportTicket, ticket_number=resp.json()["ticket_number"]))[0]
    assert t.category == "grievance"
    assert t.ack_due_at - t.created_at == timedelta(hours=48)
    assert t.resolve_due_at - t.created_at == timedelta(days=30)


async def test_3_3_content_complaints_due_in_24h_and_15_days(client, test_session_factory):
    resp = await client.post("/api/v1/contact", json={**GUEST, "category": "content_report"})
    t = (await fetch(test_session_factory, SupportTicket, ticket_number=resp.json()["ticket_number"]))[0]
    assert t.ack_due_at - t.created_at == timedelta(hours=24)
    assert t.resolve_due_at - t.created_at == timedelta(days=15)


async def test_3_3_data_requests_never_exceed_90_days(client, test_session_factory):
    resp = await client.post("/api/v1/contact", json={**GUEST, "category": "data_request"})
    t = (await fetch(test_session_factory, SupportTicket, ticket_number=resp.json()["ticket_number"]))[0]
    assert t.resolve_due_at - t.created_at <= timedelta(days=90)


async def test_3_3_admin_sees_due_dates_and_overdue_flag(client, test_session_factory):
    admin = await make_user(test_session_factory, "admin")
    await client.post("/api/v1/contact", json={**GUEST, "category": "grievance"})
    resp = await client.get("/api/v1/admin/support/tickets", headers=auth(admin.id, "admin"))
    assert resp.status_code == 200
    rows = resp.json()
    rows = rows["items"] if isinstance(rows, dict) else rows
    row = next(r for r in rows if r.get("category") == "grievance")
    assert row["ticket_number"] and row["ack_due_at"] and row["resolve_due_at"]
    assert row["sla_state"] in {"on_track", "ack_overdue", "resolve_overdue", "done"}


async def test_3_1_super_admin_sets_grievance_officer_and_it_is_published(client, test_session_factory):
    sa = await make_user(test_session_factory, "admin", super_admin=True)
    payload = {
        "grievance_officer_name": "Test Officer",
        "grievance_officer_designation": "Grievance Officer",
        "grievance_email": "grievance@example.com",
        "grievance_phone": "+91 90000 00000",
    }
    resp = await client.put("/api/v1/admin/legal/profile", json=payload, headers=auth(sa.id, "admin"))
    assert resp.status_code == 200, resp.text
    pub = (await client.get("/api/v1/legal/profile")).json()
    for k, v in payload.items():
        assert pub[k] == v


async def test_3_1_only_super_admin_can_change_legal_profile(client, test_session_factory):
    admin = await make_user(test_session_factory, "admin")
    resp = await client.put("/api/v1/admin/legal/profile", json={"legal_name": "X"}, headers=auth(admin.id, "admin"))
    assert resp.status_code == 403
