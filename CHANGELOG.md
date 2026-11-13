# Changelog

## 2026-11-11 — Compliance (DPDP), trust homepage and Hostinger deployment

Branch `compliance/dpdp`. Full write-up in `COMPLIANCE_REPORT.md`; owner inputs in `DECISIONS_NEEDED.md`. All policy texts are drafts for lawyer review.

### New
- **Legal pages:** Privacy Notice (English and Hindi), Terms, Refunds and cancellations, Cookies and third parties, Grievance redressal, Your data rights. Versioned, dated, with visible placeholders for facts the owner has not supplied.
- **Consent and age:** unticked 18+ box and agreement line at sign-up and guest checkout; append-only consent records; a banner asking existing accounts to accept the current notice.
- **My data** (`/account/data`): download, correct, nominee, consents, withdraw, delete, request tracking.
- **Grievance clocks:** every contact message becomes a numbered ticket (`GK-T-…`) with acknowledgement and resolution due dates.
- **Admin › Privacy and compliance:** overdue clocks, data requests, incident register with CERT-In (6 h) and Board (72 h) deadlines, two-step sign-in set-up.
- **Admin › Rules and fees › Legal and business details** (super admin): fills the legal pages, footer and checkout.
- **Admin two-step sign-in** (authenticator app, recovery codes), required in production.
- **Homepage:** full-bleed photo hero and six occasion cards from the supplied Unsplash photos (self-hosted WebP); booking protections, a step-through booking preview, verified-booking reviews only, founder story.
- **Hostinger deployment (Exotique procedure):** rollback branch, verified database backup before migrations, health checks and automatic rollback; loopback ports 3002/5001; bundled or shared PostgreSQL; backup and restore scripts; deploy dry run in CI.
- `docs/compliance/score.py` scores the site against the 36-item checklist (8/36 before, 32/36 now, 36/36 once four owner facts are entered).

### Security
- AES-256-GCM encryption for identity, PAN, GSTIN, bank account numbers and 2FA secrets; masked by default with audited reveal; Aadhaar limited to the last four digits.
- CSP, HSTS and frame protection; secrets redacted from application and nginx logs; rate-limit keys hashed; log rotation.
- Production refuses to start with demo data or known development passwords; seed admin password must be supplied.
- Retention job (one runner at a time) anonymises old bookings and removes expired verification documents.
- Non-breaking npm security updates.

### Super admin website control
- **Admin › Homepage content and images:** the super admin edits every homepage text, the photos, the occasion cards (3 to 8), the questions, the founder story, and which sections show. Changes go live with Publish; History keeps 30 versions with restore; Reset returns to the built-in copy. Other admins can view only.
- **Image library:** uploads are resized to WebP with location data removed; images in use cannot be deleted.
- **Review moderation:** the super admin can hide a review (with a logged reason) or feature a completed-booking review. Customer text and stars are never editable. Hidden reviews leave pages, homepage and ratings.
- **Users › Under 18:** closes an account that belongs to a minor and erases its data.
- Admin and Super Admin guides in `docs/guides/` (Markdown and PDF), and `HANDOVER.md`.

### Security (second pass)
- Nothing private by URL: hidden files, source maps, configs, dumps, server paths and API docs return 404 (web and host nginx); signed-in areas are `noindex`/`no-store`; API docs off in production; `check_exposure.sh` runs after every deploy.
- Database studio hides credential, 2FA, ID, bank and IP columns, audit-logs every look, and its SQL console is off in production.
- PyJWT 2.15.1; backslash-safe internal links; SSH deploy action pinned to a commit; CI dependency audit and Semgrep report.
- Pop-ups: the notice banner can be closed and stays closed; closed announcements stay closed across visits; repeated toasts no longer stack.

### Changed
- Reviews count and show only when tied to the reviewer's own completed booking.
- Venue videos load only when clicked (`youtube-nocookie`), so no third party is contacted on page load.
- Deleting an account now erases personal data and keeps only records the law requires.

## 2026-11-10 — Production release preparation

### New
- **Super admin and admin team.** One super admin (database-enforced). Only they can add or suspend admins, set referral partner rates and status, regenerate partner codes and change the default partner rate. Regular admins can no longer suspend or reset the password of other admins or the super admin.
- **Referral partners (brokers).** Added by admins only. Each gets a referral code and a listing link (`/owner?ref=CODE`). Owners enter the code on the first listing step (checked live). Commission is recorded in the same transaction as the confirmed offline payment, at the rate fixed at that moment, reversed proportionally on refunds, payable after the event date, and settled in recorded payouts.
- **Partner dashboard** (`/broker`): code and share link, referred venues with review status and pricing, bookings with payment state, earnings ledger, payouts, profile, CSV exports. No customer personal data is exposed.
- **Admin: Referral partners, Banners, Records and exports, Rules and fees, Admin team.** Existing tabs kept; navigation grouped.
- **Records and exports:** booking register and venue register with the full money trail, filters that match the CSV export, venue history timeline, nine CSV exports (Excel-safe, IST times, formula-injection safe). Every export is audited.
- **Banners:** multiple per placement (homepage feature, announcement strip, search results), scheduling, ordering, safe links only.
- **Open Graph share pages** for venues and categories, served to link-preview crawlers by nginx.
- **Deployment:** Dockerfiles, `docker-compose.yml` with nightly backups, nginx configs, GitHub deploy workflow, production env template. See `docs/09-operations-and-deployment/DEPLOYMENT.md`.
- **Business strategy:** `docs/10-business/BUSINESS_STRATEGY.md`.

### Improved
- Homepage rebuilt around search and the six occasions, using the supplied images (cropped, WebP, responsive sizes). Honest copy: removed invented testimonials, "Trending in Metropolis", fake "instant booking" and "verified" claims, a made-up review count fallback, seeded favourites and artificial loading delays. FAQ with structured data.
- Scroll jitter removed: replaced the JavaScript scroll engine with native scrolling; scroll-triggered fade-ins no longer hide content; venue cards no longer animate on mount.
- Performance: uploads re-encoded to WebP with metadata stripped (phone GPS included) and size capped; client-side compression before upload; self-hosted fonts; vendor chunk splitting; long-cache headers; hot-linked stock photos removed.
- API error messages are readable sentences instead of raw JSON.

### Fixed
- Category search returned no results for every category except sports.
- Admin user search ignored the search box.
- Admin Users list failed for accounts without an email.
- Uploads were trusted by declared content type; non-images are now refused.
- Per-IP rate limits could be bypassed with a spoofed `X-Forwarded-For`.
- Owner account deletion did not end the user's other sessions; venue archive and account deletion were not audited; debug prints removed.

### Unchanged by request
- Offline payment only (online payments later). Forgot-password flow as before.
