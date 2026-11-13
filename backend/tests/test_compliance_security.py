"""@compliance check 8 (items 8.1-8.4): reasonable security safeguards
(DPDP s.8(5), Rules r.6; CERT-In Directions 2022)."""
import logging
import uuid

import pytest
from sqlalchemy import text

from app.config import settings
from app.models.core import AuditLog, OwnerBankAccount, OwnerVerification
from app.modules.auth import totp
from tests.compliance_support import PASSWORD, REPO_ROOT, auth, client, fetch, make_booking, make_user, make_venue_with_unit  # noqa: F401
from tests.conftest import REAL_PNG

pytestmark = pytest.mark.compliance


async def test_8_1_api_sends_hsts_csp_and_frame_headers(client):
    resp = await client.get("/api/v1/health")
    h = resp.headers
    assert "max-age=" in h["strict-transport-security"]
    assert "frame-ancestors 'none'" in h["content-security-policy"] or h["x-frame-options"] == "DENY"
    assert h["x-content-type-options"] == "nosniff"


def test_8_1_web_server_config_sends_hsts_and_csp():
    conf = (REPO_ROOT / "frontend" / "nginx.conf").read_text() + (REPO_ROOT / "frontend" / "nginx-security-headers.conf").read_text()
    assert "include /etc/nginx/snippets/security-headers.conf" in conf
    dockerfile = (REPO_ROOT / "frontend" / "Dockerfile").read_text()
    assert "nginx-security-headers.conf /etc/nginx/snippets/security-headers.conf" in dockerfile
    assert "Strict-Transport-Security" in conf
    assert "Content-Security-Policy" in conf
    assert "frame-ancestors" in conf
    host = (REPO_ROOT / "deploy" / "nginx-host.conf").read_text()
    assert "return 301 https://" in host


async def test_8_1_refresh_cookie_is_httponly_and_secure_in_production(client, test_session_factory, monkeypatch):
    user = await make_user(test_session_factory)
    monkeypatch.setattr(settings, "environment", "production")
    monkeypatch.setattr(settings, "field_encryption_key", "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY=")
    resp = await client.post("/api/v1/auth/login", json={"login_id": user.email, "password": PASSWORD})
    cookie = resp.headers["set-cookie"].lower()
    assert "httponly" in cookie and "secure" in cookie and "samesite=lax" in cookie


async def _submit_verification(client, user, number="ABCDE1234F"):
    return await client.post(
        "/api/v1/owner/verification",
        files={"document": ("id.png", REAL_PNG, "image/png")},
        data={"business_name": "Nair Grounds", "identification_type": "pan", "identification_number": number, "pan": "ABCDE1234F", "gstin": "09ABCDE1234F1Z5"},
        headers=auth(user.id, "customer"),
    )


async def test_8_3_identity_numbers_encrypted_at_rest_and_masked_in_responses(client, test_session_factory):
    user = await make_user(test_session_factory)
    admin = await make_user(test_session_factory, "admin")
    resp = await _submit_verification(client, user)
    assert resp.status_code == 201, resp.text
    assert "ABCDE1234F" not in resp.text
    async with test_session_factory() as s:
        raw = (await s.execute(text("SELECT identification_number, pan, gstin FROM owner_verifications"))).one()
    assert all(v and v.startswith("enc:v1:") for v in raw)
    admin_list = await client.get("/api/v1/admin/owner-verifications", headers=auth(admin.id, "admin"))
    assert "ABCDE1234F" not in admin_list.text and "09ABCDE1234F1Z5" not in admin_list.text
    row = admin_list.json()[0]
    assert row["identification_number"].endswith("234F") and "•" in row["identification_number"]


async def test_8_3_bank_account_numbers_encrypted_and_masked(client, test_session_factory):
    owner = await make_user(test_session_factory, "owner", verified=True)
    resp = await client.post(
        "/api/v1/owner/bank-accounts",
        json={"account_holder_name": "Sunil Rao", "account_number": "123456789012", "ifsc_code": "SBIN0001234", "bank_name": "SBI"},
        headers=auth(owner.id, "owner"),
    )
    assert resp.status_code in (200, 201), resp.text
    assert "123456789012" not in resp.text
    async with test_session_factory() as s:
        raw = (await s.execute(text("SELECT account_number FROM owner_bank_accounts"))).scalar_one()
    assert raw.startswith("enc:v1:")
    listed = await client.get("/api/v1/owner/bank-accounts", headers=auth(owner.id, "owner"))
    assert "123456789012" not in listed.text and "9012" in listed.text


async def test_8_3_aadhaar_numbers_are_never_stored_in_full(client, test_session_factory):
    user = await make_user(test_session_factory)
    resp = await client.post(
        "/api/v1/owner/verification",
        files={"document": ("id.png", REAL_PNG, "image/png")},
        data={"identification_type": "aadhaar", "identification_number": "1234 5678 9012"},
        headers=auth(user.id, "customer"),
    )
    assert resp.status_code == 422
    assert "last 4" in resp.text


async def test_8_3_document_views_are_audit_logged(client, test_session_factory):
    user = await make_user(test_session_factory)
    admin = await make_user(test_session_factory, "admin")
    await _submit_verification(client, user)
    v = (await fetch(test_session_factory, OwnerVerification))[0]
    resp = await client.get(f"/api/v1/admin/owner-verifications/{v.id}/document", headers=auth(admin.id, "admin"))
    assert resp.status_code == 200
    logs = await fetch(test_session_factory, AuditLog, action="owner_verification.document_viewed")
    assert len(logs) == 1 and logs[0].actor_id == admin.id


async def test_8_2_customer_cannot_read_another_customers_booking_or_ticket(client, test_session_factory):
    owner = await make_user(test_session_factory, "owner", verified=True)
    venue_id, unit_id = await make_venue_with_unit(test_session_factory, owner.id)
    a = await make_user(test_session_factory)
    b = await make_user(test_session_factory)
    booking = await make_booking(test_session_factory, venue_id, unit_id, a.id, status="confirmed")
    assert (await client.get(f"/api/v1/bookings/{booking}", headers=auth(b.id, "customer"))).status_code in (403, 404)
    t = await client.post("/api/v1/support/tickets", json={"subject": "Help", "description": "Private text"}, headers=auth(a.id, "customer"))
    assert t.status_code in (200, 201), t.text
    assert (await client.get(f"/api/v1/support/tickets/{t.json()['id']}", headers=auth(b.id, "customer"))).status_code in (403, 404)


async def test_8_2_owner_cannot_read_verification_documents(client, test_session_factory):
    user = await make_user(test_session_factory)
    other_owner = await make_user(test_session_factory, "owner", verified=True)
    await _submit_verification(client, user)
    v = (await fetch(test_session_factory, OwnerVerification))[0]
    resp = await client.get(f"/api/v1/admin/owner-verifications/{v.id}/document", headers=auth(other_owner.id, "owner"))
    assert resp.status_code == 403


async def test_8_2_admin_sign_in_requires_second_factor_once_enrolled(client, test_session_factory, monkeypatch):
    clock = {"step": totp.current_step()}
    monkeypatch.setattr(totp, "current_step", lambda at=None: clock["step"])  # no 30 s boundary flakiness
    admin = await make_user(test_session_factory, "admin")
    setup = await client.post("/api/v1/auth/2fa/setup", headers=auth(admin.id, "admin"))
    assert setup.status_code == 200, setup.text
    secret = setup.json()["secret"]
    enable = await client.post("/api/v1/auth/2fa/enable", json={"code": totp.now(secret)}, headers=auth(admin.id, "admin"))
    assert enable.status_code == 200, enable.text
    assert len(enable.json()["recovery_codes"]) >= 8

    no_code = await client.post("/api/v1/auth/login", json={"login_id": admin.email, "password": PASSWORD})
    assert no_code.status_code == 401 and no_code.json()["detail"] == "two_factor_required"
    bad = await client.post("/api/v1/auth/login", json={"login_id": admin.email, "password": PASSWORD, "otp": "000000"})
    assert bad.status_code == 401
    # The code used to enable is spent (replay protection), so sign in with
    # the next 30-second code, which the ±1 step clock-skew window accepts.
    replay = await client.post("/api/v1/auth/login", json={"login_id": admin.email, "password": PASSWORD, "otp": totp.now(secret)})
    assert replay.status_code == 401
    clock["step"] += 1
    next_code = totp.now(secret)
    ok = await client.post("/api/v1/auth/login", json={"login_id": admin.email, "password": PASSWORD, "otp": next_code})
    assert ok.status_code == 200
    from app.modules.auth.security import decode_access_token
    assert "otp" in decode_access_token(ok.json()["access_token"])["amr"]
    recovery = enable.json()["recovery_codes"][0]
    ok2 = await client.post("/api/v1/auth/login", json={"login_id": admin.email, "password": PASSWORD, "otp": recovery})
    assert ok2.status_code == 200
    again = await client.post("/api/v1/auth/login", json={"login_id": admin.email, "password": PASSWORD, "otp": recovery})
    assert again.status_code == 401, "recovery codes are single use"


async def test_8_2_when_required_admin_without_2fa_is_blocked_from_admin_routes(client, test_session_factory, monkeypatch):
    monkeypatch.setattr(settings, "admin_2fa_required", True)
    admin = await make_user(test_session_factory, "admin")
    resp = await client.get("/api/v1/admin/users", headers=auth(admin.id, "admin", amr=["pwd"]))
    assert resp.status_code == 403 and resp.json()["detail"] == "two_factor_setup_required"
    # The enrolment route itself stays reachable.
    assert (await client.post("/api/v1/auth/2fa/setup", headers=auth(admin.id, "admin", amr=["pwd"]))).status_code == 200
    ok = await client.get("/api/v1/admin/users", headers=auth(admin.id, "admin", amr=["pwd", "otp"]))
    assert ok.status_code == 200


def test_8_2_two_factor_is_required_by_default_in_production():
    from app.config import Settings
    assert Settings.model_fields["admin_2fa_required"].default is None  # None = follow the environment
    assert settings.resolve_admin_2fa_required("production") is True
    assert settings.resolve_admin_2fa_required("dev") is False


def test_8_3_manage_tokens_are_redacted_from_logs():
    from app.modules.core.logging import RedactSecretsFilter
    record = logging.LogRecord("uvicorn.access", logging.INFO, __file__, 1, '%s - "%s %s HTTP/%s" %d',
                               ("1.2.3.4", "GET", "/api/v1/bookings/manage/AbCdEf123456789xyz/cancel", "1.1", 200), None)
    RedactSecretsFilter().filter(record)
    assert "AbCdEf123456789xyz" not in record.getMessage()
    assert "/api/v1/bookings/manage/[redacted]/cancel" in record.getMessage()
    conf = (REPO_ROOT / "frontend" / "nginx.conf").read_text()
    assert "log_format" in conf and "redacted" in conf


def test_8_3_log_retention_is_at_least_one_year():
    from app.modules.privacy.retention import RETENTION_DAYS
    assert RETENTION_DAYS["audit_logs"] >= 365
    compose = (REPO_ROOT / "docker-compose.yml").read_text()
    assert "max-size" in compose and "max-file" in compose


async def test_8_3_admin_database_viewer_never_shows_identity_numbers_in_clear(client, test_session_factory):
    user = await make_user(test_session_factory)
    admin = await make_user(test_session_factory, "admin")
    await _submit_verification(client, user)
    resp = await client.get("/api/v1/admin/db/tables/owner_verifications", headers=auth(admin.id, "admin"))
    assert "ABCDE1234F" not in resp.text


def test_8_4_vendor_register_lists_every_processor_with_contract_checklist():
    md = (REPO_ROOT / "docs" / "compliance" / "drafts" / "vendor-register.md").read_text()
    assert "## Contract checklist" in md
    for word in ["hosting", "storage", "Email / SMS", "Payment gateway"]:
        assert word.lower() in md.lower()


@pytest.mark.owner_facts
def test_8_4_owner_has_signed_processor_contracts():
    md = (REPO_ROOT / "docs" / "compliance" / "drafts" / "vendor-register.md").read_text()
    hosting_row = next(line for line in md.splitlines() if "VPS hosting" in line)
    assert "OWNER TO FILL" not in hosting_row, "processor contract status still a placeholder (D-09)"


def test_8_3_production_refuses_to_start_without_field_encryption_key():
    from app.config import Settings
    with pytest.raises(ValueError, match="FIELD_ENCRYPTION_KEY"):
        Settings(
            environment="production",
            jwt_secret_key="a" * 32,
            public_app_url="https://app.example.com",
            database_url="postgresql+asyncpg://user:pass@db.example.com:5432/proddb",
            cors_allowed_origins="https://app.example.com",
        )


async def test_8_2_production_refuses_admins_with_published_dev_passwords(test_session_factory):
    from sqlalchemy import update as sa_update
    from app.models.core import User
    from app.modules.auth.security import hash_password
    from app.modules.privacy import demo
    admin = await make_user(test_session_factory, "admin")
    async with test_session_factory() as s:
        async with s.begin():
            await s.execute(sa_update(User).where(User.id == admin.id).values(password_hash=hash_password("Admin@2026!")))
    with pytest.raises(RuntimeError, match="password published"):
        await demo.assert_no_known_dev_passwords_in_production(test_session_factory, "production")
    await demo.assert_no_known_dev_passwords_in_production(test_session_factory, "dev")


def test_8_2_seed_script_has_no_default_admin_password():
    src = (REPO_ROOT / "backend" / "scripts" / "seed_dataset.py").read_text()
    assert 'os.environ.get("ADMIN_PASSWORD", "' not in src
