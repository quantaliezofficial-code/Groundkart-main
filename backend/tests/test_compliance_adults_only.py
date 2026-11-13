"""@compliance check 7: adults only (owner decision; DPDP s.9 handled by not
accepting minors). Parental consent is Not applicable by design."""
import pytest
from sqlalchemy import inspect as sa_inspect, select

from app.models.core import ConsentRecord, User
from app.modules.privacy.versions import TERMS_VERSION
from tests.compliance_support import auth, client, fetch, legal, make_user, make_venue_with_unit, signup_body  # noqa: F401

pytestmark = pytest.mark.compliance


async def test_7_1_signup_without_age_confirmation_is_refused_with_clear_message(client):
    resp = await client.post("/api/v1/auth/signup", json=signup_body(age_confirmed=False))
    assert resp.status_code == 422
    assert "18" in resp.text
    body = signup_body()
    body.pop("age_confirmed")
    assert (await client.post("/api/v1/auth/signup", json=body)).status_code == 422


async def test_7_1_signup_stores_age_confirmation_with_time_and_terms_version(client, test_session_factory):
    resp = await client.post("/api/v1/auth/signup", json=signup_body())
    uid = resp.json()["id"]
    rows = [r for r in await fetch(test_session_factory, ConsentRecord) if str(r.user_id) == uid and r.purpose == "age_18_plus"]
    assert len(rows) == 1 and rows[0].terms_version == TERMS_VERSION and rows[0].created_at


async def test_7_1_guest_checkout_without_age_confirmation_is_refused(client, test_session_factory):
    owner = await make_user(test_session_factory, "owner", verified=True)
    _, unit_id = await make_venue_with_unit(test_session_factory, owner.id)
    resp = await client.post(
        "/api/v1/bookings", json={"inventory_unit_id": str(unit_id), "guest_name": "Ravi", "guest_email": "ravi@example.com"}
    )
    assert resp.status_code == 422
    assert "18" in resp.text


def test_7_1_no_date_of_birth_is_collected():
    cols = {c.key for c in sa_inspect(User).columns}
    assert not {"date_of_birth", "dob", "birth_date", "age"} & cols


def test_7_4_notice_and_terms_tell_users_not_to_enter_childrens_details():
    assert "do not enter the personal details of children" in legal("privacy.en.md")
    assert "do not enter children's personal details" in legal("terms.en.md")


async def test_7_4_admin_can_suspend_and_erase_a_minors_account(client, test_session_factory):
    admin = await make_user(test_session_factory, "admin")
    minor = await make_user(test_session_factory, "customer", name="Young Person")
    resp = await client.post(
        f"/api/v1/admin/users/{minor.id}/minor-account",
        json={"note": "Parent wrote in; user is 15."},
        headers=auth(admin.id, "admin"),
    )
    assert resp.status_code == 200, resp.text
    async with test_session_factory() as s:
        u = (await s.execute(select(User).where(User.id == minor.id))).scalar_one()
        assert u.suspended_at is not None and u.deleted_at is not None
        assert u.name != "Young Person" and u.email != minor.email


async def test_7_4_customer_cannot_use_minor_account_action(client, test_session_factory):
    c = await make_user(test_session_factory, "customer")
    target = await make_user(test_session_factory, "customer")
    resp = await client.post(f"/api/v1/admin/users/{target.id}/minor-account", json={}, headers=auth(c.id, "customer"))
    assert resp.status_code == 403


def test_7_3_no_tracking_or_advertising_code_in_frontend():
    import pathlib
    import re
    root = pathlib.Path(__file__).resolve().parents[2] / "frontend"
    pattern = re.compile(r"gtag\(|googletagmanager|fbq\(|connect\.facebook|hotjar|clarity\.ms|mixpanel|segment\.io|amplitude\.com|@amplitude|doubleclick\.net", re.I)
    files = [root / "index.html", *(root / "src").rglob("*.ts*")]
    hits = [str(f) for f in files if f.is_file() and ".test." not in f.name and pattern.search(f.read_text(encoding="utf-8", errors="ignore"))]
    assert hits == []


def test_7_2_parental_consent_not_applicable_by_design():
    """Owner decision D-12: minors are not accepted, so no parental-consent
    flow exists. This test keeps it that way and checks the rule is stated."""
    from app.main import app as fastapi_app
    paths = " ".join(getattr(r, "path", "") for r in fastapi_app.routes).lower()
    assert "parent" not in paths and "guardian" not in paths
    cols = {c.key for c in sa_inspect(User).columns}
    assert not any("parent" in c or "guardian" in c for c in cols)
    assert "GroundKart is for adults aged 18 and over" in legal("privacy.en.md")
