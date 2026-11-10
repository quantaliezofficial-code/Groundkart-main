# Changelog

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
