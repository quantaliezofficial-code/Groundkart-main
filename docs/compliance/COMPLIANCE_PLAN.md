# GroundKart compliance gap analysis and plan

> Engineering plan, 10 November 2026. Not legal advice. Legal basis for each item is in [RESEARCH.md](RESEARCH.md); data facts in [DATA_MAP.md](DATA_MAP.md); owner decisions in [DECISIONS_NEEDED.md](../../DECISIONS_NEEDED.md). All draft texts in [drafts/](drafts/) are **DRAFT FOR LAWYER REVIEW**.

## 1. How items are scored

Same method before and after: an item is ticked only if it can be found on the running site (frontend on `:3000`, API on `:8000`, dev database with demo seed). The score is reproduced by [`score.py`](score.py), which runs the `@compliance` browser and API checks and prints one line per item. Items whose only blocker is a business fact the owner has not supplied are shown as **Blocked (owner)**, not ticked. Not-applicable-by-design items are counted as met and listed separately, as the brief asks for check 7.

Status values: Pass, Partial, Fail, N/A (by design), Blocked (owner), Unknown. Risk: High / Medium / Low by penalty exposure and user harm. Effort: S (<½ day), M (1–2 days), L (>2 days).

## 2. Score before: **8 / 36**

| Check | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | Total |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Ticks before | 0/6 | 2/4 | 1/3 | 0/4 | 1/4 | 1/5 | 2/4 | 1/6 | **8/36** |

Band: "Under 18: start with checks 1, 2 and 8."

## 3. Gap analysis, item by item

Evidence paths are relative to the repository root. Screenshots of the "before" pages are in `docs/compliance/evidence/before/`.

| ID | Item | Before | Evidence (before) | Risk | Fix | Effort | Depends on |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1.1 | Privacy link in footer of every page and next to every form | Partial → **Fail** | Footer link on all public pages (`frontend/src/components/SiteFooter.tsx:20`); sign-up has a link (`AuthModal.tsx:495`); none next to Contact, support ticket, checkout, owner verification, listing builder forms | High | `<PrivacyNote/>` component placed under every form; footer already present | S | — |
| 1.2 | Lists each type of data | Partial → **Fail** | `PrivacyPolicy.tsx:34` mentions name, email, phone, "business registration and identity" only; no IP, cookies, documents, bank, booking notes, reviews | High | New notice with data table generated from DATA_MAP | M | Draft |
| 1.3 | Specific purpose for each | **Fail** | One generic paragraph (`PrivacyPolicy.tsx:41`); claims SMS confirmations that do not exist | High | Data table: purpose per item | S | Draft |
| 1.4 | Retention and recipients | **Fail** | "until deletion is requested"; no recipients named (`PrivacyPolicy.tsx:55`) | High | Retention and recipients columns; retention schedule draft | S | D-07 |
| 1.5 | Withdraw consent, rights, complain to the Board | **Fail** | Only "contact our team" (`PrivacyPolicy.tsx:62`) | High | Rights section + Board complaint route + My Data page | M | B.1 |
| 1.6 | Security practices and last-updated date | Partial → **Fail** | Date "October 2026" present; security limited to "httpOnly cookie" | Medium | Security section; version + date from one constant | S | — |
| 2.1 | No pre-ticked boxes | **Pass** | No public form checkbox is checked by default (grep of `type="checkbox"`; only owner/admin configuration toggles: `RentalSetupStep.tsx`, `BannersTab.tsx`, `AdminLayout.tsx`, which are settings, not consent) | — | Keep; add automated scan with an allow-list for settings toggles | S | — |
| 2.2 | Marketing consent separate | **Pass** | No marketing processing exists; sign-up line covers service terms only (owner decision D-11: no marketing) | — | State "no marketing" in notice; test asserts no marketing control is bundled | S | D-11 |
| 2.3 | Withdrawal as easy as giving | Partial → **Fail** | Only `DELETE /api/v1/users/me` (no UI path in profile found for withdrawal); no settings toggle | High | My Data page: withdraw consent (closes account, keeps legally required records) in two clicks; recorded | M | 2.4 |
| 2.4 | Consent records | **Fail** | No consent table (`backend/app/models/core.py`) | High | `consent_records` table: user, purpose, notice version, terms version, action, timestamp, hashed IP | M | — |
| 3.1 | Grievance Officer name, designation, email, phone | **Fail** | Only `support@` email (`SiteFooter.tsx`, `PrivacyPolicy.tsx`) | High | Business profile settings rendered in footer, Contact, Grievance page, notice | S | **D-02 (owner)** |
| 3.2 | Simple way to complain, ticket number | **Pass** (form saves) | Contact form posts to `POST /api/v1/contact` (`Contact.tsx:29`, `backend/app/main.py:3191`): hypothesis "sends nothing" **disproved**; but no ticket number shown and guests get a `guest_enquiries` row, not a ticket | Medium | Contact form always creates a ticket (guest tickets supported), returns and shows a ticket number `GK-T-XXXXXX`; `grievance` category | M | — |
| 3.3 | 90 days data / 48 h + 1 month shopping | **Fail** | No due dates on tickets | High | `ack_due_at`, `resolve_due_at` computed by category (content complaints 24 h/15 d, others 48 h/30 d, data requests 30 d within the 90-day ceiling); admin SLA badges, overdue filter | M | — |
| 4.1 | Banner with equal Accept/Reject/Choose, **or none needed** | **Fail** | No banner, but YouTube/Vimeo iframes load automatically on venue pages with videos (`DetailView.tsx:1955`) | Medium | Remove automatic third-party loads (click-to-load video via `youtube-nocookie.com`); then no banner is needed because nothing non-essential is set or loaded; test proves zero third-party requests on first load | S | — |
| 4.2 | Non-essential trackers only after agreement | **Fail** | Same iframes | Medium | Same | S | — |
| 4.3 | Policy names the tools | **Fail** | Not named | Low | Cookie and third-party notice page lists the cookie, browser storage keys, YouTube/Vimeo, Google Maps link, WhatsApp link | S | Draft |
| 4.4 | Cookie settings link in footer | **Fail** | None | Low | "Cookie settings" footer link opening a panel that shows the strictly necessary cookie and the "load external videos" preference (off by default) | S | — |
| 5.1 | Services, pricing and payment, cancellations, liability | Partial → **Fail** | `TermsOfService.tsx` has booking hold and cancellation tiers; no pricing/payment section or liability limits | High | New Terms | M | Draft |
| 5.2 | Governing law, jurisdiction, dispute handling | **Fail** | Absent | Medium | Governing law: laws of India; disputes: grievance → consumer commission route; courts at `[[OWNER TO FILL: jurisdiction city]]` | S | **D-03 (owner)** |
| 5.3 | User content rules and complaints | **Fail** | Absent | Medium | Content rules for listings and reviews; report-content route; intermediary grievance timeline | S | — |
| 5.4 | Agreement at sign-up or checkout | **Pass** | "By creating an account, you agree to our Terms of Service and Privacy Policy" (`AuthModal.tsx:495`); no record kept; nothing at guest checkout | — | Keep, add the same line at checkout and record acceptance with versions | S | 2.4 |
| 6.1 | Return/refund/exchange/delivery/warranty policies | Partial → **Fail** | Tiers in Terms and checkout (hard-coded 48/24/50, `ReviewPay.tsx:447`), no standalone policy | High | Refund and Cancellation page driven by `system_configuration` tiers; state that shipping, exchange and warranty do not apply to venue hire | S | — |
| 6.2 | Legal name, registered address, customer care, grievance | **Fail** | Email only | High | Footer legal block from business profile | S | **D-01, D-02, D-04 (owner)** |
| 6.3 | Total with break-up and payment modes before paying | Partial → **Fail** | Total shown; single rate line; no payment modes (`ReviewPay.tsx:505`) | High | Break-up: venue charge, platform fee ₹0, taxes line, total; accepted payment modes; refund policy link at checkout | S | D-15, D-16 |
| 6.4 | Product details where applicable | **Pass** | Venue page shows address, capacity, inclusions, rules, photos; country of origin does not apply to a service (RESEARCH R16) | — | Add the venue owner's business name to the venue page and confirmation (E-Commerce r.5 seller details) | S | — |
| 6.5 | No dark patterns (fake countdowns, hidden charges, sneaked items, fake reviews) | **Fail** | Reviews accepted from any signed-in user without a booking (`backend/app/main.py:2365`); seeded sample reviews indistinguishable from real ones | High | Reviews only from completed bookings, one per booking, "Verified booking" badge; DEMO DATA flag; dark-pattern Playwright scan | M | D-20 |
| 7.1 | Age question where children could use the service | **Fail** | No age check | High | Unticked "I confirm I am 18 years or older" at sign-up and guest checkout; refused without it; stored with time and Terms version; no DOB | S | D-12 (decided) |
| 7.2 | Verifiable parental consent | **Fail** (children not excluded) | — | High | **N/A by design**: adults only (owner decision). No parental flow. Q-13 to lawyer | — | Q-13 |
| 7.3 | No tracking or targeted ads at children | **Pass** | No analytics/ads code (DATA_MAP §3) | — | Keep; test | S | — |
| 7.4 | Nothing harmful to a child's well-being | **Pass** | No profiling or child-directed features | — | Keep; notice sentence asking users not to enter children's details; admin minor-account action | S | — |
| 8.1 | Whole site on HTTPS | **Pass** (config) | `deploy/nginx-host.conf` 80→443 redirect and HSTS; app sends HSTS (`backend/app/main.py:305`). Not verifiable on a live domain from here | High | Add HSTS and CSP to the web container nginx too; deploy check script | S | — |
| 8.2 | Access control, strong passwords, 2-step login | Partial → **Fail** | Role checks and password strength exist; **no second factor** for admins | High | TOTP for admin and super admin (mandatory in production), recovery codes, audit | M | D-19 |
| 8.3 | Encrypted/masked, backups, access logs ≥1 year | **Fail** | ID numbers, PAN, GSTIN, bank account numbers in plain text and returned unmasked; backups 14 days on same host; no log retention | High | AES-GCM field encryption with key from env (+ migration with backup and rollback), masking in API/UI; audit log retention ≥365 days; Docker log rotation documented; manage-token redaction in logs | L | D-10, D-18 |
| 8.4 | Vendor contracts require security | **Fail** | None documented | Medium | Vendor register and contract checklist (draft) | S | **D-09 (owner signs)** |
| 8.5 | Written breach plan; users without delay; Board 72 h | **Fail** | None | High | Breach plan draft; `breach_incidents` register with computed deadlines; admin screen; user notice template | M | D-17 |
| 8.6 | CERT-In within 6 hours | **Fail** | None | High | Same register: `cert_in_due_at = detected_at + 6h`; plan names the CERT-In contact and form | S | D-17 |
| B.1 | Rights: summary, correction, erasure, nominee; publish how | **Fail** | Self-delete only; no export, nominee or request tracking | High | My Data page; `data_requests` table with ticket numbers and due dates; JSON export; nominee; correction via profile | L | — |
| B.2 | Delete when done; processors too | **Fail** | Soft delete keeps all personal data (`backend/app/main.py:2698`) | High | Erasure service: anonymise users, guest booking contact, tickets, reviews, notifications, enquiries, verification docs and files; keep financial rows with recorded legal reason | L | D-07, Q-12 |
| B.3 | Consent records and logs ≥1 year | **Fail** | No consent records; no log retention | Medium | `consent_records`; retention config ≥365 days for audit/security logs | S | — |
| B.4 | Large-platform 3-year inactivity erasure | N/A by law (below 2 crore users) | RESEARCH R7 | Low | Adopt voluntarily as D-08 with 48 h warning job (in-app notice; email when a provider exists) | M | D-08 |

### 3.1 Starting hypotheses: proved or disproved

| Hypothesis | Result | Evidence |
| --- | --- | --- |
| Privacy and Terms pages exist with cookie, retention and grievance sections | **Proved**, but content is thin: no named officer, phone, data table, recipients, rights, Board route, security detail or language option | `frontend/src/components/PrivacyPolicy.tsx`, `TermsOfService.tsx` |
| No cookie banner and no analytics; third-party fonts and images | **Partly disproved**: no analytics (true), fonts self-hosted, no Google/Unsplash images anywhere. The remaining third-party loads are owner-added YouTube/Vimeo iframes | DATA_MAP §3 |
| Terms lack governing law, user content rules and grievance process | **Proved** | `TermsOfService.tsx` |
| No consent checkbox at sign-up and no consent record table | **Partly**: a "By creating an account, you agree" line exists; no record table | `AuthModal.tsx:495`, models |
| Contact form sends nothing | **Disproved**: it posts to `/api/v1/contact`; signed-in users get a ticket, guests a `guest_enquiries` row; no number is shown | `Contact.tsx:29`, `backend/app/main.py:3191` |
| No age or 18+ check | **Proved** | grep |
| Owner ID numbers in plain text; documents through the public upload path | **Half**: plain text proved (also PAN, GSTIN, bank account number); documents are already on a **private** store with an admin-only, audited route | `backend/app/main.py:1139`, `:1258` |
| Reviews without a completed booking | **Proved** (`booking_id` optional; checked only if supplied) | `backend/app/main.py:2365` |
| Delete-my-account scope | Sets `deleted_at`, archives venues, revokes sessions; **erases nothing**; no export, correction, nominee, retention job or breach plan | `backend/app/main.py:2698` |
| No admin 2FA; default admin password in dev script | **Proved**: password only; `seed_dataset.py --admin-password` defaults to `Admin@2026!` (dev-only, refuses production) | `backend/scripts/seed_dataset.py:1361` |
| HTTPS/HSTS/CSP depend on the proxy | **Partly**: the API sets HSTS, CSP (API responses), frame and nosniff headers itself; the web nginx sets frame/nosniff/referrer but **no CSP or HSTS**; HSTS only at host nginx | `backend/app/main.py:301`, `frontend/nginx.conf:25` |
| *(new)* Guest manage tokens appear in URLs and therefore in access logs | **Found** | `/api/v1/bookings/manage/{token}` |
| *(new)* Rate-limit keys store phone numbers, emails and IPs in clear text forever | **Found** | `backend/app/main.py:572` |

## 4. Backlog

### P0: before any public launch

| # | Change | Files / tables / endpoints / UI | Tests | Decision |
| --- | --- | --- | --- | --- |
| P0-1 | Business profile (legal name, address, grievance officer, care phone, jurisdiction, payment modes) editable by super admin, public read endpoint, rendered with `[[OWNER TO FILL: …]]` fallbacks | `system_configuration.legal_profile` JSONB; `GET /api/v1/legal/profile`; `PUT /api/v1/admin/legal/profile`; `SiteFooter`, Contact, policy pages | `test_compliance_grievance.py`, `grievance.spec.ts` | D-01–D-04, D-16 |
| P0-2 | Privacy Notice EN + HI, Terms, Refund & Cancellation, Cookie & third-party, Grievance, Your Data Rights pages; language switch; version constants | `frontend/src/content/legal/*.md`, `LegalPage.tsx`, routes `/privacy`, `/terms`, `/refunds`, `/cookies`, `/grievance`, `/your-data` | `privacy.spec.ts`, `terms.spec.ts` | D-06 |
| P0-3 | Privacy note next to every form | `PrivacyNote.tsx` in AuthModal, Contact, SupportTickets, ReviewPay, owner verification (IdentityStep), ListingBuilder | `privacy.spec.ts` | — |
| P0-4 | Consent records + agreement line + 18+ declaration at sign-up and guest checkout | `consent_records` table (migration `j1_compliance_core`); `signup`, `create_booking` accept `age_confirmed`, `terms_version`, `notice_version`; `GET/POST /api/v1/me/consents` | `test_compliance_consent.py`, `test_compliance_adults_only.py`, `consent.spec.ts`, `adults.spec.ts` | D-12 |
| P0-5 | Contact form → ticket with number, `grievance` and `data_request` categories, `ack_due_at`/`resolve_due_at`, admin SLA indicators; guest tickets | `support_tickets` new columns `ticket_number`, `ack_due_at`, `resolve_due_at`, `acknowledged_at`, guest contact columns, nullable `creator_id`; `POST /api/v1/contact` | `test_compliance_grievance.py` | — |
| P0-6 | Verified reviews only, one per booking, badge; demo-data flag and banner; refuse production start with demo rows | `reviews.verified`; `users.is_demo`, `venues.is_demo`, `reviews.is_demo`; `DEMO_MODE` check | `test_compliance_selling.py`, `dark-patterns.spec.ts` | D-20 |
| P0-7 | Checkout break-up, payment modes, refund link, owner business name on venue page and confirmation; tiers from config | `ReviewPay.tsx`, `DetailView.tsx`, `GET /api/v1/legal/booking-terms` (public tiers) | `selling.spec.ts` | D-15, D-16 |
| P0-8 | No automatic third-party loads; click-to-load video; cookie settings panel | `DetailView.tsx` `VideoEmbed`, `CookieSettings.tsx`, footer link | `cookies.spec.ts` | Q-21 |
| P0-9 | Encrypt and mask ID numbers, PAN, GSTIN, bank account numbers; backup before migration | `app/modules/core/crypto.py` (AES-256-GCM, `FIELD_ENCRYPTION_KEY`), migration `j2_encrypt_identity_fields` with downgrade, `scripts/backup_before_migration.sh`, masked schemas | `test_compliance_security.py` | D-10 |
| P0-10 | Admin TOTP 2FA, required in production, recovery codes | `users.totp_secret_enc`, `totp_enabled_at`, `totp_recovery_hashes`; `/api/v1/auth/2fa/*`; login `otp` field; admin settings UI | `test_compliance_security.py` | D-19 |
| P0-11 | Breach register with 6 h / 72 h deadlines; admin screen; plan | `breach_incidents`; `/api/v1/admin/compliance/incidents` | `test_compliance_breach.py` | D-17 |
| P0-12 | Security headers in web nginx (HSTS, CSP, frame-ancestors); redact manage tokens in logs | `frontend/nginx.conf`, `app/modules/core/logging.py` filter | `test_compliance_security.py`, `security.spec.ts` | — |

### P1: before 13 May 2027 (build now; the date may move earlier)

| # | Change | Files / tables / endpoints / UI | Tests | Decision |
| --- | --- | --- | --- | --- |
| P1-1 | My Data page: JSON export, correction, nominee, withdraw consent, deletion request with due date | `data_requests` table, `nominees` table; `/api/v1/me/data/*`; `MyData.tsx` | `test_compliance_rights.py`, `rights.spec.ts` | — |
| P1-2 | Erasure service with legal carve-out; completion confirmation | `app/modules/privacy/erasure.py` | `test_compliance_rights.py` | D-07, Q-12 |
| P1-3 | Retention jobs: rate-limit rows, idempotency keys, expired tokens, reset requests, help search log, old guest booking contacts, resolved tickets, guest enquiries, notifications, inactive accounts with 48 h warning | `app/modules/privacy/retention.py`, `RETENTION_SCHEDULE` table in code, lifespan loop | `test_compliance_retention.py` | D-07, D-08 |
| P1-4 | Admin Compliance dashboard: open grievances and data requests with due dates, consent stats, incidents, overdue | `/api/v1/admin/compliance/summary`; `ComplianceTab.tsx` | `test_compliance_dashboard` cases | — |
| P1-5 | Admin minor-account action: suspend + erase | `POST /api/v1/admin/users/{id}/minor-account` | `test_compliance_adults_only.py` | — |
| P1-6 | Hash rate-limit identifiers | `check_rate_limit` keys hashed with HMAC | `test_compliance_retention.py` | — |
| P1-7 | Legacy users: re-acceptance banner for new notice version (s.5(2)) | `NoticeUpdateBanner.tsx` when stored version < current | `consent.spec.ts` | Q-3 |

### P2: good practice

| # | Change |
| --- | --- |
| P2-1 | Off-site encrypted backups and a restore drill (deploy guide) — D-18 |
| P2-2 | More Eighth Schedule languages on request — D-06 |
| P2-3 | Annual dark-pattern self-audit record (becomes mandatory from 1 Jan 2027 per the E-Commerce amendment; run `score.py` + dark-pattern spec and file the output) |
| P2-4 | Email provider for breach notices and 48 h warnings (add to vendor register first) |
| P2-5 | DPIA-style review if GroundKart grows large |

## 5. Drafts (all DRAFT FOR LAWYER REVIEW)

| Draft | File | Shipped as page |
| --- | --- | --- |
| Privacy Notice (English) | [drafts/privacy-notice.en.md](drafts/privacy-notice.en.md) | `/privacy` |
| Privacy Notice (Hindi) | [drafts/privacy-notice.hi.md](drafts/privacy-notice.hi.md) | `/privacy?lang=hi` |
| Terms of Service | [drafts/terms.en.md](drafts/terms.en.md) | `/terms` |
| Refund and Cancellation Policy | [drafts/refunds.en.md](drafts/refunds.en.md) | `/refunds` |
| Cookie and Third-party Notice | [drafts/cookies.en.md](drafts/cookies.en.md) | `/cookies` |
| Grievance Redressal | [drafts/grievance.en.md](drafts/grievance.en.md) | `/grievance` |
| Your Data Rights procedure | [drafts/data-rights.en.md](drafts/data-rights.en.md) | `/your-data` |
| Breach response plan | [drafts/breach-response-plan.md](drafts/breach-response-plan.md) | internal |
| Vendor and processor register | [drafts/vendor-register.md](drafts/vendor-register.md) | internal |
| Data retention schedule | [drafts/retention-schedule.md](drafts/retention-schedule.md) | summarised in the notice |

The page drafts are byte-identical copies of `frontend/src/content/legal/*.md`; `test_compliance_drafts.py` fails if they drift.
