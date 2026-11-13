"""@compliance: the drafts are marked for lawyer review, in sync with what the
site renders, and contain no invented business facts."""
import re
import subprocess
import sys

import pytest

from app.modules.privacy.legal_profile import PLACEHOLDER_FIELDS
from tests.compliance_support import DRAFTS_DIR, LEGAL_DIR, REPO_ROOT

pytestmark = pytest.mark.compliance

ALL_DRAFTS = sorted(p for p in DRAFTS_DIR.glob("*.md") if p.name != "README.md")


def test_drafts_are_in_sync_with_rendered_pages():
    result = subprocess.run([sys.executable, str(REPO_ROOT / "docs" / "compliance" / "sync_drafts.py"), "--check"], capture_output=True, text=True)
    assert result.returncode == 0, result.stdout


@pytest.mark.parametrize("path", ALL_DRAFTS, ids=lambda p: p.name)
def test_every_draft_is_marked_for_lawyer_review(path):
    text = path.read_text(encoding="utf-8")
    assert "DRAFT FOR LAWYER REVIEW" in text


def test_every_placeholder_label_is_known_and_listed_in_decisions():
    decisions = (REPO_ROOT / "DECISIONS_NEEDED.md").read_text()
    labels = set()
    for p in [*LEGAL_DIR.glob("*.md"), *ALL_DRAFTS]:
        labels |= set(re.findall(r"\[\[OWNER TO FILL: ([^\]]+)\]\]", p.read_text(encoding="utf-8")))
    page_labels = set()
    for p in LEGAL_DIR.glob("*.md"):
        page_labels |= set(re.findall(r"\[\[OWNER TO FILL: ([^\]]+)\]\]", p.read_text(encoding="utf-8")))
    # Every placeholder on a public page can be filled from Admin → Settings.
    assert page_labels <= set(PLACEHOLDER_FIELDS), page_labels - set(PLACEHOLDER_FIELDS)
    # Every placeholder anywhere is explained in DECISIONS_NEEDED.md.
    missing = [label for label in labels if f"[[OWNER TO FILL: {label}]]" not in decisions]
    assert not missing, missing


def test_no_template_token_is_left_unrecognised():
    known = {"hold_minutes", "full_refund_hours", "partial_refund_hours", "partial_refund_percent"}
    for p in LEGAL_DIR.glob("*.md"):
        assert set(re.findall(r"\{\{(\w+)\}\}", p.read_text(encoding="utf-8"))) <= known, p.name
