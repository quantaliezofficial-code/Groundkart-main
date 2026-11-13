# Vendor and processor register

> DRAFT FOR LAWYER REVIEW. Version 1.0, 10 November 2026. Update before adding any new tool that touches personal data (email or SMS provider, payment gateway, analytics, error tracking, CRM). DPDP Rules r.6(1)(f) requires security terms in contracts with Data Processors.

## Register

| Vendor | Service | Role | Personal data | Location | Contract / DPA | Security terms checked | Deletion on exit | Owner action |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| [[OWNER TO FILL: hosting provider and data-centre region]] | VPS hosting: database, files, logs, backups | Processor | All personal data in DATA_MAP | [[OWNER TO FILL: region]] | [[OWNER TO FILL: contract status]] | No | No | D-05, D-09 |
| [[OWNER TO FILL: object storage provider]] (only if `STORAGE_BACKEND=s3`) | Object storage for venue media and verification documents | Processor | Photos, videos, identity documents | [[OWNER TO FILL: region]] | [[OWNER TO FILL: contract status]] | No | No | D-05, D-09 |
| GitHub | Source code and CI | Processor (no personal data) | None: tests use synthetic data only | Outside India | GitHub standard terms | n/a | n/a | — |
| YouTube / Vimeo | Video player embedded by owners, click-to-load | Independent | Visitor IP when the visitor presses play | Outside India | None (visitor's own choice; disclosed) | n/a | n/a | Q-21 |
| Banks / UPI providers | Payments and payouts | Independent | Payee details | India | n/a | n/a | n/a | — |
| Email / SMS provider | **None yet** | — | — | — | — | — | — | Add a row before integrating |
| Payment gateway | **None yet** | — | — | — | — | — | — | Add a row before integrating (RESEARCH §7) |

## Contract checklist for every processor

A processor contract (or the provider's data processing addendum) should cover:

1. Processing only on GroundKart's documented instructions and only for GroundKart's purposes.
2. Confidentiality of staff with access.
3. Reasonable security safeguards at least equal to DPDP Rules r.6: encryption, access control, logging and monitoring, backups.
4. Breach notice to GroundKart **without delay** and in any case in time for GroundKart to meet the 6-hour CERT-In and 72-hour Board clocks (ask for notice within a few hours).
5. Sub-processors: list provided, prior notice of changes, same obligations flowed down.
6. Location of data and logs (India preferred; CERT-In logs must be producible in India).
7. Deletion or return of all personal data at the end of the contract or on request, with written confirmation; deletion from backups within a stated period.
8. Help with Data Principal requests and with Board or CERT-In inquiries.
9. Audit or evidence of controls (for example ISO/IEC 27001 certificate or SOC 2 report).
10. Retention of logs for at least 1 year where the processor holds them.
