#!/usr/bin/env python3
"""Score GroundKart against the 36-item website compliance checklist.

Runs the two automated suites that carry checklist item IDs and prints one
line per item:

  * API and server checks: backend pytest, marker `compliance`, test names
    start with the item ID (test_6_3_... is item 6.3);
  * browser checks: Playwright specs in frontend/e2e/compliance, titles
    carry "[6.3]" tags.

Item status:
  Pass             every check for the item passed
  Blocked (owner)  only checks tagged owner_facts / @owner-facts failed:
                   the code is done, a business fact is missing
                   (DECISIONS_NEEDED.md)
  Fail             at least one other check failed
  N/A (by design)  7.2 parental consent: the service is adults-only
                   (D-12). Counted as met and listed separately.
  No check         nothing automated covers the item

Usage (from the repository root, with the dev stack running for the
browser part: API on :8000, frontend on :3000):

  python3 docs/compliance/score.py                    # run both suites
  python3 docs/compliance/score.py --api-only         # backend only
  python3 docs/compliance/score.py --junit j.xml --playwright-json p.json   # score saved results
  python3 docs/compliance/score.py --markdown out.md  # also write a table

This is an engineering self-check, not legal advice: a Pass means the
behaviour the checklist describes can be found and tested on the running
site, not that a lawyer has approved the wording.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"

ITEMS: dict[str, str] = {}
for line in (ROOT / "docs/compliance/source_checklist.md").read_text(encoding="utf-8").splitlines():
    m = re.match(r"- \*\*(\d\.\d)\*\* (.+)", line)
    if m:
        ITEMS[m.group(1)] = m.group(2)
assert len(ITEMS) == 36, f"expected 36 checklist items, found {len(ITEMS)}"

NOT_APPLICABLE = {"7.2": "Adults-only service (D-12): no data from under-18s is collected, so no parental-consent flow."}

PY_ID = re.compile(r"^test_(\d)_(\d+)_")
PW_ID = re.compile(r"\[(\d\.\d)\]")


def owner_fact_tests() -> set[str]:
    names: set[str] = set()
    for f in BACKEND.glob("tests/test_compliance_*.py"):
        src = f.read_text(encoding="utf-8")
        for m in re.finditer(r"@pytest\.mark\.owner_facts\s*\n(?:@[^\n]+\n)*\s*(?:async\s+)?def\s+(test_\w+)", src):
            names.add(m.group(1))
    return names


class Result:
    def __init__(self) -> None:
        self.passed: list[str] = []
        self.failed: list[str] = []
        self.owner_failed: list[str] = []
        self.owner_passed: list[str] = []


def run_pytest(junit: Path) -> None:
    py = os.environ.get("PYTHON", sys.executable)
    cmd = [py, "-m", "pytest", "-q", "-p", "no:cacheprovider", "-m", "compliance", f"--junitxml={junit}"]
    print("$ (backend) " + " ".join(cmd[1:]), file=sys.stderr)
    subprocess.run(cmd, cwd=BACKEND, check=False)


def run_playwright(out: Path) -> None:
    env = {**os.environ, "PLAYWRIGHT_JSON_OUTPUT_NAME": str(out)}
    cmd = ["npx", "playwright", "test", "e2e/compliance", "--project=desktop-chromium", "--reporter=json"]
    print("$ (frontend) " + " ".join(cmd), file=sys.stderr)
    subprocess.run(cmd, cwd=FRONTEND, env=env, check=False, stdout=subprocess.DEVNULL)


def score_junit(path: Path, results: dict[str, Result]) -> int:
    owner = owner_fact_tests()
    n = 0
    for case in ET.parse(path).getroot().iter("testcase"):
        name = case.get("name", "").split("[")[0]
        m = PY_ID.match(name)
        if not m:
            continue
        item = f"{m.group(1)}.{m.group(2)}"
        if item not in ITEMS:
            continue
        n += 1
        label = f"api:{name}"
        if case.find("skipped") is not None:
            continue
        failed = case.find("failure") is not None or case.find("error") is not None
        r = results[item]
        if name in owner:
            (r.owner_failed if failed else r.owner_passed).append(label)
        else:
            (r.failed if failed else r.passed).append(label)
    return n


def _walk(suite: dict):
    for spec in suite.get("specs", []):
        yield spec
    for child in suite.get("suites", []):
        yield from _walk(child)


def score_playwright(path: Path, results: dict[str, Result]) -> int:
    data = json.loads(path.read_text(encoding="utf-8"))
    n = 0
    for top in data.get("suites", []):
        for spec in _walk(top):
            title = spec.get("title", "")
            ids = [i for i in PW_ID.findall(title) if i in ITEMS]
            if not ids:
                continue
            statuses = [t.get("status") for t in spec.get("tests", [])]
            if statuses and all(s == "skipped" for s in statuses):
                continue
            n += 1
            failed = not spec.get("ok", False)
            owner = "@owner-facts" in title or "owner-facts" in (spec.get("tags") or [])
            for item in ids:
                r = results[item]
                label = f"browser:{title}"
                if owner:
                    (r.owner_failed if failed else r.owner_passed).append(label)
                else:
                    (r.failed if failed else r.passed).append(label)
    return n


def status_of(item: str, r: Result) -> str:
    if item in NOT_APPLICABLE:
        return "N/A (by design)"
    if r.failed:
        return "Fail"
    if r.owner_failed:
        return "Blocked (owner)"
    if r.passed or r.owner_passed:
        return "Pass"
    return "No check"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--api-only", action="store_true", help="skip the browser suite")
    ap.add_argument("--junit", type=Path, help="score an existing pytest junit XML instead of running pytest")
    ap.add_argument("--playwright-json", type=Path, help="score an existing Playwright JSON report")
    ap.add_argument("--markdown", type=Path, help="also write the result as a Markdown table")
    args = ap.parse_args()

    results: dict[str, Result] = defaultdict(Result)
    tmp = Path(tempfile.mkdtemp(prefix="gk-score-"))

    junit = args.junit
    if junit is None:
        junit = tmp / "pytest.xml"
        run_pytest(junit)
    n_api = score_junit(junit, results) if junit.exists() else 0

    n_pw = 0
    pw = args.playwright_json
    if pw is None and not args.api_only:
        pw = tmp / "playwright.json"
        run_playwright(pw)
    if pw is not None and pw.exists():
        n_pw = score_playwright(pw, results)

    rows = []
    for item, text in ITEMS.items():
        r = results[item]
        st = status_of(item, r)
        checks = len(r.passed) + len(r.failed) + len(r.owner_passed) + len(r.owner_failed)
        rows.append((item, st, checks, text, r))

    met = sum(1 for _, st, *_ in rows if st in ("Pass", "N/A (by design)"))
    blocked = [i for i, st, *_ in rows if st == "Blocked (owner)"]
    failed = [i for i, st, *_ in rows if st == "Fail"]
    unchecked = [i for i, st, *_ in rows if st == "No check"]

    width = max(len(st) for _, st, *_ in rows)
    print()
    for item, st, checks, text, _ in rows:
        print(f"{item:>4}  {st:<{width}}  {checks:>2} checks  {text[:80]}")
    print()
    print(f"Checks run: {n_api} API/server, {n_pw} browser")
    print(f"Score: {met} / 36  (Pass + N/A by design)")
    print(f"Blocked by owner facts: {', '.join(blocked) or 'none'}  -> {met + len(blocked)} / 36 once DECISIONS_NEEDED.md is filled")
    if NOT_APPLICABLE:
        print("Not applicable by design: " + "; ".join(f"{k} ({v})" for k, v in NOT_APPLICABLE.items()))
    if failed:
        print(f"Failing: {', '.join(failed)}")
        for item, st, _, _, r in rows:
            if st == "Fail":
                for f in r.failed:
                    print(f"   {item}: {f}")
    if unchecked:
        print(f"No automated check: {', '.join(unchecked)}")

    if args.markdown:
        lines = [
            "| Item | Status | Checks | Requirement |",
            "|---|---|---|---|",
            *[f"| {i} | {st} | {c} | {t} |" for i, st, c, t, _ in rows],
            "",
            f"**Score: {met} / 36** (Pass + N/A by design). Blocked by owner facts: {', '.join(blocked) or 'none'}.",
        ]
        args.markdown.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"Wrote {args.markdown}")

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
