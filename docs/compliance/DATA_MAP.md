# GroundKart personal data map

> Engineering inventory, 10 November 2026, from the code on branch `compliance/dpdp` (`backend/app/models/core.py`, schemas, services, `backend/scripts/`, `frontend/src/`, `docker-compose.yml`, `deploy/`). Lawful grounds and retention periods are **proposals for a lawyer and the owner to confirm**. Recommended periods marked with D-xx are owner decisions in [DECISIONS_NEEDED.md](../../DECISIONS_NEEDED.md).

Legend. **Ground**: C = consent (DPDP s.6); LU-a = legitimate use, voluntarily provided for a specified purpose (s.7(a)); LU-law = compliance with a law or court order (s.7(c)–(e)); LU-emp = employment (s.7(i)). **Roles**: SA super admin, A admin, O venue owner, B broker (referral partner), C customer, G guest, P public.

## 1. Database tables

| # | Data item | Where stored | Who can see | Purpose | Ground | Retention today → recommended | Recipients | Protection today | Gaps |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Name, phone, email | `users.name`, `users.phone` (unique), `users.email` (citext) | Self; A/SA; O sees a customer's name/phone/email only for that customer's bookings at their venue | Account, sign-in, booking contact | C (sign-up) | Forever; soft delete keeps everything → anonymise on erasure; inactive accounts 3 years with 48 h warning (D-08) | Hosting provider; venue owner (per booking) | DB access via app roles; TLS in transit | Self-deletion only sets `deleted_at`; name/phone/email stay. No consent record. |
| 2 | Password hash | `users.password_hash` | Nobody (hash only) | Authentication | C (SPDI r.5 today) | Life of account → delete on erasure | Hosting | Argon2 hash (`app/modules/auth/security.py`) | None. |
| 3 | Role, super-admin flag, `created_by`, verified flag | `users.role`, `is_super_admin`, `created_by`, `is_verified` | Self; A/SA | Access control | LU-a / contract | Life of account | — | Partial unique index for one super admin | None. |
| 4 | Suspension flags and reason | `users.suspended_at`, `suspension_reason` | A/SA; self sees generic login error | Abuse handling, minors | LU-law / legitimate interest of the platform (Q-4) | Life of account → 1 year after closure (D-07) | — | Audit row on change | Reason text could contain personal data; no structured "minor" reason. |
| 5 | Password-change flags | `users.must_change_password`, `password_changed_at` | A/SA | Security | LU | Life of account | — | — | None. |
| 6 | Refresh tokens | `refresh_tokens` (hash, expiry, revocation, rotation chain) | Nobody | Session continuity | C (sign-in) | Never deleted → purge 30 days after expiry/revocation | — | SHA-256 hash only; httpOnly, SameSite=Lax cookie; Secure in production | No purge job. |
| 7 | Password reset requests | `password_reset_requests` (token hash, status, requester, reason) | A/SA | Account recovery | LU-a | Forever → 90 days | — | Token hashed; audit trail | No purge job. |
| 8 | Owner verification: business name, ID type, **ID number**, PAN, GSTIN, document | `owner_verifications.*`; document in private store `PRIVATE_UPLOADS_DIR/owner-verifications/{user_id}/…` or private S3 | Self (status only); A/SA (all fields, document) | KYC of venue owners, fraud prevention, E-Commerce seller identification | C + LU-law (E-Commerce r.5/r.6, Q-8, Q-16) | Forever → life of listing + 3 years (D-07), document 1 year after decision (D-07) | Hosting / S3 | Private storage, admin-only route, 5-minute presigned URL, every view logged `owner_verification.document_viewed` | **ID number, PAN and GSTIN stored and returned in plain text** (`backend/app/schemas/admin.py:93`); no masking; Aadhaar risk (Q-16). |
| 9 | Owner bank account: holder name, **account number**, IFSC, bank, UPI | `owner_bank_accounts` | Self; A/SA | Payouts | C (SPDI financial information) | Forever → life of account + tax period (D-07, Q-12) | Bank (manual transfer) | Access control | **Account number in plain text**; returned unmasked. |
| 10 | Broker profile: company, city, payout method and details, notes | `broker_profiles` | Self; A/SA | Commission payouts | Contract | Life of partnership + tax period | Bank | Access control | `payout_details` free text (may hold account numbers) unencrypted. |
| 11 | Venue listing: address, city, pincode, lat/long, description, photos, videos, rules | `venues`, `venue_media`, `venue_content_blocks`, `venue_purposes`, uploads store | P (public listing) | Marketplace listing | C / contract | Life of listing; archived kept → anonymise owner link on erasure (keep for bookings) | Public; link-preview bots | Public by design | Owner's home address may be the venue address (owner choice; Terms note). |
| 12 | Referral code on venue, broker link | `venues.broker_id`, `referral_code`, `referred_at` | O (own), B (own), A/SA | Commission | Contract | Life of listing | — | — | None. |
| 13 | Booking: customer link or **guest name, email, phone**, guest count, **customer notes**, purpose, date/time, amount, pricing snapshot, manage token hash | `bookings` | C/G (own); O (bookings at own venues, including contact); A/SA; B sees reference, date, amount only (`ReferredBookingView`) | Fulfil booking, contact for the event, disputes | C or LU-a (Q-4) | Forever → 8 years for financial fields (D-07, Q-12); contact fields and notes anonymised 1 year after the event (D-07) | Venue owner; hosting | Manage token hashed; access checks per role | Guest PII never purged; notes free text may hold children's details. |
| 14 | Booking events, action requests (reason, metadata) | `booking_events`, `booking_action_requests` | O/C (own), A/SA | Audit trail of booking changes | LU-law / contract | Forever → same as booking | — | Append-only by convention | `metadata` may hold free text. |
| 15 | Payments: amount, method, gateway reference, raw payload, commission | `payments` | C (own), O (own venue), A/SA | Accounting, reconciliation | LU-law (tax) | Forever → 8 years (Q-12) | Bank / future gateway | Access control | `raw_payload` may carry payer details once a gateway is added. |
| 16 | Refunds, payouts, ledger, broker commissions and payouts | `refunds`, `payouts`, `ledger_entries`, `broker_commissions`, `broker_payouts`, `broker_payout_items` | Party concerned; A/SA | Accounting | LU-law | Forever → 8 years | Bank | Access control, ledger immutability | None beyond retention. |
| 17 | Reviews: rating, text, author, booking link | `reviews` | P (text + author first name); A/SA | Trust, quality | C (posting) | Forever → life of listing, or until author erasure (anonymise author) | Public | Admin moderation | **Any signed-in user can review any venue without a completed booking** (`backend/app/main.py:2365`); no verified badge; author erasure not handled. |
| 18 | Support tickets: subject, description, category, links to booking/venue; ticket events and comments (internal notes) | `support_tickets`, `ticket_events` | Creator; O (venue tickets); A/SA (incl. internal notes) | Support and grievances | C / LU-a | Forever → 2 years after closure (D-07) | — | Role checks | No `grievance` category, no acknowledgement or resolution due dates, no ticket number shown on contact form. |
| 19 | Guest enquiries (contact form, signed out): name, email, phone, subject, message | `guest_enquiries` | A/SA | Answer the enquiry / grievance | C / LU-a | Forever → 1 year after closure (D-07) | — | — | Not a ticket: no number, no SLA, no status updates for the sender. |
| 20 | Help search queries, feedback | `help_search_log.query`, `role`; `help_feedback.user_id` | A/SA | Improve help articles | Legitimate interest (Q-4) | Forever → 90 days | — | — | Search text may contain personal data typed by users. |
| 21 | Notifications and deliveries | `notifications.message`, `notification_deliveries.provider_response` | Self; A/SA | In-app notices | LU-a | Forever → 1 year | — | — | No purge. |
| 22 | Audit log: actor, action, entity, metadata | `audit_logs` | A/SA | Security, accountability | LU-law (DPDP r.6(c)/(e), CERT-In) | Forever → **at least 1 year** (r.6(e)), then 3 years max (D-07) | — | Append-only by convention | Metadata may include storage keys and names; no purge. |
| 23 | Rate-limit keys (contain **phone or email or IP** in clear text: `ratelimit:login:{login}`, `ratelimit:signup:{phone}`, `ratelimit:*:ip:{ip}`) | `login_rate_limits.key` | Nobody via UI; DB operators | Abuse prevention | Legitimate interest | Forever → delete rows 1 day after window ends | — | — | **Identifiers in clear text, never purged.** |
| 24 | Idempotency keys and cached responses (response bodies may contain booking and guest details) | `idempotency_keys` | Nobody via UI | Safe retries | LU-a | Has `expires_at`, never purged → delete after expiry | — | — | No purge job. |
| 25 | Jobs and outbox payloads | `jobs.payload`, `outbox_events.payload` | Nobody via UI | Background work | LU-a | Forever → 30 days after completion | — | — | No purge. |
| 26 | Homepage placements, banners, help articles (staff-authored) | `homepage_placements`, `site_banners`, `help_articles*` | P | Content | — | — | Public | — | Not personal data except author ids. |
| 27 | System configuration | `system_configuration` | A/SA | Platform rules (cancellation tiers, commission) | — | — | — | — | Not personal data. |

## 2. Files, logs, caches and backups

| # | Data item | Where stored | Who can see | Purpose | Ground | Retention today → recommended | Recipients | Protection today | Gaps |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 28 | Venue photos and videos (EXIF stripped, WebP) | `UPLOADS_DIR` volume `uploads` or public S3 bucket | P | Listing | Contract | Life of listing | Public, CDN if configured | EXIF/GPS stripped by `app/modules/storage/images.py` | Faces of people may appear; Terms should tell owners not to upload identifiable people without permission. |
| 29 | Banner images | same | P | Marketing banners | — | — | Public | Same | None. |
| 30 | Verification documents | `PRIVATE_UPLOADS_DIR` volume `private_uploads` or private S3 | A/SA | KYC | see row 8 | Forever → 1 year after decision (D-07) | Hosting / S3 | Not web-served; admin route only; access audited | Not encrypted at rest at application level (disk encryption depends on host, D-10). |
| 31 | API logs (uvicorn access log: client IP, method, path, status; app logs with request id) | Docker json-file logs of `api` container | Server operators | Debugging, security | LU-law (CERT-In, r.6) | Docker default: unbounded → rotate, keep **365 days** in India (CERT-In 180 days minimum, DPDP r.6(e) 1 year) | Hosting | Host access only | No rotation or retention set. **Guest manage tokens are in the URL path** (`/api/v1/bookings/manage/{token}`), so every access log holds a working credential for that booking. |
| 32 | Web/proxy logs (IP, user agent, URL, referrer) | `web` container nginx and host nginx `access.log` | Server operators | Security | LU-law | Default logrotate (host) / unbounded (container) → 365 days | Hosting | Host access only | Not documented; nginx proxies `/api`, so the same manage token appears in proxy logs. |
| 33 | Database backups (full copy of everything above) | `backups` volume, nightly `pg_dump`, deleted after 14 days | Server operators | Recovery | LU (r.6(d)) | 14 days | Hosting | Same host as DB | Same host = not an off-site backup; not encrypted; erased data survives up to 14 days in backups (document in notice). |
| 34 | Browser storage | `localStorage`: `groundkart_active_role`, `groundkart_favorites` (venue ids), `groundkart_referral_code`; `sessionStorage`: search filters, scroll positions, tab names | The visitor | UI convenience | Strictly necessary / user-initiated | Until cleared | None (never sent to third parties) | No tokens stored (access token in memory, refresh token in httpOnly cookie) | Should be listed in the cookie notice. |
| 35 | Cookie `refresh_token` (httpOnly, SameSite=Lax, Secure in prod, path `/api/v1/auth`) | Browser | — | Keep the user signed in | Strictly necessary | Until expiry (refresh TTL) | None | httpOnly | List in the cookie notice. |

## 3. What the browser sends to third parties

Scanned `frontend/index.html`, `frontend/src/**/*.{ts,tsx,css}` and `public/` for absolute URLs, and the built CSS for font URLs.

| Host | When it is contacted | Data sent | Status |
| --- | --- | --- | --- |
| `fonts.googleapis.com`, `fonts.gstatic.com` | Never. Fonts are bundled with `@fontsource-variable/inter` and `@fontsource-variable/fraunces`. | — | **Hypothesis disproved** (fixed in round 1). |
| `lh3.googleusercontent.com`, `images.unsplash.com` | Never. No references in source or seed data; homepage images are self-hosted under `/img/`. | — | **Hypothesis disproved.** |
| `www.youtube.com`, `player.vimeo.com` | When a visitor opens a venue page whose owner added a YouTube/Vimeo video: the `<iframe>` loads on render. | Visitor IP, user agent, referrer, YouTube/Vimeo cookies | **Gap**: third-party request without notice; fix with click-to-load player (`youtube-nocookie.com`) and disclosure (Q-21). |
| `www.google.com/maps` | Only when the visitor clicks "Open in Maps" (a link). | Coordinates in URL, visitor IP | Acceptable (user-initiated navigation); disclose. |
| `wa.me` | Only when an admin or broker clicks a WhatsApp share link. | Message text | Acceptable (user-initiated); disclose. |
| `schema.org`, `www.w3.org` | Never (namespace strings in JSON-LD/SVG). | — | — |
| `www.quantaliez.com` | Only on click (footer credit link). | — | Acceptable. |

No analytics, advertising pixels, tag managers, chat widgets, error-tracking SDKs or A/B tools exist in the frontend or `index.html` (verified by grep for `gtag`, `googletagmanager`, `fbq`, `hotjar`, `clarity`, `segment`, `mixpanel`, `sentry`, `intercom`, `crisp`, `tawk`: no matches).

## 4. Processors and other recipients

| Recipient | Role | Data | Location | Contract status |
| --- | --- | --- | --- | --- |
| VPS / hosting provider `[[OWNER TO FILL: hosting provider and data-centre region]]` | Processor | Everything (DB, files, logs, backups) | `[[OWNER TO FILL]]` (should be India, Q-7) | Provider's standard terms; DPA to check (vendor register) |
| Object storage (only if `STORAGE_BACKEND=s3`) `[[OWNER TO FILL: provider]]` | Processor | Venue media, verification documents | `[[OWNER TO FILL]]` | To check |
| Venue owners | Separate Data Fiduciaries (Q-5) | Customer name, phone, email, notes, guest count for their bookings | India | Terms of Service for owners (draft) |
| Brokers | Recipient of business data only | Venue names, booking references, dates, amounts | India | Partner agreement `[[OWNER TO FILL]]` |
| Banks / UPI | Independent | Payee details for manual payouts and refunds | India | n/a |
| Email/SMS provider | **None integrated** | — | — | Add to register before integrating |
| Payment gateway | **None integrated** (offline only) | — | — | Add to register before integrating |
| YouTube, Vimeo | Independent (embed) | Visitor IP, cookies when player loads | Outside India | Disclose; click-to-load |
| GitHub (CI/CD) | Processor for source code only | No personal data (tests use synthetic data) | Outside India | Standard terms |

## 5. Children's data

No date of birth or age field exists anywhere. There is no 18+ check. Free-text fields where children's details could appear: booking `customer_notes`, ticket descriptions and comments, reviews, guest enquiry messages, venue descriptions written by owners (e.g. "coaching for school children" in seed data). Planned: 18+ declaration, notice text asking users not to enter children's details, and the admin minor-account action.

## 6. Demo and seed data

`backend/scripts/seed_dataset.py`, `seed_demo_data.py`, `full_pipeline_seed.py` create demo owners, customers, venues, bookings and sample reviews, all with synthetic names and the shared demo password `Demo@2026!`; `seed_dataset.py` defaults `--admin-password` to `Admin@2026!`. Both scripts refuse to run when `ENVIRONMENT` is `prod`/`production`. **No marker distinguishes demo rows** once they exist, so a database seeded in staging and promoted would carry fake reviews into production. Planned: a `DEMO_MODE` setting and an `is_demo` flag on seeded users/venues/reviews, a visible "DEMO DATA" banner when demo rows are present, and a production start-up check that refuses to serve if demo rows exist.
