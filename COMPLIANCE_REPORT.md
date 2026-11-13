# GroundKart compliance report

> **Engineering report, not legal advice.** It records what was built and tested against the 36-item website compliance checklist (Rinisha), using Indian law as researched on 10 November 2026 (`docs/compliance/RESEARCH.md`). Every policy text is a **draft for lawyer review**. Business facts that only the owner can supply are shown on the site as `[[OWNER TO FILL: …]]` placeholders and listed in `DECISIONS_NEEDED.md`.

Branch: `compliance/dpdp` · Report date: 11 November 2026

## 1. Result

| | Before | After (today) | After the owner fills four facts |
| --- | --- | --- | --- |
| Score (Pass + N/A by design) | **8 / 36** | **32 / 36** | **36 / 36** |
| Band | "Under 18: start with checks 1, 2 and 8" | "30–36: great shape" | "30–36: great shape" |

The four items not counted today are **Blocked (owner)**: the code, page sections and tests are in place, and each needs a business fact or a signed document that only the owner has.

| Item | What is missing | How to fix | Decision |
| --- | --- | --- | --- |
| 3.1 Grievance Officer on the website | Name, designation, email, phone | Super admin: **Admin → Rules and fees → Legal and business details** | D-02 |
| 5.2 Governing law and jurisdiction | Court city | Same form | D-03 |
| 6.2 Legal business details | Legal name, CIN, registered office, customer care | Same form | D-01, D-04 |
| 8.4 Vendor contracts that require security | Signed data-processing terms with the hosting provider (Hostinger) and any other processor | Sign, then record in `docs/compliance/drafts/vendor-register.md` | D-05, D-09 |

**Not applicable by design (counted as met, listed separately):** 7.2 verifiable parental consent. GroundKart is adults-only (owner decision D-12): sign-up and guest checkout require an unticked "I confirm I am 18 years or older" box, no date of birth is collected, and the server refuses without it. Whether this is enough is lawyer question Q-13.

The brief's target of at least 33/36 is reached only when the first three facts above are entered (about five minutes in the admin form). I have not filled them with guesses.

## 2. Item by item

Before = `docs/compliance/COMPLIANCE_PLAN.md` §3 (screenshots in `docs/compliance/evidence/before/`). After = `python3 docs/compliance/score.py` on 11 Nov 2026 (83 API/server checks and 49 browser checks; screenshots in `docs/compliance/evidence/after/`).

| Item | Requirement (short) | Before | After | Main evidence |
| --- | --- | --- | --- | --- |
| 1.1 | Privacy link in footer and next to every form | Fail | Pass | `PrivacyNote` under every form; `e2e/compliance/privacy.spec.ts` |
| 1.2 | Lists each type of data | Fail | Pass | Notice data table from `DATA_MAP.md` |
| 1.3 | Purpose for each | Fail | Pass | Same table, purpose column |
| 1.4 | Retention and recipients | Fail | Pass | Retention and recipients columns; `drafts/retention-schedule.md` |
| 1.5 | Withdraw, rights, complain to the Board | Fail | Pass | Rights section; **My data** page `/account/data` |
| 1.6 | Security practices, last-updated date | Fail | Pass | Security section; version 1.0, 10 Nov 2026 |
| 2.1 | No pre-ticked boxes | Pass | Pass | `dark-patterns.spec.ts` checks every form |
| 2.2 | Marketing separate from service consent | Pass | Pass | No marketing purpose at all (D-11) |
| 2.3 | Withdraw as easily as given | Fail | Pass | One-step withdrawal on My data; `test_2_3_*` |
| 2.4 | Record of who consented, to what, when | Fail | Pass | Append-only `consent_records` with versions and hashed IP; re-acceptance banner for older accounts |
| 3.1 | Grievance Officer named on the site | Fail | **Blocked (owner)** | Footer, Contact and Grievance page read the legal profile |
| 3.2 | Simple complaint route with ticket number | Pass | Pass | Contact form always opens a `GK-T-YYMM-NNNN` ticket |
| 3.3 | 90-day DPDP / 48 h + 1 month e-commerce clocks | Fail | Pass | SLA due dates per ticket; admin **Privacy and compliance** tab |
| 4.1 | Cookie banner, or none needed | Fail | Pass | Nothing non-essential loads: videos are click-to-load (`youtube-nocookie`); test proves no third-party requests on first load |
| 4.2 | Trackers only after agreement | Fail | Pass | No analytics or ads; same test |
| 4.3 | Policy names the tools | Fail | Pass | Cookie and third-party notice `/cookies` |
| 4.4 | Change the choice later | Fail | Pass | Footer "Cookie settings" panel |
| 5.1 | Terms cover services, price, cancellation, liability | Fail | Pass | `/terms` draft (the old page had no pricing, payment or liability sections) |
| 5.2 | Governing law and jurisdiction | Fail | **Blocked (owner)** | Terms clause reads the court city from the legal profile |
| 5.3 | Rules for user content and complaints | Fail | Pass | Reviews only from completed bookings; content-report clock 24 h / 15 days |
| 5.4 | Agreement at sign-up or checkout | Pass | Pass | Agreement line plus versions stored |
| 6.1 | Refund, cancellation and delivery policies | Fail | Pass | `/refunds`, tiers read from live config |
| 6.2 | Legal name, address, care, grievance details | Fail | **Blocked (owner)** | Footer legal block |
| 6.3 | Price break-up and payment modes before paying | Fail | Pass | Checkout `price-breakup`, platform fee ₹0 |
| 6.4 | Mandatory product details | Pass | Pass | Venue page plus seller line |
| 6.5 | No dark patterns or fake reviews | Fail | Pass | No timers or pre-selected add-ons; verified-booking reviews only; DEMO DATA marker; production refuses demo rows |
| 7.1 | Age question | Fail | Pass | 18+ declaration at sign-up, guest checkout and the notice banner |
| 7.2 | Parental consent | Fail | N/A by design | Adults-only (D-12, Q-13) |
| 7.3 | No tracking aimed at children | Pass | Pass | No tracking code |
| 7.4 | Nothing harmful to children | Pass | Pass | Admin "minor account" action erases data |
| 8.1 | HTTPS everywhere | Pass | Pass | HSTS, TLS 1.2/1.3, CSP (`nginx-security-headers.conf`) |
| 8.2 | Access control, strong passwords, 2-step login | Fail | Pass | Admin TOTP two-step sign-in (required in production), role checks |
| 8.3 | Encryption or masking, backups, 1-year logs | Fail | Pass | AES-256-GCM for ID, PAN, GSTIN, bank numbers and 2FA secrets; masked by default, audited reveal; backups before every deploy; log redaction and rotation |
| 8.4 | Vendor contracts require security | Fail | **Blocked (owner)** | `drafts/vendor-register.md` |
| 8.5 | Written breach plan, Board within 72 h | Fail | Pass | `drafts/breach-response-plan.md`; incident register with deadlines |
| 8.6 | CERT-In within 6 hours | Fail | Pass | Incident register shows the 6-hour clock and "mark reported" |

## 3. What was built

**Notices and pages.** Privacy Notice (English and Hindi), Terms of Use, Refund and Cancellation Policy, Cookie and third-party notice, Grievance Redressal, Your Data Rights. All carry a "DRAFT FOR LAWYER REVIEW" banner, a version and a date, and fill business facts from the legal profile. Drafts are mirrored in `docs/compliance/drafts/` (`sync_drafts.py --check` keeps them identical).

**Consent.** Unticked 18+ box and agreement line at sign-up and guest checkout; append-only consent records with notice and terms versions and a keyed hash of the IP; one-step withdrawal; a bottom banner asking existing accounts to accept the current notice (DPDP s.5(2)).

**Rights.** My data page: download everything as JSON, correct details, name a nominee, see consents, withdraw, delete the account, and track requests (`GK-D-…`). Erasure anonymises personal data and keeps only records a law requires, with the reason.

**Grievance.** Every contact message becomes a numbered ticket with acknowledgement and resolution due dates; admins see SLA badges; the Grievance Officer has one overview screen.

**Security.** Field encryption with a production-only key; masked numbers with audit-logged reveal; admin two-step sign-in with a locally drawn QR code and recovery codes; rate-limit keys hashed; secrets redacted from app and nginx logs; CSP, HSTS and frame protection; Aadhaar limited to the last four digits; production refuses to start with demo data or known development passwords; npm dependencies updated where non-breaking.

**Breach and retention.** Incident register with CERT-In (6 h) and Board (72 h) clocks; daily retention job (one runner at a time) that anonymises old bookings, deletes verification documents after their period and warns inactive accounts.

**Homepage trust.** Full-bleed photo hero with self-hosted Unsplash photos, six occasion cards, "What protects your booking" (numbers read from the live booking rules), a step-through booking preview, verified-booking reviews only (hidden when there are none), and the founder story with only the facts supplied (D-13: founder to approve the wording).

**Deployment (Hostinger, Exotique procedure).** GitHub Actions over SSH with `VPS_*` secrets; on the VPS: rollback branch at the running commit, verified database backup before migrations, rebuild of `api` and `web` only, health checks, automatic code rollback, never `down -v`. Ports bound to 127.0.0.1 (web 3002, api 5001) beside Exotique. Runbook: `docs/09-operations-and-deployment/DEPLOYMENT.md`. A dry run of the server script (`deploy/hostinger/simulate_deploy.py`) runs in CI.

## 3a. Security review: nothing private by URL (second pass, 11 Nov 2026)

Requested by the owner: `.env`, source maps, the `.git` folder, the database, the login cookie and admin areas must never be reachable through a URL, and pop-ups must not keep coming back once closed.

| Concern | What protects it | Proof |
| --- | --- | --- |
| `.env`, `.git`, other hidden files | Web and host nginx return 404 for any hidden path (only `/.well-known/` allowed); `.dockerignore` keeps `.env`, `.git` and dumps out of images; `.env` is git-ignored | `check_exposure.sh` against the real nginx config with planted `.env`, `.git/config`, `.map` and `.sql` files: all 404; `test_compliance_exposure.py` |
| Source maps | Production build has none (`sourcemap: false`); `*.map` returns 404 anyway; shipped JS has no `sourceMappingURL` | same script and test |
| Database | Postgres publishes no port; API and web listen on 127.0.0.1 only; `.sql`, `.dump`, `.sqlite`, `/backups` return 404; backups live outside the web root | `test_8_3_database_and_api_ports_are_not_published_publicly` |
| Login cookie | Refresh token only in an `HttpOnly` cookie, `Secure` in production, `SameSite=Lax`, path `/api/v1/auth`; no token in browser storage | backend test and browser test [8.2] |
| Admin | All admin data needs an admin token (401/403 otherwise) and, in production, two-step sign-in; admin pages are `noindex` and `no-store`; API docs and schema are off in production | exposure script, `test_8_2_*` |
| Database studio | Passwords, tokens, 2FA material, ID and bank numbers and IP data shown as `[hidden]` in the table browser, CSV export (formula-safe) and query results; every view, export and query audit-logged; SQL console off in production | `test_8_3_database_studio_hides_credentials_and_logs_every_look`, `test_8_2_sql_console_is_off_in_production` |
| Open redirects | Banner links reject `//host` and the backslash form `/\host` in the API and the UI | `test_8_3_banner_links_cannot_leave_the_site_by_backslash_tricks`, `safeUrl.test.ts` |
| Deploys | `check_exposure.sh` runs after every deploy; a failure rolls the code back | `deploy.yml` |

**Dependencies and static analysis.** PyJWT 2.7.0 had published advisories and is now 2.15.1; `pip-audit` reports no known vulnerabilities. Shipped JavaScript dependencies: `npm audit --omit=dev` finds none. The remaining npm advisories are in the test runner (`vitest`), which is never shipped; its upgrade fails with an npm installer error and is listed below. React Router stays on 6.30.6 because version 7 broke the checkout navigation; the advisory's backslash redirect is blocked in our own link checks instead. A Semgrep scan with the open rule set (Python/FastAPI, SQLAlchemy, JWT, React, browser, Dockerfile, GitHub Actions, nginx, secrets) found no injectable SQL or secrets. Real findings were fixed: the deploy action that receives the SSH key is now pinned to a commit, sequence names are whitelisted, and email length is capped before the pattern check. CI now runs `pip-audit` and `npm audit` as blocking checks and Semgrep as a report.

**Pop-ups.** Nothing opens by itself on a first visit (browser test). The notice banner has "Not now" and a close button, and stays closed on that browser until the notice version changes; checkout still asks for the 18+ box. A closed announcement strip stays closed on later visits until the admin publishes a different one. The same toast message no longer stacks when an action is repeated.

## 4. Tests

| Suite | Result on 11 Nov 2026 |
| --- | --- |
| Backend (`pytest -m "not owner_facts"`) | 572 passed (the one owner-facts test, 8.4, is excluded and fails as expected until vendor terms are signed) |
| Frontend unit (`vitest`) | 32 files, 199 tests passed |
| Browser compliance (`playwright e2e/compliance`) | 49 checks; only the three `@owner-facts` checks fail (3.1, 5.2, 6.2), as expected |
| Browser regression (S0 smoke, S1 browsing, S2 auth, S3 booking, S4 owner, S5 admin, S6 support, S12 security) | All pass. When every suite runs at once, the demo accounts hit the login rate limit (429) and a few owner tests fail on sign-in; they pass when re-run. One S5 test ("admin user management") showed the same ordering flake earlier |
| Type check, API contract test and production build | Clean |
| Deploy dry run (`simulate_deploy.py`) | 12 of 12 checks passed |
| Migrations on an empty database | `alembic upgrade head`, downgrade to the pre-compliance revision and upgrade again: clean |
| Exposure probe (`check_exposure.sh`) against the production nginx config | All checks passed |

No existing test was weakened. Stale selectors in two older browser tests were updated to the current markup (venue cards are now `<article>` elements).

## 5. Still to do

**Owner (see `DECISIONS_NEEDED.md`):** fill the legal profile (D-01 to D-04, D-22); name the hosting provider and region and sign its data processing terms (D-05, D-09); confirm the checkout tax statement and payment modes (D-15, D-16); approve the founder text (D-13); confirm the domain and DNS (D-24); choose the database layout on the VPS (D-23, default bundled); set up off-server backups (D-25); Hindi translation sign-off (D-21).

**Lawyer:** the 22 questions in `docs/compliance/RESEARCH.md` §10. The most important: Q-1 commencement dates, Q-3 legacy notice, Q-4 consent versus legitimate use for booking data, Q-11 payments, Q-13 adults-only design, Q-16 Aadhaar, Q-22 cancellation charges.

**Engineering follow-ups (not blocking the score):**

- React Router 7: tried; it broke checkout navigation (the slot was lost on the way to `/checkout`). Stay on 6.30.6 with the backslash check, and plan the upgrade with the navigation code reworked.
- `vitest` 3 → 4 (test runner only, never shipped): the npm installer fails on this lock file; retry with a newer npm.
- There is no email or SMS provider yet. Breach notices to affected people and inactivity warnings are shown in the app; sending them by email needs a provider (and an update to the vendor register).
- P2 items in the plan, including the annual dark-pattern self-audit record that the E-Commerce amendment requires from 1 January 2027 (run `score.py` and the dark-pattern spec, and file the output).

## 6. Dates

| Date | What happens | Status |
| --- | --- | --- |
| In force now | SPDI Rules 2011, E-Commerce Rules 2020, Dark Patterns Guidelines 2023, CERT-In Directions 2022 | Covered above |
| 13 Nov 2026 (or 14 Nov, Q-1) | DPDP Rule 4: Consent Managers can register | Nothing to build; GroundKart is not a Consent Manager |
| 1 Jan 2027 | E-Commerce (Amendment) Rules 2026 | Annual dark-pattern self-audit record; review seller disclosures (Q-9) |
| 13 May 2027 (or 14 May, Q-1) | DPDP core duties and penalties | Built now; MeitY consulted on shortening the window, so do not wait |

## 7. How to re-run

```bash
# Dev stack: Postgres, API on :8000 (backend), frontend on :3000
cd backend && pytest -q -m compliance                    # API and server checks
cd frontend && npx playwright test e2e/compliance --project=desktop-chromium
python3 docs/compliance/score.py                         # both suites, one line per item
python3 docs/compliance/score.py --api-only              # what CI prints
python3 docs/compliance/sync_drafts.py --check           # drafts match the live pages
python3 deploy/hostinger/simulate_deploy.py              # deploy and rollback dry run
sh deploy/hostinger/check_exposure.sh https://groundkart.com   # nothing private by URL (live site)
pip-audit -r backend/requirements.lock.txt && (cd frontend && npm audit --omit=dev)   # known vulnerable dependencies
```
