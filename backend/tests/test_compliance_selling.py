"""@compliance check 6: selling online (E-Commerce Rules 2020 r.4-6; CCPA Dark
Patterns Guidelines 2023)."""
import pytest
from sqlalchemy import update

from app.models.core import OwnerVerification, Review, User, Venue
from tests.compliance_support import auth, client, fetch, legal, make_booking, make_unit, make_user, make_venue_with_unit  # noqa: F401

pytestmark = pytest.mark.compliance


@pytest.fixture
async def world(test_session_factory):
    owner = await make_user(test_session_factory, "owner", verified=True, name="Sunil Rao")
    venue_id, unit_id = await make_venue_with_unit(test_session_factory, owner.id)
    customer = await make_user(test_session_factory, "customer", name="Kavya Nair")
    other = await make_user(test_session_factory, "customer", name="Other Person")
    completed = await make_booking(test_session_factory, venue_id, unit_id, customer.id, status="completed")
    unit2 = await make_unit(test_session_factory, venue_id)
    confirmed = await make_booking(test_session_factory, venue_id, unit2, customer.id, status="confirmed")
    return dict(owner=owner, venue_id=venue_id, customer=customer, other=other, completed=completed, confirmed=confirmed)


async def test_6_5_review_without_a_booking_is_refused(client, world):
    resp = await client.post(
        f"/api/v1/venues/{world['venue_id']}/reviews",
        json={"rating": 5, "content": "Great!"},
        headers=auth(world["other"].id, "customer"),
    )
    assert resp.status_code in (400, 422)


async def test_6_5_review_of_someone_elses_booking_is_refused(client, world):
    resp = await client.post(
        f"/api/v1/venues/{world['venue_id']}/reviews",
        json={"rating": 5, "content": "Great!", "booking_id": str(world["completed"])},
        headers=auth(world["other"].id, "customer"),
    )
    assert resp.status_code == 403


async def test_6_5_review_requires_completed_booking_at_that_venue(client, world):
    resp = await client.post(
        f"/api/v1/venues/{world['venue_id']}/reviews",
        json={"rating": 4, "content": "Fine", "booking_id": str(world["confirmed"])},
        headers=auth(world["customer"].id, "customer"),
    )
    assert resp.status_code == 400


async def test_6_5_verified_review_is_labelled_and_shows_first_name_and_initial_only(client, world):
    resp = await client.post(
        f"/api/v1/venues/{world['venue_id']}/reviews",
        json={"rating": 5, "content": "Lovely turf", "booking_id": str(world["completed"])},
        headers=auth(world["customer"].id, "customer"),
    )
    assert resp.status_code == 201, resp.text
    listed = (await client.get(f"/api/v1/venues/{world['venue_id']}/reviews")).json()
    listed = listed["items"] if isinstance(listed, dict) else listed
    assert listed[0]["verified_booking"] is True
    assert listed[0]["user_name"] == "Kavya N."


async def test_6_5_unverified_legacy_reviews_are_not_public(client, world, test_session_factory):
    async with test_session_factory() as s:
        async with s.begin():
            s.add(Review(venue_id=world["venue_id"], user_id=world["other"].id, rating=1, content="fake"))
    listed = (await client.get(f"/api/v1/venues/{world['venue_id']}/reviews")).json()
    listed = listed["items"] if isinstance(listed, dict) else listed
    assert all(r["content"] != "fake" for r in listed)


async def test_6_2_venue_page_shows_the_seller(client, world, test_session_factory):
    async with test_session_factory() as s:
        async with s.begin():
            s.add(OwnerVerification(user_id=world["owner"].id, business_name="Rao Sports LLP", status="approved"))
    venue = (await client.get(f"/api/v1/venues/{world['venue_id']}")).json()
    assert venue["seller"]["business_name"] == "Rao Sports LLP"
    assert venue["seller"]["name"] == "Sunil Rao"
    # Seller block never leaks the owner's private contact details publicly.
    assert "phone" not in venue["seller"] and "email" not in venue["seller"]


def test_6_1_refund_policy_covers_all_cases_and_states_what_does_not_apply():
    md = legal("refunds.en.md")
    for phrase in ["{{full_refund_hours}}", "venue owner or GroundKart cancels", "How refunds are paid",
                   "no shipping or delivery", "no return or exchange", "no product warranty"]:
        assert phrase.lower() in md.lower(), phrase


async def test_6_5_demo_rows_are_flagged_and_reported(client, test_session_factory):
    u = await make_user(test_session_factory, "owner", verified=True)
    async with test_session_factory() as s:
        async with s.begin():
            await s.execute(update(User).where(User.id == u.id).values(is_demo=True))
    resp = await client.get("/api/v1/meta/demo")
    assert resp.status_code == 200
    assert resp.json()["demo_data_present"] is True


async def test_6_5_production_refuses_to_start_with_demo_data(test_session_factory, monkeypatch):
    from app.modules.privacy import demo
    u = await make_user(test_session_factory, "owner", verified=True)
    async with test_session_factory() as s:
        async with s.begin():
            await s.execute(update(Venue).values(is_demo=False))
            await s.execute(update(User).where(User.id == u.id).values(is_demo=True))
    with pytest.raises(RuntimeError, match="DEMO DATA"):
        await demo.assert_no_demo_data_in_production(test_session_factory, environment="production")
    await demo.assert_no_demo_data_in_production(test_session_factory, environment="dev")


async def test_6_5_homepage_reviews_endpoint_returns_verified_reviews_only(client, world, test_session_factory):
    async with test_session_factory() as s:
        async with s.begin():
            await s.execute(update(Venue).where(Venue.id == world["venue_id"]).values(status="active"))
            s.add(Review(venue_id=world["venue_id"], user_id=world["other"].id, rating=1, content="An unverified review that must not appear"))
            s.add(Review(venue_id=world["venue_id"], user_id=world["customer"].id, booking_id=world["completed"], rating=5,
                         content="Verified review from a completed booking", verified=True))
    rows = (await client.get("/api/v1/reviews/recent")).json()
    assert [r["content"] for r in rows] == ["Verified review from a completed booking"]
    assert rows[0]["user_name"] == "Kavya N." and rows[0]["verified_booking"] is True
