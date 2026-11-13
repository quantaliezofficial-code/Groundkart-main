# Data retention schedule

> DRAFT FOR LAWYER REVIEW. Version 1.0, 10 November 2026. Periods are **suggested defaults** awaiting owner decision D-07 and lawyer question Q-12. The code copy of this table is `RETENTION_DAYS` in `backend/app/modules/privacy/retention.py`; `test_compliance_retention.py` fails if the two disagree. The daily retention job runs inside the API process.

| Data class | Table / store | Period | Starts from | Deletion method | Legal reason to keep longer |
| --- | --- | --- | --- | --- | --- |
| Rate-limit counters | `login_rate_limits` | 1 day | end of window | Delete row | — |
| Idempotency keys and cached responses | `idempotency_keys` | 0 days | `expires_at` | Delete row | — |
| Refresh tokens (expired or revoked) | `refresh_tokens` | 30 days | expiry or revocation | Delete row | — |
| Password reset requests | `password_reset_requests` | 90 days | creation | Delete row | — |
| Help search queries | `help_search_log` | 90 days | creation | Delete row | — |
| Completed jobs and delivered outbox events | `jobs`, `outbox_events` | 30 days | creation | Delete row | — |
| In-app notifications | `notifications` | 365 days | creation | Delete row | — |
| Guest enquiries (legacy, before tickets) | `guest_enquiries` | 365 days | creation | Delete row | — |
| Guest booking contact and booking notes | `bookings.guest_name/guest_email/guest_phone/customer_notes` | 365 days | event date | Anonymise fields | Financial fields kept (row below) |
| Resolved and closed support tickets | `support_tickets`, `ticket_events` | 730 days | closure | Anonymise creator contact and text | Open disputes or legal claims |
| Verification documents | private file store | 365 days | review decision | Delete file, clear `storage_key` | Ongoing fraud investigation |
| Verification numbers (ID number, PAN, GSTIN) and bank details | `owner_verifications`, `owner_bank_accounts` | Until account closure | closure | Erase fields (encrypted values cleared) | Payout records keep the amount and reference only |
| Consent records | `consent_records` | 365 days | account closure | Delete row | Burden of proof (DPDP s.6(10)); keep while account exists |
| Security and audit logs | `audit_logs`; API and proxy logs | 365 days (never less) | creation | Delete row / rotate | CERT-In: at least 180 days in India; DPDP r.6(e) and r.8(3): at least 1 year |
| Breach incidents | `breach_incidents` | Never deleted | — | — | Accountability |
| Data requests (rights) | `data_requests` | 3 years | closure | Delete row | Proof of compliance |
| Booking, payment, refund, payout, ledger and commission records | `bookings` (financial fields), `payments`, `refunds`, `payouts`, `ledger_entries`, `broker_*` | 8 years | end of financial year | Keep; personal fields anonymised on erasure | Tax and accounting law (Q-12) |
| Closed accounts | `users` | Immediately on closure | closure | Anonymise name, email, phone, password; keep id | Financial rows above point to the id |
| Inactive accounts (no sign-in, no booking) | `users` | 3 years, with 48 h warning | last activity | Warn, then anonymise as closed | Voluntary (D-08); Third Schedule threshold not met |
| Database backups | `backups` volume | 14 days | backup time | Rolling delete | Recovery (r.6(d)) |
