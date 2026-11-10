"""
Super admin, team, referral partners (brokers), commission wallet, banners,
records/exports and share pages — exercised through real HTTP against the
real schema.

The permission cases are the important ones here: each privileged action is
tested from the role that may do it AND from the nearest role that may not.
"""
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import httpx
import pytest
from sqlalchemy import select, text

from app.db import get_db, get_idem_db
from app.main import app
from app.models.core import AuditLog, BrokerCommission, User, Venue, VenueMedia
from app.modules.auth.security import create_access_token, hash_password
from tests.conftest import REAL_JPEG, real_image_bytes


@pytest.fixture
async def client(test_session_factory):
    async def _override_get_db():
        async with test_session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_idem_db] = _override_get_db

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


def _auth(user_id: uuid.UUID, role: str) -> dict:
    return {"Authorization": f"Bearer {create_access_token(user_id, role)}"}


def _phone() -> str:
    return "98" + f"{uuid.uuid4().int % 10**8:08d}"


@pytest.fixture
async def super_admin(test_session_factory) -> uuid.UUID:
    async with test_session_factory() as session:
        async with session.begin():
            user = User(
                name="Platform Owner",
                email=f"owner-{uuid.uuid4().hex[:8]}@example.com",
                phone=_phone(),
                password_hash=hash_password("not-used-in-tests"),
                role="admin",
                is_super_admin=True,
            )
            session.add(user)
            await session.flush()
            return user.id


async def _make_broker(client, actor_id, **overrides) -> dict:
    body = {"name": "Ravi Kumar", "phone": _phone(), "email": f"ravi-{uuid.uuid4().hex[:6]}@example.com"}
    body.update(overrides)
    resp = await client.post("/api/v1/admin/brokers", json=body, headers=_auth(actor_id, "admin"))
    assert resp.status_code == 201, resp.text
    return resp.json()


# ---------------------------------------------------------------------------
# Team
# ---------------------------------------------------------------------------


async def test_super_admin_adds_admin_who_sets_own_password_and_logs_in(client, super_admin):
    phone = _phone()
    resp = await client.post(
        "/api/v1/admin/team",
        json={"name": "Neha Operations", "phone": phone, "email": "neha.ops@example.com"},
        headers=_auth(super_admin, "admin"),
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert "/reset-password?token=" in body["setup_url"]
    token = body["setup_url"].split("token=")[1]

    # The account can't be used until its holder chooses a password.
    resp = await client.post("/api/v1/auth/reset-password", json={"token": token, "new_password": "a-strong-passphrase-1"})
    assert resp.status_code == 200, resp.text

    login = await client.post("/api/v1/auth/login", json={"login_id": phone, "password": "a-strong-passphrase-1"})
    assert login.status_code == 200
    me = await client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {login.json()['access_token']}"})
    assert me.json()["role"] == "admin"
    assert me.json()["is_super_admin"] is False

    team = await client.get("/api/v1/admin/team", headers=_auth(super_admin, "admin"))
    assert team.status_code == 200
    names = {m["name"]: m for m in team.json()}
    assert names["Platform Owner"]["is_super_admin"] is True
    assert names["Neha Operations"]["is_super_admin"] is False


async def test_regular_admin_cannot_add_admins_or_see_team(client, super_admin, seeded_admin):
    headers = _auth(seeded_admin, "admin")
    resp = await client.post(
        "/api/v1/admin/team", json={"name": "Sneaky Admin", "phone": _phone()}, headers=headers
    )
    assert resp.status_code == 403
    assert (await client.get("/api/v1/admin/team", headers=headers)).status_code == 403


async def test_only_one_super_admin_can_exist(test_session_factory, super_admin):
    from sqlalchemy.exc import IntegrityError

    with pytest.raises(IntegrityError):
        async with test_session_factory() as session:
            async with session.begin():
                session.add(
                    User(
                        name="Second Owner",
                        phone=_phone(),
                        password_hash="x",
                        role="admin",
                        is_super_admin=True,
                    )
                )


async def test_admin_cannot_suspend_or_reset_other_admins_but_super_admin_can(
    client, test_session_factory, super_admin, seeded_admin
):
    async with test_session_factory() as session:
        async with session.begin():
            other = User(name="Other Admin", phone=_phone(), password_hash="x", role="admin")
            session.add(other)
            await session.flush()
            other_id = other.id

    admin_headers = _auth(seeded_admin, "admin")
    # A regular admin acting on another admin, and on the super admin.
    for target in (other_id, super_admin):
        resp = await client.post(
            f"/api/v1/admin/users/{target}/suspend", json={"reason": "testing"}, headers=admin_headers
        )
        assert resp.status_code == 403, resp.text
        resp = await client.post(
            f"/api/v1/admin/users/{target}/reset-password",
            json={"method": "temporary", "reason": "takeover attempt"},
            headers=admin_headers,
        )
        assert resp.status_code == 403, resp.text

    # The super admin can manage an admin...
    resp = await client.post(
        f"/api/v1/admin/users/{other_id}/suspend", json={"reason": "left the team"}, headers=_auth(super_admin, "admin")
    )
    assert resp.status_code == 200
    # ...and a suspended admin's still-valid token is refused on the live-checked routes.
    resp = await client.get("/api/v1/admin/brokers", headers=_auth(other_id, "admin"))
    assert resp.status_code == 401


async def test_super_admin_cannot_delete_own_account(client, super_admin):
    resp = await client.delete("/api/v1/users/me", headers=_auth(super_admin, "admin"))
    assert resp.status_code == 409


# ---------------------------------------------------------------------------
# Brokers: who can set what
# ---------------------------------------------------------------------------


async def test_admin_adds_broker_at_default_rate_and_cannot_set_terms(client, super_admin, seeded_admin):
    created = await _make_broker(client, seeded_admin)
    broker = created["broker"]
    assert broker["referral_code"].startswith("GK-RAV-")
    assert Decimal(broker["commission_percent"]) == Decimal("2.00")
    assert broker["commission_basis"] == "booking_amount"
    assert "/reset-password?token=" in created["setup_url"]

    # An admin sending a rate is refused, not silently defaulted.
    resp = await client.post(
        "/api/v1/admin/brokers",
        json={"name": "Asha Verma", "phone": _phone(), "commission_percent": "9.5"},
        headers=_auth(seeded_admin, "admin"),
    )
    assert resp.status_code == 403

    resp = await client.patch(
        f"/api/v1/admin/brokers/{broker['id']}", json={"commission_percent": "8"}, headers=_auth(seeded_admin, "admin")
    )
    assert resp.status_code == 403

    # Contact details are fine for an admin.
    resp = await client.patch(
        f"/api/v1/admin/brokers/{broker['id']}", json={"city": "Lucknow"}, headers=_auth(seeded_admin, "admin")
    )
    assert resp.status_code == 200 and resp.json()["city"] == "Lucknow"

    # The super admin sets the terms.
    resp = await client.patch(
        f"/api/v1/admin/brokers/{broker['id']}",
        json={"commission_percent": "3.50", "commission_basis": "platform_commission"},
        headers=_auth(super_admin, "admin"),
    )
    assert resp.status_code == 200
    assert Decimal(resp.json()["commission_percent"]) == Decimal("3.50")
    assert resp.json()["commission_basis"] == "platform_commission"


async def test_broker_cannot_reach_admin_routes_or_change_own_terms(client, super_admin):
    created = await _make_broker(client, super_admin, commission_percent="4")
    broker_id = uuid.UUID(created["broker"]["id"])
    headers = _auth(broker_id, "broker")

    assert (await client.get("/api/v1/admin/brokers", headers=headers)).status_code == 403
    assert (await client.get("/api/v1/admin/records/venues", headers=headers)).status_code == 403
    assert (await client.get("/api/v1/admin/users", headers=headers)).status_code == 403

    # commission_percent isn't a field a broker can send; it is ignored and unchanged.
    resp = await client.patch(
        "/api/v1/broker/me", json={"commission_percent": "50", "city": "Kanpur"}, headers=headers
    )
    assert resp.status_code == 200
    assert Decimal(resp.json()["commission_percent"]) == Decimal("4.00")
    assert resp.json()["city"] == "Kanpur"
    assert "notes" not in resp.json()


async def test_customer_and_owner_cannot_open_broker_dashboard(client, seeded_customer, seeded_verified_owner):
    assert (await client.get("/api/v1/broker/me", headers=_auth(seeded_customer, "customer"))).status_code == 403
    assert (await client.get("/api/v1/broker/venues", headers=_auth(seeded_verified_owner, "owner"))).status_code == 403


# ---------------------------------------------------------------------------
# Referral code -> venue attribution
# ---------------------------------------------------------------------------

_VENUE_BODY = {
    "name": "Gomti Greens Lawn",
    "category": "banquet_hall",
    "address": "Shaheed Path",
    "city": "Lucknow",
    "unit_type": "full_day",
    "base_price": "60000",
    "save_as_draft": True,
}


async def test_owner_lists_with_referral_code_and_cannot_switch_it(client, super_admin, seeded_verified_owner):
    first = (await _make_broker(client, super_admin))["broker"]
    second = (await _make_broker(client, super_admin, name="Meera Joshi"))["broker"]
    owner = _auth(seeded_verified_owner, "owner")

    # Lower-case with a stray space, the way people actually type codes.
    resp = await client.post(
        "/api/v1/venues", json={**_VENUE_BODY, "referral_code": f" {first['referral_code'].lower()} "}, headers=owner
    )
    assert resp.status_code == 201, resp.text
    venue_id = resp.json()["id"]
    # The public venue shape never carries referral data.
    assert "referral_code" not in resp.json() and "broker_id" not in resp.json()

    ref = await client.get(f"/api/v1/owner/venues/{venue_id}/referral", headers=owner)
    assert ref.json()["referral_code"] == first["referral_code"]
    assert ref.json()["locked"] is True

    # The owner can't redirect the commission to someone else afterwards.
    resp = await client.put(
        f"/api/v1/owner/venues/{venue_id}/referral", json={"code": second["referral_code"]}, headers=owner
    )
    assert resp.status_code == 409

    # An admin can correct it, and that is audited.
    resp = await client.put(
        f"/api/v1/admin/venues/{venue_id}/broker", json={"broker_id": second["id"]}, headers=_auth(super_admin, "admin")
    )
    assert resp.status_code == 200 and resp.json()["referral_code"] == second["referral_code"]

    venues = await client.get("/api/v1/broker/venues", headers=_auth(uuid.UUID(second["id"]), "broker"))
    assert [v["name"] for v in venues.json()] == ["Gomti Greens Lawn"]
    assert (await client.get("/api/v1/broker/venues", headers=_auth(uuid.UUID(first["id"]), "broker"))).json() == []


async def test_invalid_or_paused_code_is_rejected_the_same_way(client, super_admin, seeded_verified_owner):
    broker = (await _make_broker(client, super_admin))["broker"]
    owner = _auth(seeded_verified_owner, "owner")

    resp = await client.post("/api/v1/venues", json={**_VENUE_BODY, "referral_code": "GK-XXX-0000"}, headers=owner)
    assert resp.status_code == 422

    await client.patch(
        f"/api/v1/admin/brokers/{broker['id']}", json={"status": "paused"}, headers=_auth(super_admin, "admin")
    )
    check = await client.post("/api/v1/referral-codes/check", json={"code": broker["referral_code"]}, headers=owner)
    assert check.status_code == 200 and check.json() == {"valid": False, "partner_name": None}


async def test_referral_code_check_requires_login(client):
    resp = await client.post("/api/v1/referral-codes/check", json={"code": "GK-ABC-1234"})
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Commission ledger and wallet
# ---------------------------------------------------------------------------


async def _attribute_seeded_venue(test_session_factory, unit_id, broker_id) -> uuid.UUID:
    async with test_session_factory() as session:
        async with session.begin():
            venue_id = (
                await session.execute(text("SELECT venue_id FROM inventory_units WHERE id = :u"), {"u": unit_id})
            ).scalar_one()
            venue = await session.get(Venue, venue_id)
            venue.broker_id = broker_id
            venue.referral_code = "GK-TEST-0001"
            venue.referred_at = datetime.now(timezone.utc)
            return venue_id


async def _book_and_pay(client, unit_id, admin_id) -> dict:
    created = await client.post(
        "/api/v1/bookings",
        json={"inventory_unit_id": str(unit_id), "guest_name": "Raj Kumar", "guest_email": "raj@example.com"},
    )
    assert created.status_code == 201, created.text
    booking = created.json()
    paid = await client.post(
        f"/api/v1/admin/bookings/{booking['booking_id']}/confirm-payment",
        json={"amount": "2000.00", "method": "upi", "reference": "UPI-1"},
        headers=_auth(admin_id, "admin"),
    )
    assert paid.status_code == 200, paid.text
    return booking


async def test_confirmed_payment_earns_commission_then_becomes_payable_and_is_paid_once(
    client, test_session_factory, super_admin, seeded_admin, seeded_unit
):
    broker = (await _make_broker(client, super_admin, commission_percent="5"))["broker"]
    broker_id = uuid.UUID(broker["id"])
    await _attribute_seeded_venue(test_session_factory, seeded_unit, broker_id)
    await _book_and_pay(client, seeded_unit, seeded_admin)

    headers = _auth(broker_id, "broker")
    me = (await client.get("/api/v1/broker/me", headers=headers)).json()
    # 5% of ₹2000. The event is in the future, so it is earned but not yet payable.
    assert Decimal(me["wallet"]["earned"]) == Decimal("100.00")
    assert Decimal(me["wallet"]["pending"]) == Decimal("100.00")
    assert Decimal(me["wallet"]["payable"]) == Decimal("0.00")

    bookings = (await client.get("/api/v1/broker/bookings", headers=headers)).json()
    assert len(bookings) == 1
    assert bookings[0]["payment_state"] == "received"
    assert bookings[0]["commission_status"] == "pending"
    # No customer personal details are exposed to a broker.
    assert not any(k.startswith("customer") or k.startswith("guest") for k in bookings[0])

    # Nothing payable yet -> settlement refused.
    resp = await client.post(
        f"/api/v1/admin/brokers/{broker_id}/payouts", json={"expected_amount": "100.00"}, headers=_auth(seeded_admin, "admin")
    )
    assert resp.status_code == 409

    # The event date passes.
    async with test_session_factory() as session:
        async with session.begin():
            await session.execute(
                text("UPDATE broker_commissions SET event_date = :d WHERE broker_id = :b"),
                {"d": date.today() - timedelta(days=3), "b": broker_id},
            )
    me = (await client.get("/api/v1/broker/me", headers=headers)).json()
    assert Decimal(me["wallet"]["payable"]) == Decimal("100.00")

    # A stale on-screen figure is refused rather than paying an unapproved amount.
    resp = await client.post(
        f"/api/v1/admin/brokers/{broker_id}/payouts", json={"expected_amount": "90.00"}, headers=_auth(seeded_admin, "admin")
    )
    assert resp.status_code == 409

    resp = await client.post(
        f"/api/v1/admin/brokers/{broker_id}/payouts",
        json={"expected_amount": "100.00", "method": "upi", "reference": "PAYOUT-77"},
        headers=_auth(seeded_admin, "admin"),
    )
    assert resp.status_code == 201, resp.text
    assert Decimal(resp.json()["amount"]) == Decimal("100.00")

    # Paying twice is impossible: the balance is gone.
    resp = await client.post(
        f"/api/v1/admin/brokers/{broker_id}/payouts", json={"expected_amount": "100.00"}, headers=_auth(seeded_admin, "admin")
    )
    assert resp.status_code == 409

    me = (await client.get("/api/v1/broker/me", headers=headers)).json()
    assert Decimal(me["wallet"]["paid"]) == Decimal("100.00")
    assert Decimal(me["wallet"]["payable"]) == Decimal("0.00")
    payouts = (await client.get("/api/v1/broker/payouts", headers=headers)).json()
    assert len(payouts) == 1 and payouts[0]["reference"] == "PAYOUT-77"


async def test_refund_reverses_commission(client, test_session_factory, super_admin, seeded_admin, seeded_unit):
    broker = (await _make_broker(client, super_admin, commission_percent="5"))["broker"]
    broker_id = uuid.UUID(broker["id"])
    await _attribute_seeded_venue(test_session_factory, seeded_unit, broker_id)
    booking = await _book_and_pay(client, seeded_unit, seeded_admin)

    # Event is far in the future -> full-refund tier.
    resp = await client.post(
        f"/api/v1/bookings/manage/{booking['manage_token']}/cancel", json={"reason": "Change of plans"}
    )
    assert resp.status_code == 200, resp.text

    async with test_session_factory() as session:
        row = (await session.execute(select(BrokerCommission))).scalar_one()
        assert row.amount == Decimal("100.00")
        assert row.reversed_amount == Decimal("100.00")

    wallet = (await client.get("/api/v1/broker/me", headers=_auth(broker_id, "broker"))).json()["wallet"]
    assert Decimal(wallet["earned"]) == Decimal("0.00")
    assert Decimal(wallet["reversed"]) == Decimal("100.00")


async def test_rate_is_snapshotted_and_platform_commission_basis_works(
    client, test_session_factory, super_admin, seeded_admin, seeded_unit
):
    broker = (
        await _make_broker(client, super_admin, commission_percent="20", commission_basis="platform_commission")
    )["broker"]
    broker_id = uuid.UUID(broker["id"])
    await _attribute_seeded_venue(test_session_factory, seeded_unit, broker_id)
    await _book_and_pay(client, seeded_unit, seeded_admin)

    # Platform commission is 10% of ₹2000 = ₹200; the broker gets 20% of that.
    rows = (await client.get(f"/api/v1/admin/brokers/{broker_id}/commissions", headers=_auth(seeded_admin, "admin"))).json()
    assert Decimal(rows[0]["basis_amount"]) == Decimal("200.00")
    assert Decimal(rows[0]["amount"]) == Decimal("40.00")

    # Changing the rate later doesn't rewrite what was already earned.
    await client.patch(
        f"/api/v1/admin/brokers/{broker_id}", json={"commission_percent": "1"}, headers=_auth(super_admin, "admin")
    )
    rows = (await client.get(f"/api/v1/admin/brokers/{broker_id}/commissions", headers=_auth(seeded_admin, "admin"))).json()
    assert Decimal(rows[0]["rate"]) == Decimal("20.00") and Decimal(rows[0]["amount"]) == Decimal("40.00")


async def test_no_commission_without_a_referral_partner(client, test_session_factory, seeded_admin, seeded_unit):
    await _book_and_pay(client, seeded_unit, seeded_admin)
    async with test_session_factory() as session:
        assert (await session.execute(select(BrokerCommission))).scalars().all() == []


# ---------------------------------------------------------------------------
# Banners
# ---------------------------------------------------------------------------


async def test_banner_lifecycle_and_public_visibility(client, seeded_admin, seeded_customer):
    admin = _auth(seeded_admin, "admin")
    live = await client.post(
        "/api/v1/admin/banners",
        json={"title": "Wedding season dates are open", "cta_label": "See venues", "cta_url": "/search?category=banquet_hall"},
        headers=admin,
    )
    assert live.status_code == 201, live.text
    future = await client.post(
        "/api/v1/admin/banners",
        json={"title": "Diwali offers", "start_at": (datetime.now(timezone.utc) + timedelta(days=5)).isoformat()},
        headers=admin,
    )
    assert future.status_code == 201
    hidden = await client.post("/api/v1/admin/banners", json={"title": "Draft banner", "enabled": False}, headers=admin)
    assert hidden.status_code == 201

    public = await client.get("/api/v1/banners?placement=home_hero")
    assert [b["title"] for b in public.json()] == ["Wedding season dates are open"]
    assert len((await client.get("/api/v1/admin/banners", headers=admin)).json()) == 3

    # Image upload is re-encoded to WebP.
    resp = await client.post(
        f"/api/v1/admin/banners/{live.json()['id']}/image",
        files={"image": ("banner.png", real_image_bytes("PNG", size=(1200, 500)), "image/png")},
        headers=admin,
    )
    assert resp.status_code == 200 and resp.json()["image_url"].endswith(".webp")

    # Only admins manage banners.
    resp = await client.post(
        "/api/v1/admin/banners", json={"title": "Not allowed"}, headers=_auth(seeded_customer, "customer")
    )
    assert resp.status_code == 403

    assert (await client.delete(f"/api/v1/admin/banners/{hidden.json()['id']}", headers=admin)).status_code == 204


@pytest.mark.parametrize("bad_url", ["javascript:alert(1)", "//evil.example/x", "http://insecure.example", "data:text/html,x"])
async def test_banner_link_must_be_safe(client, seeded_admin, bad_url):
    resp = await client.post(
        "/api/v1/admin/banners", json={"title": "Bad link", "cta_url": bad_url}, headers=_auth(seeded_admin, "admin")
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Uploads
# ---------------------------------------------------------------------------


async def test_venue_photo_is_stored_as_webp_and_non_images_are_refused(
    client, test_session_factory, seeded_verified_owner
):
    owner = _auth(seeded_verified_owner, "owner")
    venue_id = (await client.post("/api/v1/venues", json=_VENUE_BODY, headers=owner)).json()["id"]

    big = real_image_bytes("JPEG", size=(4000, 3000))
    resp = await client.post(
        f"/api/v1/venues/{venue_id}/images", files={"image": ("big.jpg", big, "image/jpeg")}, headers=owner
    )
    assert resp.status_code == 201, resp.text
    async with test_session_factory() as session:
        media = (await session.execute(select(VenueMedia))).scalar_one()
        assert media.storage_key.endswith(".webp")

    # Claims to be a JPEG, isn't one.
    resp = await client.post(
        f"/api/v1/venues/{venue_id}/images",
        files={"image": ("evil.jpg", b"<?php echo 'not an image'; ?>", "image/jpeg")},
        headers=owner,
    )
    assert resp.status_code == 422


def test_optimizer_caps_dimensions_and_shrinks():
    from app.modules.storage.images import MAX_LONG_EDGE, optimize_image

    import io

    from PIL import Image

    buf = io.BytesIO()
    # Noise-free gradient so the JPEG is non-trivial but deterministic.
    Image.linear_gradient("L").resize((4200, 2800)).convert("RGB").save(buf, format="JPEG", quality=95)
    out, content_type, (w, h) = optimize_image(buf.getvalue())
    assert content_type == "image/webp"
    assert max(w, h) == MAX_LONG_EDGE
    assert len(out) < len(buf.getvalue())


# ---------------------------------------------------------------------------
# Records, exports, history
# ---------------------------------------------------------------------------


async def test_registers_and_csv_export(client, test_session_factory, super_admin, seeded_admin, seeded_unit):
    broker = (await _make_broker(client, super_admin, commission_percent="5"))["broker"]
    venue_id = await _attribute_seeded_venue(test_session_factory, seeded_unit, uuid.UUID(broker["id"]))
    # A venue name that would be a live formula if written to CSV unescaped.
    async with test_session_factory() as session:
        async with session.begin():
            (await session.get(Venue, venue_id)).name = "=HYPERLINK(\"http://evil\")"
    await _book_and_pay(client, seeded_unit, seeded_admin)
    admin = _auth(seeded_admin, "admin")

    venues = (await client.get("/api/v1/admin/records/venues", headers=admin)).json()
    assert len(venues) == 1
    assert venues[0]["broker_name"] == "Ravi Kumar"
    assert Decimal(venues[0]["amount_received"]) == Decimal("2000.00")
    assert Decimal(venues[0]["platform_commission"]) == Decimal("200.00")

    bookings = (await client.get("/api/v1/admin/records/bookings?payment=received", headers=admin)).json()
    assert len(bookings) == 1
    row = bookings[0]
    assert row["payment_reference"] == "UPI-1" and row["payment_method"] == "upi"
    assert Decimal(row["owner_share"]) == Decimal("1800.00")
    assert Decimal(row["broker_commission"]) == Decimal("100.00")
    assert row["customer_name"] == "Raj Kumar"

    resp = await client.get("/api/v1/admin/records/export/venues.csv", headers=admin)
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/csv")
    assert "attachment" in resp.headers["content-disposition"]
    body = resp.content.decode("utf-8")
    assert body.startswith("﻿Venue ID,Venue,Category")
    assert "'=HYPERLINK" in body  # neutralised, not executable

    resp = await client.get("/api/v1/admin/records/export/bookings.csv", headers=admin)
    assert "Booking ref" in resp.text and "UPI-1" in resp.text

    # Downloads are themselves on the record.
    async with test_session_factory() as session:
        exports = (
            await session.execute(select(AuditLog).where(AuditLog.action == "records.exported"))
        ).scalars().all()
        assert {e.extra_data["kind"] for e in exports} == {"venues", "bookings"}

    listing = (await client.get("/api/v1/admin/records/exports", headers=admin)).json()
    assert {e["kind"] for e in listing} >= {"venues", "bookings", "payments", "brokers", "audit_log"}
    assert (await client.get("/api/v1/admin/records/export/nope.csv", headers=admin)).status_code == 404


async def test_records_are_admin_only(client, seeded_customer, seeded_verified_owner):
    for user_id, role in ((seeded_customer, "customer"), (seeded_verified_owner, "owner")):
        assert (await client.get("/api/v1/admin/records/bookings", headers=_auth(user_id, role))).status_code == 403
        assert (
            await client.get("/api/v1/admin/records/export/users.csv", headers=_auth(user_id, role))
        ).status_code == 403
    assert (await client.get("/api/v1/admin/records/export/users.csv")).status_code == 401


async def test_venue_history_records_each_step(client, seeded_admin, seeded_verified_owner, super_admin):
    owner = _auth(seeded_verified_owner, "owner")
    broker = (await _make_broker(client, super_admin))["broker"]
    venue_id = (
        await client.post("/api/v1/venues", json={**_VENUE_BODY, "referral_code": broker["referral_code"]}, headers=owner)
    ).json()["id"]
    await client.patch(f"/api/v1/venues/{venue_id}", json={"description": "A lawn by the river."}, headers=owner)

    history = await client.get(f"/api/v1/admin/venues/{venue_id}/history", headers=_auth(seeded_admin, "admin"))
    assert history.status_code == 200
    actions = [e["action"] for e in history.json()["timeline"]]
    assert actions[0] == "venue.created"
    assert "venue.referral_applied" in actions and "venue.updated" in actions
    assert history.json()["timeline"][0]["actor_name"] == "Mr. Verma"


# ---------------------------------------------------------------------------
# Admin users list
# ---------------------------------------------------------------------------


async def test_user_search_filters_and_accounts_without_email_do_not_break_the_list(
    client, test_session_factory, seeded_admin
):
    async with test_session_factory() as session:
        async with session.begin():
            session.add(User(name="Phone Only Person", phone=_phone(), password_hash="x", role="customer", email=None))
            session.add(User(name="Someone Else", phone=_phone(), password_hash="x", role="customer", email="else@example.com"))
    admin = _auth(seeded_admin, "admin")
    everyone = await client.get("/api/v1/admin/users", headers=admin)
    assert everyone.status_code == 200
    found = await client.get("/api/v1/admin/users?search=phone only", headers=admin)
    assert [u["name"] for u in found.json()] == ["Phone Only Person"]
    assert found.json()[0]["email"] is None


# ---------------------------------------------------------------------------
# Share pages
# ---------------------------------------------------------------------------


async def test_share_page_has_open_graph_tags_and_escapes_owner_text(client, test_session_factory, seeded_unit):
    async with test_session_factory() as session:
        async with session.begin():
            venue_id = (
                await session.execute(text("SELECT venue_id FROM inventory_units WHERE id = :u"), {"u": seeded_unit})
            ).scalar_one()
            venue = await session.get(Venue, venue_id)
            venue.tagline = 'Floodlit turf "><script>alert(1)</script>'
            slug = venue.slug

    resp = await client.get(f"/share/venues/{slug}")
    assert resp.status_code == 200
    html = resp.text
    assert '<meta property="og:title" content="The Grand Turf Arena, Lucknow | GroundKart">' in html
    assert '<meta property="og:type" content="place">' in html
    assert f'/venues/{slug}"' in html
    assert 'name="twitter:card" content="summary_large_image"' in html
    assert "From ₹2,000 per hour" in html
    assert "<script>" not in html and "&lt;script&gt;" in html


async def test_share_page_never_previews_an_unpublished_venue(client, test_session_factory, seeded_unit):
    async with test_session_factory() as session:
        async with session.begin():
            venue_id = (
                await session.execute(text("SELECT venue_id FROM inventory_units WHERE id = :u"), {"u": seeded_unit})
            ).scalar_one()
            venue = await session.get(Venue, venue_id)
            venue.status = "pending_review"
            slug = venue.slug
    resp = await client.get(f"/share/venues/{slug}")
    assert resp.status_code == 404
    assert "The Grand Turf Arena" not in resp.text
    assert 'property="og:title"' in resp.text  # still a valid, generic card

    assert (await client.get("/share/venues/..%2F..%2Fetc")).status_code == 404
    assert (await client.get("/share/categories/sports")).status_code == 200
