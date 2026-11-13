# GroundKart handover

Everything needed to run, deploy and maintain GroundKart. Start here.

Branch: `compliance/dpdp` (merge into `main` by pull request; merging deploys). Date: 11 November 2026.

## Read first

| Who | Document |
| --- | --- |
| Super admin (owner) | [docs/guides/SUPER_ADMIN_GUIDE.md](docs/guides/SUPER_ADMIN_GUIDE.md) |
| Admins | [docs/guides/ADMIN_GUIDE.md](docs/guides/ADMIN_GUIDE.md) |
| Customers and owners (how the site works) | [docs/03-features-and-user-guides/USER_GUIDE.md](docs/03-features-and-user-guides/USER_GUIDE.md), [BOOKING_LIFECYCLE.md](docs/03-features-and-user-guides/BOOKING_LIFECYCLE.md) |
| Whoever deploys (Hostinger VPS) | [docs/09-operations-and-deployment/DEPLOYMENT.md](docs/09-operations-and-deployment/DEPLOYMENT.md) |
| Owner decisions still open | [DECISIONS_NEEDED.md](DECISIONS_NEEDED.md) |
| Compliance result and lawyer questions | [COMPLIANCE_REPORT.md](COMPLIANCE_REPORT.md) |
| What changed | [CHANGELOG.md](CHANGELOG.md) |

## Compliance pack (`docs/compliance/`)

| File | What it is |
| --- | --- |
| `RESEARCH.md` | Laws researched (DPDP Act and Rules, E-Commerce Rules, dark patterns, IT/SPDI, CERT-In), dates, 22 lawyer questions |
| `DATA_MAP.md` | Every piece of personal data: where stored, who sees it, purpose, retention, recipients |
| `COMPLIANCE_PLAN.md` | Gap analysis before the work and the backlog |
| `source_checklist.md` | The 36-item checklist used for scoring |
| `drafts/` | Policy drafts for lawyer review: privacy notice (English, Hindi), terms, refunds, cookies, grievance, data rights, breach response plan, vendor register, retention schedule |
| `evidence/before`, `evidence/after` | Screenshots |
| `score.py` | Re-runs the 36-item score |

## Before launch (owner)

1. Fill **Legal and business details** in the admin console (company, CIN, address, Grievance Officer, jurisdiction).
2. Have a lawyer review the drafts in `docs/compliance/drafts/` and the answers in `DECISIONS_NEEDED.md`.
3. Sign data-processing terms with Hostinger; record them in the vendor register.
4. Point the domain at the VPS and follow DEPLOYMENT.md first-time setup.
5. Approve the founder text on the homepage (or edit it in Admin › Homepage content and images).

## Product facts

- Backend: FastAPI, PostgreSQL, Alembic (`backend/`). Frontend: React, Vite, TypeScript (`frontend/`).
- Tests: backend `pytest -m "not owner_facts"` (572), frontend `vitest` (199), browser `playwright` (compliance and regression suites).
- Never commit `.env`, uploads or database dumps. Never run `docker compose down -v`.
