"""@compliance check 8 (items 8.5-8.6): breach register and clocks
(DPDP s.8(6), Rules r.7; CERT-In Directions 2022 direction (ii))."""
from datetime import datetime, timedelta, timezone

import pytest

from tests.compliance_support import REPO_ROOT, auth, client, make_user  # noqa: F401

pytestmark = pytest.mark.compliance

PLAN = (REPO_ROOT / "docs" / "compliance" / "drafts" / "breach-response-plan.md").read_text()


def test_8_5_written_breach_plan_covers_users_board_and_72_hours():
    assert "DRAFT FOR LAWYER REVIEW" in PLAN
    assert "Without delay" in PLAN and "72 hours" in PLAN and "User notice template" in PLAN


def test_8_6_written_plan_covers_cert_in_six_hours():
    assert "6 hours" in PLAN and "CERT-In" in PLAN


async def test_8_5_admin_logs_incident_and_deadlines_are_computed(client, test_session_factory):
    admin = await make_user(test_session_factory, "admin")
    detected = datetime(2026, 11, 10, 9, 0, tzinfo=timezone.utc)
    resp = await client.post(
        "/api/v1/admin/compliance/incidents",
        json={"title": "Suspicious admin login", "description": "Login from unknown IP", "detected_at": detected.isoformat(),
              "data_categories": ["contact details"], "affected_count": 12, "is_cyber_incident": True},
        headers=auth(admin.id, "admin"),
    )
    assert resp.status_code == 201, resp.text
    inc = resp.json()
    assert inc["reference"].startswith("GK-INC-")
    assert datetime.fromisoformat(inc["cert_in_due_at"]) == detected + timedelta(hours=6)
    assert datetime.fromisoformat(inc["board_report_due_at"]) == detected + timedelta(hours=72)
    assert inc["users_notice_due"] == "without_delay"


async def test_8_5_incident_register_tracks_notices_and_overdue(client, test_session_factory):
    admin = await make_user(test_session_factory, "admin")
    old = datetime.now(timezone.utc) - timedelta(hours=10)
    created = (await client.post("/api/v1/admin/compliance/incidents",
                                 json={"title": "Old", "description": "x", "detected_at": old.isoformat(), "is_cyber_incident": True},
                                 headers=auth(admin.id, "admin"))).json()
    listed = (await client.get("/api/v1/admin/compliance/incidents", headers=auth(admin.id, "admin"))).json()
    row = next(r for r in listed if r["id"] == created["id"])
    assert "cert_in" in row["overdue"]
    upd = await client.patch(f"/api/v1/admin/compliance/incidents/{created['id']}",
                             json={"cert_in_reported_at": datetime.now(timezone.utc).isoformat()},
                             headers=auth(admin.id, "admin"))
    assert upd.status_code == 200
    assert "cert_in" not in upd.json()["overdue"]


async def test_8_5_only_admins_can_see_incidents(client, test_session_factory):
    c = await make_user(test_session_factory)
    assert (await client.get("/api/v1/admin/compliance/incidents", headers=auth(c.id, "customer"))).status_code == 403
