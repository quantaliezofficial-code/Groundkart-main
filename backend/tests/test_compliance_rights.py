"""@compliance beyond-8 B.1/B.2: Data Principal rights and erasure
(DPDP s.11-14, s.8(7); Rules r.8, r.14)."""
from datetime import timedelta

import pytest
from sqlalchemy import select

from app.models.core import (
    Booking, DataRequest, Notification, OwnerBankAccount, OwnerVerification, Payment, Review, SupportTicket, User,
)
from tests.compliance_support import auth, client, fetch, make_booking, make_user, make_venue_with_unit  # noqa: F401
from tests.conftest import REAL_PNG

pytestmark = pytest.mark.compliance


@pytest.fixture
async def person(client, test_session_factory):
    owner = await make_user(test_session_factory, "owner", verified=True)
    venue_id, unit_id = await make_venue_with_unit(test_session_factory, owner.id)
    me = await make_user(test_session_factory, "customer", name="Rohan Gupta")
    booking_id = await make_booking(test_session_factory, venue_id, unit_id, me.id, status="completed", customer_notes="Bring 2 extra balls")
    async with test_session_factory() as s:
        async with s.begin():
            s.add(Payment(booking_id=booking_id, amount=1500, status="success", gateway="offline"))
            s.add(Notification(user_id=me.id, type="test", message="Hello Rohan"))
            s.add(Review(venue_id=venue_id, user_id=me.id, booking_id=booking_id, rating=5, content="Great", verified=True))
    await client.post("/api/v1/support/tickets", json={"subject": "Question", "description": "My phone is 9812345678"}, headers=auth(me.id, "customer"))
    return dict(me=me, booking_id=booking_id, venue_id=venue_id, owner=owner)


async def test_B1_export_contains_all_my_data_and_recipients(client, person):
    resp = await client.get("/api/v1/me/data/export", headers=auth(person["me"].id, "customer"))
    assert resp.status_code == 200
    assert "attachment" in resp.headers.get("content-disposition", "")
    data = resp.json()
    for key in ["profile", "bookings", "payments", "support_tickets", "reviews", "notifications", "consents", "nominee", "data_requests", "recipients"]:
        assert key in data, key
    assert data["profile"]["email"] == person["me"].email
    assert data["bookings"][0]["customer_notes"] == "Bring 2 extra balls"
    assert any("venue owner" in r["recipient"].lower() for r in data["recipients"])
    assert "password_hash" not in resp.text


async def test_B1_user_can_correct_profile(client, person):
    resp = await client.patch("/api/v1/users/me", json={"name": "Rohan K. Gupta"}, headers=auth(person["me"].id, "customer"))
    assert resp.status_code == 200, resp.text
    assert resp.json()["name"] == "Rohan K. Gupta"


async def test_B1_user_can_name_a_nominee(client, person):
    h = auth(person["me"].id, "customer")
    resp = await client.put("/api/v1/me/nominee", json={"name": "Sita Gupta", "relationship": "Spouse", "email": "sita@example.com"}, headers=h)
    assert resp.status_code == 200, resp.text
    assert (await client.get("/api/v1/me/nominee", headers=h)).json()["name"] == "Sita Gupta"
    assert (await client.delete("/api/v1/me/nominee", headers=h)).status_code == 204


async def test_B1_data_request_gets_a_number_and_due_date(client, person, test_session_factory):
    resp = await client.post("/api/v1/me/data-requests", json={"type": "correction", "details": "My booking shows the wrong date"}, headers=auth(person["me"].id, "customer"))
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["request_number"].startswith("GK-D-")
    rows = await fetch(test_session_factory, DataRequest, request_number=body["request_number"])
    assert rows[0].due_at - rows[0].created_at == timedelta(days=30)
    assert rows[0].ticket_id is not None, "data requests also open a support ticket so admins see the SLA"


async def test_B2_erasure_anonymises_personal_data_and_keeps_financial_records_with_reason(client, person, test_session_factory):
    me = person["me"]
    async with test_session_factory() as s:
        async with s.begin():
            s.add(OwnerVerification(user_id=me.id, business_name="Gupta Sports", identification_number="enc:v1:xx", status="rejected"))
            s.add(OwnerBankAccount(owner_id=me.id, account_holder_name="Rohan", account_number="enc:v1:yy", ifsc_code="SBIN0000001"))
    resp = await client.post("/api/v1/me/erase", json={"confirm": "DELETE"}, headers=auth(me.id, "customer"))
    assert resp.status_code == 200, resp.text
    result = resp.json()
    assert result["status"] == "completed"
    assert any("payments" in k["table"] for k in result["kept"])
    assert all(k["reason"] for k in result["kept"])

    async with test_session_factory() as s:
        u = (await s.execute(select(User).where(User.id == me.id))).scalar_one()
        assert u.deleted_at and u.name == "Former customer" and me.email != u.email and me.phone != u.phone
        b = (await s.execute(select(Booking).where(Booking.id == person["booking_id"]))).scalar_one()
        assert b.customer_notes is None and b.amount == 1500
        assert (await s.execute(select(Payment).where(Payment.booking_id == b.id))).scalar_one().amount == 1500
        assert (await s.execute(select(Notification).where(Notification.user_id == me.id))).first() is None
        t = (await s.execute(select(SupportTicket).where(SupportTicket.creator_id == me.id))).scalars().all()
        assert all("9812345678" not in x.description for x in t)
        r = (await s.execute(select(Review).where(Review.booking_id == b.id))).scalar_one()
        assert r.user_id == me.id  # kept, but the public name becomes "Former customer"
        ov = (await s.execute(select(OwnerVerification).where(OwnerVerification.user_id == me.id))).scalars().all()
        assert all(v.identification_number is None and v.business_name is None for v in ov)
        assert (await s.execute(select(OwnerBankAccount).where(OwnerBankAccount.owner_id == me.id))).first() is None
    reviews = (await client.get(f"/api/v1/venues/{person['venue_id']}/reviews")).json()
    reviews = reviews["items"] if isinstance(reviews, dict) else reviews
    assert reviews[0]["user_name"] == "Former customer"


async def test_B2_delete_me_route_also_erases(client, person, test_session_factory):
    resp = await client.delete("/api/v1/users/me", headers=auth(person["me"].id, "customer"))
    assert resp.status_code == 204
    async with test_session_factory() as s:
        u = (await s.execute(select(User).where(User.id == person["me"].id))).scalar_one()
        assert u.email != person["me"].email


async def test_B2_erasure_deletes_uploaded_verification_documents(client, test_session_factory):
    from app.storage_client import get_private_file_storage
    me = await make_user(test_session_factory)
    resp = await client.post("/api/v1/owner/verification", files={"document": ("id.png", REAL_PNG, "image/png")},
                             data={"identification_type": "pan", "identification_number": "ABCDE1234F"}, headers=auth(me.id, "customer"))
    assert resp.status_code == 201
    key = (await fetch(test_session_factory, OwnerVerification, user_id=me.id))[0].storage_key
    storage = get_private_file_storage()
    await storage.get_object(key)  # exists
    await client.post("/api/v1/me/erase", json={"confirm": "DELETE"}, headers=auth(me.id, "customer"))
    with pytest.raises(Exception):
        await storage.get_object(key)


async def test_B2_guest_can_erase_through_manage_link(client, test_session_factory):
    owner = await make_user(test_session_factory, "owner", verified=True)
    _, unit_id = await make_venue_with_unit(test_session_factory, owner.id, days_ahead=40)
    created = await client.post("/api/v1/bookings", json={"inventory_unit_id": str(unit_id), "guest_name": "Ravi", "guest_email": "ravi@example.com", "guest_phone": "9811100022", "age_confirmed": True})
    token = created.json()["manage_token"]
    resp = await client.post(f"/api/v1/bookings/manage/{token}/erase", json={"confirm": "DELETE"})
    assert resp.status_code == 200, resp.text
    b = (await fetch(test_session_factory, Booking))[0]
    assert b.guest_email != "ravi@example.com" and b.guest_phone is None
