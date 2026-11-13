# Drafts for lawyer review

Every file here is a **DRAFT FOR LAWYER REVIEW** prepared by engineers. None of it is legal advice. Business facts that the owner has not supplied appear as `[[OWNER TO FILL: …]]` placeholders; see `DECISIONS_NEEDED.md` at the repository root.

| File | What it is | Where it is used |
| --- | --- | --- |
| `privacy-notice.en.md`, `privacy-notice.hi.md` | Privacy Notice in English and Hindi (Hindi needs a translator's check, D-21) | `/privacy` (language switch) |
| `terms.en.md` | Terms of Service, including governing law, disputes, user content rules, marketplace role, cancellation tiers, liability and the 18+ rule | `/terms` |
| `refunds.en.md` | Refund and Cancellation Policy | `/refunds`, linked at checkout |
| `cookies.en.md` | Cookie and Third-party Notice | `/cookies`, footer "Cookie settings" |
| `grievance.en.md` | Grievance Redressal page with timelines | `/grievance` |
| `data-rights.en.md` | Data Principal rights procedure | `/your-data` |
| `breach-response-plan.md` | Breach and cyber incident plan (6 h CERT-In, 72 h Board) | Internal |
| `vendor-register.md` | Processor register and contract checklist | Internal |
| `retention-schedule.md` | Retention periods and deletion methods | Internal; summarised in the notice |

The page drafts are copies of `frontend/src/content/legal/*.md`. Edit the frontend file, then run `python docs/compliance/sync_drafts.py`. Tokens such as `{{full_refund_hours}}` are filled from the live booking settings when the page renders, so the policy always matches the code.

**For the reviewing lawyer:** please also see the 22 open questions in `docs/compliance/RESEARCH.md` §10.
