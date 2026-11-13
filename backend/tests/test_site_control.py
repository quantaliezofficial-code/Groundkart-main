"""Super admin control of the website: homepage content, asset library and
review moderation (app/routers/site.py)."""
import io

import pytest
from PIL import Image
from sqlalchemy import select, update

from app.models.core import AuditLog, Review, Venue
from tests.compliance_support import auth, client, make_booking, make_user, make_venue_with_unit  # noqa: F401


def png_bytes(color=(10, 120, 60)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (64, 40), color).save(buf, "PNG")
    return buf.getvalue()


@pytest.fixture
async def people(test_session_factory):
    return dict(
        super=await make_user(test_session_factory, "admin", super_admin=True, name="Owner Super"),
        admin=await make_user(test_session_factory, "admin", name="Plain Admin"),
    )


VALID = {
    "hero": {"title": "Find a ground", "title_highlight": "near you.", "subtitle": "Real photos and open dates."},
    "sections": {"founder": False},
    "faq": [{"q": "Is booking free?", "a": "Searching and sending a request are free."}],
}


async def test_homepage_content_publish_read_version_and_restore(client, people):
    assert (await client.get("/api/v1/site/homepage")).json()["data"] == {}

    su = auth(people["super"].id, "admin")
    r = await client.put("/api/v1/admin/site/homepage", headers=su, json={"data": VALID, "base_version": 0, "note": "first"})
    assert r.status_code == 200, r.text
    assert r.json()["version"] == 1
    public = (await client.get("/api/v1/site/homepage")).json()
    assert public["data"]["hero"]["title"] == "Find a ground" and public["data"]["sections"] == {"founder": False}

    # A stale editor cannot overwrite a newer version.
    stale = await client.put("/api/v1/admin/site/homepage", headers=su, json={"data": {}, "base_version": 0})
    assert stale.status_code == 409

    r2 = await client.put("/api/v1/admin/site/homepage", headers=su, json={"data": {"closing": {"title": "See open dates"}}, "base_version": 1})
    assert r2.json()["version"] == 2
    revs = (await client.get("/api/v1/admin/site/homepage/revisions", headers=su)).json()
    assert [v["version"] for v in revs] == [2, 1] and revs[1]["note"] == "first"

    restored = await client.post(f"/api/v1/admin/site/homepage/revisions/{revs[1]['id']}/restore", headers=su)
    assert restored.json()["version"] == 3 and restored.json()["data"]["hero"]["title"] == "Find a ground"

    reset = await client.delete("/api/v1/admin/site/homepage", headers=su)
    assert reset.json()["data"] == {} and reset.json()["version"] == 4


async def test_only_the_super_admin_edits_website_content(client, people):
    plain = auth(people["admin"].id, "admin")
    assert (await client.put("/api/v1/admin/site/homepage", headers=plain, json={"data": VALID})).status_code == 403
    assert (await client.delete("/api/v1/admin/site/homepage", headers=plain)).status_code == 403
    view = (await client.get("/api/v1/admin/site/homepage", headers=plain)).json()
    assert view["can_edit"] is False
    files = {"image": ("x.png", png_bytes(), "image/png")}
    assert (await client.post("/api/v1/admin/site/assets", headers=plain, files=files, data={"label": "x"})).status_code == 403
    assert (await client.put("/api/v1/admin/site/homepage", json={"data": VALID})).status_code == 401


@pytest.mark.parametrize(
    "bad",
    [
        {"hero": {"title": "x" * 121}},
        {"hero": {"script": "<b>"}},
        {"occasions": [{"key": "a", "label": "A", "category": "casino", "image_url": "/img/photos/occ-sports-720.webp", "alt": "a"}] * 3},
        {"hero": {"image_url": "https://evil.example/x.jpg"}},
        {"hero": {"image_url": "/img/../../etc/passwd"}},
        {"founder": {"link_url": "javascript:alert(1)"}},
        {"faq": [{"q": "?", "a": "short"}]},
    ],
)
async def test_homepage_content_is_validated(client, people, bad):
    r = await client.put("/api/v1/admin/site/homepage", headers=auth(people["super"].id, "admin"), json={"data": bad})
    assert r.status_code == 422, r.text


async def test_asset_library_upload_use_and_protected_delete(client, people):
    su = auth(people["super"].id, "admin")
    up = await client.post(
        "/api/v1/admin/site/assets", headers=su,
        files={"image": ("hall.png", png_bytes(), "image/png")}, data={"label": "Hall", "alt_text": "A banquet hall"},
    )
    assert up.status_code == 201, up.text
    asset = up.json()
    assert asset["width"] == 64 and asset["url"].endswith(".webp")

    occ = [
        {"key": k, "label": k.title(), "category": c, "image_url": asset["url"] if i == 0 else "/img/photos/occ-sports-720.webp", "alt": "photo"}
        for i, (k, c) in enumerate([("weddings", "banquet"), ("sports", "sports"), ("parties", "party_hall")])
    ]
    pub = await client.put("/api/v1/admin/site/homepage", headers=su, json={"data": {"occasions": occ, "hero": {"image_url": asset["url"]}}})
    assert pub.status_code == 200, pub.text

    blocked = await client.delete(f"/api/v1/admin/site/assets/{asset['id']}", headers=su)
    assert blocked.status_code == 409 and "Homepage hero" in blocked.json()["detail"]

    await client.delete("/api/v1/admin/site/homepage", headers=su)
    renamed = await client.patch(f"/api/v1/admin/site/assets/{asset['id']}", headers=su, json={"alt_text": "Hall at night"})
    assert renamed.json()["alt_text"] == "Hall at night"
    assert (await client.delete(f"/api/v1/admin/site/assets/{asset['id']}", headers=su)).status_code == 204
    assert (await client.get("/api/v1/admin/site/assets", headers=su)).json() == []

    bad = await client.post("/api/v1/admin/site/assets", headers=su, files={"image": ("x.png", b"not an image", "image/png")}, data={"label": "x"})
    assert bad.status_code == 422


async def test_review_moderation_hides_features_and_keeps_ratings_honest(client, people, test_session_factory):
    owner = await make_user(test_session_factory, "owner", verified=True)
    venue_id, unit_id = await make_venue_with_unit(test_session_factory, owner.id)
    happy = await make_user(test_session_factory, "customer", name="Asha Kumar")
    unhappy = await make_user(test_session_factory, "customer", name="Ravi Shah")
    b1 = await make_booking(test_session_factory, venue_id, unit_id, happy.id, status="completed")
    async with test_session_factory() as s:
        async with s.begin():
            await s.execute(update(Venue).where(Venue.id == venue_id).values(status="active"))
            good = Review(venue_id=venue_id, user_id=happy.id, booking_id=b1, rating=5, content="Great ground, well kept and on time.", verified=True)
            rude = Review(venue_id=venue_id, user_id=unhappy.id, rating=1, content="Abusive text naming a staff member's phone", verified=True)
            unverified = Review(venue_id=venue_id, user_id=unhappy.id, rating=5, content="Never booked but loved it anyway, honestly", verified=False)
            s.add_all([good, rude, unverified])
        ids = dict(good=good.id, rude=rude.id, unverified=unverified.id)

    su = auth(people["super"].id, "admin")
    no_reason = await client.patch(f"/api/v1/admin/reviews/{ids['rude']}/moderation", headers=su, json={"hidden": True})
    assert no_reason.status_code == 422
    hidden = await client.patch(f"/api/v1/admin/reviews/{ids['rude']}/moderation", headers=su, json={"hidden": True, "reason": "Personal data of a staff member"})
    assert hidden.status_code == 200 and hidden.json()["hidden_reason"] == "Personal data of a staff member"

    public = (await client.get(f"/api/v1/venues/{venue_id}/reviews")).json()
    assert [r["content"] for r in public] == ["Great ground, well kept and on time."]
    async with test_session_factory() as s:
        assert float((await s.get(Venue, venue_id)).avg_rating) == 5.0

    assert (await client.patch(f"/api/v1/admin/reviews/{ids['unverified']}/moderation", headers=su, json={"featured": True})).status_code == 422
    assert (await client.patch(f"/api/v1/admin/reviews/{ids['rude']}/moderation", headers=su, json={"featured": True})).status_code == 422
    feat = await client.patch(f"/api/v1/admin/reviews/{ids['good']}/moderation", headers=su, json={"featured": True})
    assert feat.json()["featured"] is True
    recent = (await client.get("/api/v1/reviews/recent")).json()
    assert recent[0]["featured"] is True and all("Abusive" not in r["content"] for r in recent)

    plain = auth(people["admin"].id, "admin")
    assert (await client.patch(f"/api/v1/admin/reviews/{ids['good']}/moderation", headers=plain, json={"featured": False})).status_code == 403

    admin_list = (await client.get("/api/v1/admin/reviews", headers=plain)).json()
    rude_row = next(r for r in admin_list if r["id"] == str(ids["rude"]))
    assert rude_row["hidden_at"] and rude_row["hidden_reason"]

    unhide = await client.patch(f"/api/v1/admin/reviews/{ids['rude']}/moderation", headers=su, json={"hidden": False})
    assert unhide.json()["hidden_at"] is None
    async with test_session_factory() as s:
        assert float((await s.get(Venue, venue_id)).avg_rating) == 3.0
        actions = (await s.execute(select(AuditLog.action).where(AuditLog.entity_type == "review"))).scalars().all()
    assert actions.count("review.moderated") >= 3
