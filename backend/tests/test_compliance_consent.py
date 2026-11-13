"""@compliance check 2: consent done properly (DPDP s.6, E-Commerce r.4(9))."""
import hashlib

import pytest
from sqlalchemy import select

from app.models.core import ConsentRecord, User
from app.modules.privacy.versions import NOTICE_VERSION, TERMS_VERSION
from tests.compliance_support import auth, client, fetch, make_user, signup_body  # noqa: F401

pytestmark = pytest.mark.compliance


async def test_2_4_signup_records_consent_with_versions_time_and_hashed_ip(client, test_session_factory):
    body = signup_body()
    resp = await client.post("/api/v1/auth/signup", json=body)
    assert resp.status_code == 201, resp.text
    user_id = resp.json()["id"]

    rows = await fetch(test_session_factory, ConsentRecord)
    rows = [r for r in rows if str(r.user_id) == user_id]
    purposes = {r.purpose for r in rows}
    assert {"terms", "privacy_notice", "age_18_plus"} <= purposes
    for r in rows:
        assert r.action == "given"
        assert r.notice_version == NOTICE_VERSION
        assert r.terms_version == TERMS_VERSION
        assert r.created_at is not None
        # IP is stored only as a keyed hash, never in clear text.
        assert r.ip_hash and "203.0.113.7" not in r.ip_hash
        assert r.ip_hash != hashlib.sha256(b"203.0.113.7").hexdigest()


async def test_2_2_no_marketing_purpose_is_bundled_with_service_consent(client, test_session_factory):
    resp = await client.post("/api/v1/auth/signup", json=signup_body(marketing_opt_in=True))
    assert resp.status_code == 201
    rows = await fetch(test_session_factory, ConsentRecord)
    assert not any("marketing" in r.purpose for r in rows)


async def test_2_4_user_can_list_own_consents(client, test_session_factory):
    resp = await client.post("/api/v1/auth/signup", json=signup_body())
    uid = resp.json()["id"]
    import uuid as _uuid
    resp = await client.get("/api/v1/me/consents", headers=auth(_uuid.UUID(uid), "customer"))
    assert resp.status_code == 200
    items = resp.json()
    assert {i["purpose"] for i in items} >= {"terms", "privacy_notice", "age_18_plus"}
    assert all("ip_hash" not in i for i in items)


async def test_2_3_withdrawing_consent_is_one_call_is_recorded_and_takes_effect(client, test_session_factory):
    user = await make_user(test_session_factory)
    resp = await client.post("/api/v1/me/consents/withdraw", headers=auth(user.id, "customer"), json={"confirm": True})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["request_number"].startswith("GK-D-")
    assert body["status"] == "completed"

    rows = await fetch(test_session_factory, ConsentRecord, user_id=user.id)
    assert any(r.action == "withdrawn" for r in rows)
    async with test_session_factory() as s:
        u = (await s.execute(select(User).where(User.id == user.id))).scalar_one()
        assert u.deleted_at is not None
        assert u.email != user.email and u.phone != user.phone
    # Takes effect: the account can no longer be used.
    me = await client.get("/api/v1/users/me", headers=auth(user.id, "customer"))
    assert me.status_code == 401


async def test_2_3_withdrawal_requires_explicit_confirmation(client, test_session_factory):
    user = await make_user(test_session_factory)
    resp = await client.post("/api/v1/me/consents/withdraw", headers=auth(user.id, "customer"), json={})
    assert resp.status_code == 422


async def test_2_4_existing_account_accepts_new_notice_and_confirms_age(client, test_session_factory):
    """DPDP s.5(2): accounts created before the notice existed are asked to
    accept it; the 18+ confirmation is required if they never gave one."""
    user = await make_user(test_session_factory)  # legacy account: no consent rows
    me = (await client.get("/api/v1/users/me", headers=auth(user.id, "customer"))).json()
    assert me["accepted_terms_version"] is None and me["age_confirmed"] is False

    refused = await client.post("/api/v1/me/consents/accept", headers=auth(user.id, "customer"), json={"accept": True})
    assert refused.status_code == 422

    ok = await client.post("/api/v1/me/consents/accept", headers=auth(user.id, "customer"), json={"accept": True, "age_confirmed": True})
    assert ok.status_code == 200, ok.text
    rows = await fetch(test_session_factory, ConsentRecord, user_id=user.id)
    assert {r.purpose for r in rows} == {"terms", "privacy_notice", "age_18_plus"}
    assert all(r.source == "notice_update" and r.terms_version == TERMS_VERSION for r in rows)

    me = (await client.get("/api/v1/users/me", headers=auth(user.id, "customer"))).json()
    assert me["accepted_terms_version"] == TERMS_VERSION and me["age_confirmed"] is True
