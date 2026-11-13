"""Copy the shipped legal page sources into docs/compliance/drafts/.

The pages the site renders live in frontend/src/content/legal/ (so the
frontend Docker build can bundle them). The lawyer reviews the copies in
docs/compliance/drafts/. Run this after editing a page; the compliance test
test_compliance_drafts.py fails if the two ever differ.

    python docs/compliance/sync_drafts.py          # copy
    python docs/compliance/sync_drafts.py --check  # exit 1 if out of date
"""
import pathlib
import shutil
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
SRC = ROOT / "frontend" / "src" / "content" / "legal"
DST = ROOT / "docs" / "compliance" / "drafts"

PAIRS = {
    "privacy.en.md": "privacy-notice.en.md",
    "privacy.hi.md": "privacy-notice.hi.md",
    "terms.en.md": "terms.en.md",
    "refunds.en.md": "refunds.en.md",
    "cookies.en.md": "cookies.en.md",
    "grievance.en.md": "grievance.en.md",
    "data-rights.en.md": "data-rights.en.md",
}


def main() -> int:
    check = "--check" in sys.argv
    stale = []
    for src_name, dst_name in PAIRS.items():
        src, dst = SRC / src_name, DST / dst_name
        if check:
            if not dst.exists() or dst.read_bytes() != src.read_bytes():
                stale.append(dst_name)
        else:
            shutil.copyfile(src, dst)
    if stale:
        print("Out of date drafts:", ", ".join(stale))
        return 1
    print("drafts checked" if check else "drafts copied")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
