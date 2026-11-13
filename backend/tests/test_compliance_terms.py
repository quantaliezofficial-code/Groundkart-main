"""@compliance check 5: Terms of Service (Contract Act 1872; Intermediary Rules 2021 r.3)."""
import re

import pytest

from app.models.core import ConsentRecord
from app.modules.privacy.versions import TERMS_VERSION
from tests.compliance_support import client, fetch, legal, make_user, make_venue_with_unit  # noqa: F401

pytestmark = pytest.mark.compliance

TERMS = legal("terms.en.md")


def _heads():
    return [h.lower() for h in re.findall(r"^## \d+\. (.+)$", TERMS, flags=re.M)]


def test_5_1_terms_cover_service_pricing_payment_cancellation_and_liability():
    heads = _heads()
    for h in ["what groundkart does", "bookings", "prices and payment", "cancellations and refunds", "our responsibility"]:
        assert h in heads, h


def test_5_1_cancellation_tiers_are_rendered_from_live_settings_not_hard_coded():
    section = TERMS.split("## 5. Cancellations and refunds", 1)[1].split("\n## ", 1)[0]
    for token in ["{{full_refund_hours}}", "{{partial_refund_hours}}", "{{partial_refund_percent}}"]:
        assert token in section
    assert "48 hours" not in section and "50%" not in section


def test_5_2_terms_state_governing_law_jurisdiction_and_dispute_steps():
    heads = _heads()
    assert "governing law and jurisdiction" in heads
    assert "laws of India" in TERMS
    assert "[[OWNER TO FILL: jurisdiction city]]" in TERMS or "courts at" in TERMS
    assert "complaints and disputes" in heads
    assert "Consumer Protection Act, 2019" in TERMS


def test_5_3_terms_include_user_content_rules_and_complaint_handling():
    assert "reviews and other content" in _heads()
    assert "Reporting content" in TERMS
    assert "24 hours" in TERMS and "15 days" in TERMS


def test_5_3_terms_state_marketplace_role_and_age_requirement():
    assert "marketplace" in TERMS and "not the owner or operator" in TERMS
    assert "18 or older" in TERMS


async def test_5_4_guest_checkout_records_terms_acceptance_with_version(client, test_session_factory):
    owner = await make_user(test_session_factory, "owner", verified=True)
    _, unit_id = await make_venue_with_unit(test_session_factory, owner.id)
    resp = await client.post(
        "/api/v1/bookings",
        json={"inventory_unit_id": str(unit_id), "guest_name": "Ravi", "guest_email": "ravi@example.com", "age_confirmed": True},
    )
    assert resp.status_code == 201, resp.text
    booking_id = resp.json()["booking_id"]
    rows = [r for r in await fetch(test_session_factory, ConsentRecord) if str(r.booking_id) == booking_id]
    assert {r.purpose for r in rows} >= {"terms", "privacy_notice", "age_18_plus"}
    assert all(r.terms_version == TERMS_VERSION for r in rows)


async def test_5_1_sitemap_lists_every_legal_page(client):
    body = (await client.get("/sitemap.xml")).text
    for path in ("/privacy", "/terms", "/refunds", "/cookies", "/grievance", "/your-data"):
        assert f"{path}</loc>" in body, path
