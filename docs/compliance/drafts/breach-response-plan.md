# Personal data breach and cyber incident response plan

> DRAFT FOR LAWYER REVIEW. Prepared by the GroundKart engineering team, version 1.0, 10 November 2026. Not legal advice. Placeholders in double square brackets are owner decisions (DECISIONS_NEEDED D-17).

## 1. Scope

Any event that compromises the confidentiality, integrity or availability of personal data GroundKart holds (a **personal data breach** under DPDP Act s.2(u)), and any **cyber incident** of a type listed in Annexure I of the CERT-In Directions of 28 April 2022 (for example unauthorised access to servers, databases or admin accounts; data leak; website defacement; malware; denial of service; attacks on cloud or APIs). One event is often both.

## 2. Clocks

| Notice | To | Deadline | Source |
| --- | --- | --- | --- |
| Cyber incident report | CERT-In (incident@cert-in.org.in, phone/fax on cert-in.org.in, prescribed form) | **6 hours** from noticing or being told | CERT-In Directions (ii), in force since 27 Jun 2022 |
| Initial breach intimation | Data Protection Board of India | **Without delay** | DPDP Rules r.7(2)(a), from 13 May 2027 |
| Detailed breach report | Data Protection Board of India | **72 hours** from becoming aware (or longer if the Board allows on written request) | DPDP Rules r.7(2)(b) |
| Notice to each affected person | Affected users, through their account and registered contact | **Without delay** | DPDP Rules r.7(1) |
| Log production | CERT-In on request | As directed | CERT-In Directions (iv): logs kept 180 days in India |

The admin **Compliance → Incidents** screen computes `cert_in_due_at = detected_at + 6 h` and `board_report_due_at = detected_at + 72 h` the moment an incident is logged, and shows overdue items in red.

## 3. Roles

| Role | Person | Duties |
| --- | --- | --- |
| Incident lead | [[OWNER TO FILL: incident lead]] (default: the super admin) | Declares the incident, owns the clocks, signs off notices |
| Deputy | [[OWNER TO FILL: deputy incident lead]] | Takes over if the lead is unreachable for 30 minutes |
| Technical responder | [[OWNER TO FILL: technical responder]] | Contains, preserves evidence, restores service |
| CERT-In point of contact | [[OWNER TO FILL: CERT-In point of contact]] | Files the CERT-In report |
| Legal adviser | [[OWNER TO FILL: legal adviser]] | Reviews Board and user notices |

Keep a printed copy of this table and phone numbers off the server.

## 4. Steps

1. **Detect and log (0–30 min).** Anyone who sees signs of a breach (alert, unusual admin activity in the audit log, a user report, a leaked file) tells the incident lead and logs it in **Compliance → Incidents** with what is known. Detection time is the time you noticed, not the time you were sure.
2. **Contain (as fast as possible).** Revoke sessions (`refresh_tokens` revocation for affected accounts), rotate secrets (`JWT_SECRET`, database password, `FIELD_ENCRYPTION_KEY` re-wrap if exposed, S3 keys), block abusive IPs at the proxy, take the affected component offline if needed, and force password resets.
3. **Preserve evidence.** Snapshot logs (API, nginx, audit log) and the database before cleaning up. Do not delete logs. Record every action with time in the incident timeline.
4. **CERT-In (≤ 6 h).** If the event is a listed incident type, file the report even if facts are incomplete; send updates later. Record the submission time in the incident.
5. **Assess.** What data, how many people, which categories (contact details, ID numbers, bank details, documents), likely consequences.
6. **Board, initial (without delay).** Send the description: nature, extent, timing, location, likely impact.
7. **Users (without delay).** Notify every affected person through their GroundKart account (in-app notification) and their registered email/phone, using the template in §5.
8. **Board, detailed (≤ 72 h).** Facts and reasons, mitigation, findings about who caused it, remedial measures, and the report of user notices sent.
9. **Recover and review.** Restore from backup if needed, fix the root cause, add a test, and hold a review within 14 days. Close the incident with the lessons recorded.

## 5. User notice template

> **Subject: Important: a security incident affecting your GroundKart account**
>
> On [date] we discovered [what happened, in one sentence]. It happened on [date/time] and affected [what data: e.g. your name and phone number].
>
> **What this means for you:** [likely consequences, e.g. you may receive calls or messages pretending to be GroundKart].
>
> **What we have done:** [containment and fixes].
>
> **What you can do:** [e.g. change your password, watch for messages asking for payment, never share OTPs].
>
> If you have questions, contact our Grievance Officer [[OWNER TO FILL: Grievance Officer name]] at [[OWNER TO FILL: grievance email]] or [[OWNER TO FILL: grievance phone]], quoting reference [incident reference].

## 6. Incident register

The `breach_incidents` table is the register. Each incident records: reference, title, description, detected and occurred times, data categories, number of people affected, status, the three deadlines, the times each notice was actually sent, containment and remediation notes, and who logged and closed it. Never delete an incident.

## 7. Practice

Run a table-top exercise every six months using a fictional incident (for example "an admin laptop with a saved session is stolen"), time each step against the clocks, and update this plan.
