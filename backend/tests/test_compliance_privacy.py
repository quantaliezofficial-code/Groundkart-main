"""@compliance check 1: Privacy Notice (DPDP Act s.5, Rules r.3, SPDI r.4).

Browser-side checks (links next to every form, language switch) live in
frontend/e2e/compliance/privacy.spec.ts; these cover the content and the API
that feeds it."""
import re

import pytest

from app.modules.privacy.versions import NOTICE_VERSION, TERMS_VERSION
from tests.compliance_support import client, legal  # noqa: F401

pytestmark = pytest.mark.compliance

EN = legal("privacy.en.md")
HI = legal("privacy.hi.md")


def _headings(md: str) -> list[str]:
    return [h.strip().lower() for h in re.findall(r"^#{2,3} (.+)$", md, flags=re.M)]


def test_1_2_notice_lists_each_data_type():
    table = EN.split("## Data we collect", 1)[1].split("\n## ", 1)[0]
    for item in ["Name, mobile number, email", "Password", "Booking details", "Payment and refund",
                 "support tickets", "Reviews", "identity document", "bank account", "IP address", "cookie"]:
        assert item.lower() in table.lower(), f"data table is missing {item!r}"


def test_1_3_every_data_row_has_a_specific_purpose_ground_retention_and_recipient():
    table = EN.split("## Data we collect", 1)[1].split("\n## ", 1)[0]
    rows = [r for r in table.splitlines() if r.startswith("| ") and not r.startswith("| Data") and not r.startswith("| ---")]
    assert len(rows) >= 12
    for row in rows:
        cells = [c.strip() for c in row.strip("|").split("|")]
        assert len(cells) == 6, row
        assert all(cells), f"empty cell in row: {row}"


def test_1_4_notice_states_retention_and_recipients_by_name():
    heads = _headings(EN)
    assert "how long we keep it" in heads
    assert "who we share it with" in heads
    assert "hosting provider" in EN and "Venue owners" in EN and "Banks and UPI providers" in EN


def test_1_5_notice_explains_withdrawal_rights_and_board_complaint():
    heads = _headings(EN)
    assert "your rights" in heads
    for phrase in ["Withdraw consent", "Get a summary", "Correct or update", "erase", "Nominate", "Data Protection Board of India"]:
        assert phrase.lower() in EN.lower(), phrase
    assert "90-day" in EN


def test_1_6_notice_describes_security_practices_and_last_updated_date():
    assert "how we protect your data" in _headings(EN)
    assert re.search(r"Version \d+\.\d+ · Last updated \d{1,2} \w+ 20\d\d", EN)
    assert f"Version {NOTICE_VERSION}" in EN
    assert f"Version {TERMS_VERSION}" in legal("terms.en.md")


def test_1_1_hindi_notice_exists_with_same_version_and_structure():
    assert f"संस्करण {NOTICE_VERSION}" in HI
    assert len(_headings(HI)) == len(_headings(EN))
    # Same number of data rows in the table
    count = lambda md: len([r for r in md.splitlines() if r.startswith("| ") and "---" not in r])
    assert count(HI) == count(EN)


def test_1_1_notice_states_adults_only_and_no_childrens_details():
    assert "18 and over" in EN
    assert "do not enter the personal details of children" in EN


async def test_1_1_legal_profile_endpoint_publishes_versions_and_live_booking_terms(client):
    resp = await client.get("/api/v1/legal/profile")
    assert resp.status_code == 200
    data = resp.json()
    assert data["notice_version"] == NOTICE_VERSION
    assert data["terms_version"] == TERMS_VERSION
    assert data["booking_terms"] == {
        "hold_minutes": 30,
        "full_refund_hours": 48,
        "partial_refund_hours": 24,
        "partial_refund_percent": 50,
    }
    assert data["platform_fee"] == 0
    # Unset business facts are returned as null, never invented.
    assert data["legal_name"] is None
    assert data["grievance_officer_name"] is None
