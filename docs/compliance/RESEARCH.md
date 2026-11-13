# GroundKart: legal research for India website and data compliance

> **Engineering research, not legal advice.** Prepared by the engineering team on 10 November 2026 to scope product work. Every conclusion below is a working reading for a qualified lawyer to confirm. Uncertainties are collected in section 10, "Questions for a lawyer".

Reading date for every source below: **10 November 2026** unless stated.

## 1. Sources read

Primary sources first. Where an official site would not serve the document to an automated reader (egazette.gov.in blocks robots; meity.gov.in renders its document list with JavaScript), we read a faithful reproduction of the Gazette text and record both URLs. A lawyer should confirm against the certified Gazette copy.

| # | Instrument | Version / date read | Primary source | Copy actually read (if different) |
| --- | --- | --- | --- | --- |
| S1 | Digital Personal Data Protection Act, 2023 (Act 22 of 2023) | As enacted 11 Aug 2023; S.O. 5458(E) Removal of Difficulties Order of 6 Oct 2026 reported (wording fixes to s.9(1) and s.10(2)(c)(ii)), not yet read in Gazette form | Gazette of India Extraordinary, Part II Sec 1, 11 Aug 2023; MeitY: https://www.meity.gov.in/ (Acts and Policies) | Section and Schedule text via https://dpdp.myndsolution.com/wiki/act/schedule/ (states "verbatim from the Gazette") |
| S2 | Commencement notification under s.1(2) | G.S.R. 843(E), 13 Nov 2025 (Gazette No. 757) | https://egazette.gov.in (No. 757 of 13 Nov 2025) | https://dpdp.myndsolution.com/wiki/notifications/gsr-843e-2025-commencement/ |
| S3 | Digital Personal Data Protection Rules, 2025 | G.S.R. 846(E), dated 13 Nov 2025, Gazette No. 760 (CG-DL-E-14112025-267650) | https://egazette.gov.in/WriteReadData/2025/267650.pdf ; MeitY page https://www.meity.gov.in/documents/act-and-policies/digital-personal-data-protection-rules-2025 | https://dpdpa.com/DPDP_Rules_2025_English_only.pdf (Gazette PDF copy) |
| S4 | MeitY stakeholder consultation on DPDP timeline | PIB release, 22 Jan 2026 | https://www.pib.gov.in/PressReleasePage.aspx?PRID=2206598 | Reported by Khurana & Khurana (Mondaq, 18 Mar 2026) and S.S. Rana (13 Feb 2026) |
| S5 | Consumer Protection (E-Commerce) Rules, 2020 | G.S.R. 462(E), 23 Jul 2020, in force 24 Jul 2020 | https://consumeraffairs.nic.in (Acts and Rules) / egazette | Summaries: Khaitan & Co (27 Jul 2020), HSA (Sep 2020) |
| S6 | Consumer Protection (E-Commerce) (Amendment) Rules, 2026 | G.S.R. 789(E), 9 Sep 2026, **in force 1 Jan 2027** | https://consumeraffairs.nic.in / egazette | Summaries: SCC Online (14 Sep 2026), AZB (18 Sep 2026), Argus (Mondaq, 23 Sep 2026), Bar & Bench, Conventus Law |
| S7 | CCPA Guidelines for Prevention and Regulation of Dark Patterns, 2023 | Gazette, 30 Nov 2023 (13 specified patterns, Annexure 1) | https://consumeraffairs.nic.in (CCPA) | PIB 8 Dec 2023 (via productgrowth.in source list) |
| S8 | CCPA Advisory on self-audit for dark patterns | CCPA-1/1/2023-CCPA, 5 Jun 2025 | https://consumeraffairs.nic.in (CCPA advisories) | Text reproduced by TaxGuru; PIB 20 Nov 2025 (26 platforms declared compliance); PIB 3 Jun 2026 (orders against two platforms) |
| S9 | Information Technology Act, 2000, s.43A and s.72A; IT (Reasonable Security Practices and Procedures and Sensitive Personal Data or Information) Rules, 2011 | G.S.R. 313(E), 11 Apr 2011 | https://www.meity.gov.in (IT Act and Rules) | Read from memory of the published text; confirm (see Q-14) |
| S10 | IT (Intermediary Guidelines and Digital Media Ethics Code) Rules, 2021 | G.S.R. 139(E), 25 Feb 2021, as amended by G.S.R. 794(E), 28 Oct 2022 and later amendments | https://www.meity.gov.in | Read from memory of the published text; confirm (see Q-15) |
| S11 | CERT-In Directions under s.70B(6) IT Act | No. 20(3)/2022-CERT-In, 28 Apr 2022, effective 27 Jun 2022; FAQs 18 May 2022 | https://www.cert-in.org.in/PDF/CERT-In_Directions_70B_28.04.2022.pdf ; https://www.cert-in.org.in/PDF/FAQs_on_CyberSecurityDirections_May2022.pdf | Primary PDF read directly |
| S12 | RBI rules on payment aggregators and card data storage | Pointer only, not read in this pass | https://www.rbi.org.in | — |

## 2. What is in force today (10 Nov 2026) and what comes later

Verified from S2 and S3 (the Rules count every period from publication in the Gazette; neither notification names a calendar date):

| Date | Act provisions | Rules | Effect for GroundKart |
| --- | --- | --- | --- |
| 13 Nov 2025 (in force) | s.1(2), s.2 (definitions), s.18–26 (Data Protection Board), s.35, s.38–43, s.44(1) and (3) | Rules 1, 2, 17–21 | Board exists. **No duty to Data Principals yet under DPDP.** |
| **13 Nov 2026 (in 3 days)** | s.6(9), s.27(1)(d) | Rule 4 (Consent Managers) | Consent Managers can register. GroundKart is not one; nothing to build. |
| **13 May 2027** | s.3–5, s.6(1)–(8) and (10), s.7–17, s.27 (rest), s.28–34 (penalties), s.36–37, s.44(2) (omits IT Act s.43A) | Rules 3, 5–16, 22, 23 | Notice, consent, safeguards, breach intimation, erasure, children, rights, grievance, transfer and **penalties** all apply. |
| Until 13 May 2027 | IT Act s.43A and the **SPDI Rules 2011 remain in force** | — | Today's binding privacy baseline: privacy policy (r.4), consent for SPDI (r.5), grievance officer resolving within one month (r.5(9)), reasonable security practices (r.8). |
| In force since 24 Jul 2020 | E-Commerce Rules 2020 | — | Binding today (see section 4). |
| **1 Jan 2027** | E-Commerce (Amendment) Rules 2026 | — | Stricter disclosure, ranking, dark-pattern and grievance duties. |
| In force since 30 Nov 2023 | Dark Patterns Guidelines | — | Binding today. |
| In force since 27 Jun 2022 | CERT-In Directions | — | Binding today: 6-hour reporting, 180-day logs. |

**Date uncertainty (Q-1):** the Rules are *dated* 13 Nov 2025 but several firms (AMS Shardul, Lidings, SCC Online) date publication 14 Nov 2025, which would move the later dates to 14 Nov 2026 and 14 May 2027. We plan to **13 May 2027** (the earlier date) to be safe.

**Proposed acceleration (S4):** on 22 Jan 2026 MeitY consulted on shortening the 18-month window to 12 months, at least for Significant Data Fiduciaries, with comments due 4 Feb 2026. Our searches on 10 Nov 2026 found **no amending notification**; a Lok Sabha answer of 12 Aug 2026 was reported as still describing 18 months. If it is notified, the core duties could start on or soon after 13 Nov 2026. GroundKart's plan therefore treats P1 items as "build now", not "build by May".

**Removal of Difficulties Order (S1):** S.O. 5458(E) of 6 Oct 2026 is reported to make wording fixes to s.9(1) (children) and s.10(2)(c)(ii) (SDF). We have not read the Gazette text (Q-2).

## 3. DPDP Act 2023 and DPDP Rules 2025: what they require

All section numbers refer to S1 and rule numbers to S3.

### 3.1 Definitions (s.2)

- **Data Principal**: the individual the data relates to; for a child, includes the parent or lawful guardian.
- **Data Fiduciary**: anyone who alone or with others decides the purpose and means of processing.
- **Data Processor**: anyone who processes data on behalf of a Data Fiduciary.
- **Child** (s.2(f)): an individual who has not completed eighteen years.
- **Personal data breach**: unauthorised processing or accidental disclosure, acquisition, sharing, use, alteration, destruction or loss of access that compromises confidentiality, integrity or availability.
- The Act applies to digital personal data (and non-digital data later digitised) processed in India (s.3).

### 3.2 Notice (s.5, Rule 3)

Every request for consent must be accompanied or preceded by a notice. Rule 3 requires the notice to be **standalone**, in clear and plain language, a fair account enabling specific and informed consent, and at minimum:

1. an itemised description of the personal data and the specified purpose(s), with a description of the goods or services the processing enables;
2. the communication link (website or app) and description of other means by which the person can **withdraw consent** (as easily as it was given), **exercise rights**, and **complain to the Board**.

s.5(3): the person must have the option to read the notice in **English or any language in the Eighth Schedule to the Constitution** (22 languages). s.5(2): people who consented before commencement must be given a notice as soon as reasonably practicable (Q-3: this likely covers all GroundKart users who sign up before 13 May 2027).

### 3.3 Consent (s.6) and legitimate uses (s.7)

- Consent must be **free, specific, informed, unconditional and unambiguous with a clear affirmative action**, limited to the data necessary for the purpose (s.6(1)). Any part of a consent that infringes the Act is invalid.
- Withdrawal must be as easy as giving (s.6(4)); after withdrawal the fiduciary and its processors must stop processing within a reasonable time unless the law permits otherwise (s.6(6)). Withdrawal does not affect prior lawful processing.
- Burden of proving notice and consent is on the fiduciary (s.6(10)) → **we must keep consent records.**
- Consent Managers (s.6(7)–(9), Rule 4) are optional for fiduciaries.
- **Legitimate uses (s.7)** include (a) a specified purpose for which the person *voluntarily provided* data and has not indicated non-consent, and others (legal obligations, medical emergencies, employment). s.7(a) is the likely ground for a guest giving name/email/phone to make a booking (Q-4).

### 3.4 General duties of a Data Fiduciary (s.8)

- s.8(1): responsible for processing by its processors.
- s.8(3): completeness and accuracy when data is used for decisions or disclosed.
- **s.8(5) + Rule 6: reasonable security safeguards**, at minimum: (a) encryption, obfuscation, masking or virtual tokens; (b) access control; (c) logs, monitoring and review to detect unauthorised access; (d) continuity measures such as backups; (e) **retaining logs and personal data for one year** for detection, investigation and remediation, unless another law says otherwise; (f) security terms in contracts with processors; (g) technical and organisational measures to make sure of observance.
- **s.8(6) + Rule 7: breach intimation**
  - to each affected person **without delay**, in plain language, through their account or registered contact: nature, extent, timing and location; likely consequences; mitigation steps; safety steps they can take; business contact details;
  - to the Board **without delay** (a description), and **within 72 hours** of becoming aware (or longer if the Board allows on written request) a detailed report: facts, circumstances and reasons, mitigation, findings about the person who caused it, remedial measures, and a report on the user notices given.
- **s.8(7) + Rule 8: erasure** when the person withdraws consent or the specified purpose is no longer served, unless retention is required by law; processors must erase too. **Third Schedule:** e-commerce entities with **at least 2 crore registered users** in India (and online gaming ≥50 lakh, social media ≥2 crore) must treat the purpose as over after **3 years** without the user approaching them or exercising rights; **48 hours' notice** before erasure (Rule 8(2)). **Rule 8(3) + Seventh Schedule:** personal data, traffic data and logs must be retained for **at least one year** from processing for the State purposes listed, then erased unless another law requires retention.
- **s.8(9) + Rule 9:** publish prominently on the website the business contact information of a Data Protection Officer (SDF only) or **a person able to answer questions** about processing, and state it in every response to a rights request.
- **s.8(10):** an effective grievance redressal mechanism.

### 3.5 Children (s.9, Rules 10–12)

- Verifiable consent of a parent or lawful guardian before processing a child's data (s.9(1), Rule 10: check the parent is an identifiable adult using reliable details already held, voluntarily provided, or a virtual token such as DigiLocker).
- No processing likely to have a detrimental effect on a child's well-being (s.9(2)); no tracking, behavioural monitoring or targeted advertising directed at children (s.9(3)).
- Rule 12 and the Fourth Schedule exempt certain classes and purposes. **Part B includes processing "to confirm that a user is not a child"** — relevant to GroundKart's 18+ check.
- Penalty for breaching s.9: up to ₹200 crore.

### 3.6 Rights and duties of Data Principals (s.11–15, Rule 14)

- s.11 summary of personal data processed and processing activities, identities of fiduciaries and processors it was shared with.
- s.12 correction, completion, updating and erasure.
- s.13 grievance redressal: the person must exhaust the fiduciary's mechanism before going to the Board. **Rule 14(3): respond within a reasonable period not exceeding 90 days.**
- s.14 nominate another individual to exercise rights on death or incapacity (Rule 14(4)).
- Rule 14(1): publish prominently how to make a request and the identifiers needed (e.g. username, phone, email).
- s.15 duties of Data Principals, including not registering a false or frivolous grievance and not impersonating; penalty up to ₹10,000.

### 3.7 Significant Data Fiduciary (s.10, Rule 13)

Designated by Central Government notification based on volume and sensitivity, risk to rights, sovereignty, electoral democracy, security and public order. Not automatic. Duties: Data Protection Officer in India, independent data auditor, DPIA and audit every 12 months with report to the Board (Rule 13), algorithmic risk checks, and possible localisation of specified data. GroundKart is unlikely to be designated at its scale (Q-6).

### 3.8 Cross-border transfer (s.16, Rule 15)

Transfers are allowed except to countries the Government restricts by notification; Rule 15 adds requirements the Government may specify for transfers to foreign States. No restricted-country list found as of 10 Nov 2026. Relevant if hosting, storage or email providers process data outside India (Q-7).

### 3.9 Penalties (s.33 and the Schedule)

| Breach | Maximum penalty |
| --- | --- |
| Reasonable security safeguards (s.8(5)) | ₹250 crore |
| Breach intimation to Board or users (s.8(6)) | ₹200 crore |
| Additional obligations for children (s.9) | ₹200 crore |
| Additional obligations of SDFs (s.10) | ₹150 crore |
| Duties of Data Principals (s.15) | ₹10,000 |
| Voluntary undertaking breach (s.32) | up to the penalty for the underlying breach |
| Any other provision of the Act or Rules | ₹50 crore |

Penalties are per instance, set by the Board with regard to nature, gravity, duration, mitigation etc. (s.33(2)). s.33 itself only starts on 13 May 2027.

## 4. Consumer Protection (E-Commerce) Rules 2020 and the 2026 amendment

**Does it cover venue hire?** The Rules apply to "all goods and services bought or sold over digital or electronic network" (r.2(1)(a)) and to marketplace and inventory models. Hiring a venue is a service bought over a digital network, so GroundKart is very likely a **marketplace e-commerce entity** and each venue owner a **seller** (Q-8). Offline payment confirmation does not change that: the contract is formed on the platform.

Duties of every e-commerce entity (r.4), in force today:

- Be a company incorporated in India or a foreign company/office (r.4(1)) → legal entity details needed (DECISIONS_NEEDED D-01).
- Display prominently: legal name, principal geographic address of headquarters and branches, website name and details, **contact details of customer care and the grievance officer** (r.4(2)).
- Grievance mechanism; **grievance officer's name, contact and designation displayed**; acknowledge complaints **within 48 hours** and redress **within one month** (r.4(4), r.4(5)).
- No unfair trade practice (r.4(3)); no manipulation of price (r.4(11)); **no recording of consent automatically, including pre-ticked checkboxes**; consent must be an explicit and affirmative action (**r.4(9)**).
- No cancellation charges unless similar charges are borne by the entity if it cancels unilaterally (r.4(10)).
- Effect refunds within a reasonable period (r.4(12)).

Marketplace duties (r.5), in force today: undertaking from sellers that content is accurate; display **seller details** (name of business, geographic address, customer care number, ratings) "in a clear and accessible manner"; ticket number for each complaint so consumers can track status; information on return, refund, exchange, warranty, delivery, payment modes, grievance redressal mechanism, and **all relevant details for the consumer to make an informed decision at the pre-purchase stage**; explanation of main parameters for ranking. **Seller duties (r.6):** no false reviews; grievance officer; written contract with the marketplace; total price with break-up.

**2026 amendment (from 1 Jan 2027), as summarised by S6 commentators:** wider definition of ranking and sponsored-listing labels; rules on announced price reductions (new r.4(13)); bundled and optional fees restrictions at checkout; **annual dark-pattern self-audits become mandatory** (previously an advisory); stricter seller identification including government-issued identity details of sellers; restrictions on use of consumer information; participation in the National Consumer Helpline convergence process mandatory (r.4(7)); grievance 48 hours / one month retained. We have not read the Gazette text of G.S.R. 789(E) (Q-9).

## 5. Dark Patterns Guidelines 2023 and the 2025 advisory

Apply to all platforms systematically offering goods or services in India, advertisers and sellers. The 13 specified patterns (Annexure 1): **false urgency, basket sneaking, confirm shaming, forced action, subscription trap, interface interference, bait and switch, drip pricing, disguised advertisement, nagging, trick question, SaaS billing, rogue malwares**. The 5 Jun 2025 advisory asked e-commerce platforms to self-audit within three months and give self-declarations; on 20 Nov 2025 PIB reported 26 platforms had done so, and in June 2026 the CCPA passed orders with fines under the Consumer Protection Act, the E-Commerce Rules and the Guidelines (reported; Q-10). "Fake reviews" are not one of the 13 named patterns; they are covered by the E-Commerce Rules (r.4(3), r.6), the BIS IS 19000:2022 standard on online consumer reviews (voluntary), and unfair trade practice under the Consumer Protection Act.

## 6. IT Act, SPDI Rules 2011, Intermediary Rules 2021

- **SPDI Rules 2011 (in force until 13 May 2027):** "sensitive personal data or information" covers passwords, financial information (bank account, card), health, sexual orientation, biometrics. GroundKart holds passwords (hashed) and owner bank account details. Duties: a privacy policy on the website (r.4); written consent for SPDI collection, purpose limitation and option to withdraw (r.5); a Grievance Officer whose name and contact are published, redressing **within one month** (r.5(9)); disclosure only with consent (r.6); reasonable security practices, IS/ISO/IEC 27001 named as one standard (r.8). s.72A IT Act (disclosure in breach of contract) stays.
- **Intermediary Rules 2021:** GroundKart hosts third-party content (owner listings, photos, videos, reviews, ticket text), so it is an intermediary for that content. Duties include publishing rules and regulations, privacy policy and user agreement; informing users not to host unlawful content; a **Grievance Officer** with published contact; acknowledging complaints **within 24 hours** and resolving **within 15 days** (as amended in 2022), with 72 hours for certain removal requests; acting on court or government orders; retaining information for 180 days after removal for investigation (Q-15). The 24-hour/15-day intermediary clock is **stricter** than the 48-hour/one-month consumer clock and the 90-day DPDP clock.
- **CERT-In Directions 2022 (S11, read directly):** report the listed cyber incidents (including data breach, data leak, unauthorised access, website defacement, attacks on servers and databases) to CERT-In **within 6 hours of noticing**; designate a point of contact; synchronise clocks with NTP of NIC or NPL (or traceable sources); **enable logs of all ICT systems and keep them for a rolling 180 days within Indian jurisdiction**; the FAQs allow logs abroad if they can be produced on demand. Non-compliance is punishable under s.70B(7) IT Act.

## 7. Payments (pointer only)

GroundKart currently takes payment offline (bank transfer/UPI/cash confirmed by an admin) and stores no card data. Before online payments are added, check: RBI's framework for payment aggregators and gateways (merchants must not store card credentials; card-on-file tokenisation since 1 Oct 2022); whether GroundKart's collection on behalf of owners makes it a payment aggregator needing authorisation or requires a nodal/escrow arrangement through a licensed PA; GST TCS for e-commerce operators (CGST Act s.52) and record retention under the GST and Income-tax laws and Companies Act s.128 (Q-11, Q-12).

## 8. What applies to GroundKart

**Roles.**

- **GroundKart as Data Fiduciary** for: customers (accounts and bookings), guests (bookings without an account), venue owners (account, verification documents, bank details, listings), referral partners (brokers), admins, and anyone who uses the Contact or Help forms.
- **Venue owners as separate Data Fiduciaries** for the customer details GroundKart passes to them to fulfil a booking (name, phone, email, notes, guest count). The owner decides how to use them at the venue. The Terms should require owners to use customer data only to deliver the booking and to delete it after, and GroundKart should pass only what is needed (Q-5).
- **Brokers** see venue-level and booking-amount data for venues they referred, not customer contact details (verified: `ReferredBookingView` in `backend/app/schemas/partners.py` carries no customer name, phone or email). They are not processors for customer data.
- **Processors (current code):** hosting provider (VPS, e.g. Hostinger per the deploy guide), object storage if S3 is configured, database backups on the same host. No email or SMS provider is integrated yet (password reset links are shared by admins, notifications are in-app only). No payment gateway is integrated (`payments.gateway` defaults to "razorpay" as a label, offline flow only). No analytics, ads, chat widget or tag manager. Fonts are self-hosted (`@fontsource-variable/*`). Third-party embeds: YouTube or Vimeo players, only on venue pages where an owner added a video.
- **Intermediary** for owner listings, photos, videos and reviews.
- **Marketplace e-commerce entity** under the E-Commerce Rules; venue owners are sellers.

**Significant Data Fiduciary?** Not unless notified. Unlikely at current scale. Not in the Third Schedule's 2-crore-user e-commerce class either; the 3-year inactive-erasure rule does not apply by law but is adopted voluntarily as a retention period proposal (D-08).

**Guests (no account).** A guest checkout collects name, email, optional phone and notes. The notice must be shown before submission. Ground: consent with the 18+ declaration, or s.7(a) voluntary provision (Q-4). Guests need a way to exercise rights without an account: the emailed manage link plus the grievance contact.

**Minors using sports venues.** Sports venues are often used by school teams and children, and the seed data even describes coaching for "school children". The owner's decision is that **only adults (18+) may hold accounts or make bookings**. Children may still attend a venue booked by an adult; the booker should not enter children's names or details in notes. We build: an unticked 18+ declaration at sign-up and guest checkout, stored with timestamp and Terms version; Terms and Notice sentences; no date of birth; an admin action to suspend and erase an account found to belong to a minor. **We do not build a parental-consent flow.** Whether a self-declaration is enough is an open question (Q-13), because a minor could still tick the box and s.9 penalties are high. Rule 12 / Fourth Schedule Part B exempts processing "to confirm that a user is not a child", which supports a lightweight check but does not answer whether a checkbox is sufficient.

**Grievance timelines to honour (strictest first).** Intermediary content complaints: acknowledge 24 h, resolve 15 days. Consumer complaints: acknowledge 48 h, resolve one month. SPDI: one month. DPDP data grievances: within 90 days (from May 2027). We implement **acknowledge within 24 hours and resolve within 15 days for content complaints, 48 hours and 30 days for all others**, configurable.

**Log retention to honour.** CERT-In: rolling 180 days, in India. DPDP Rule 6(e) and 8(3): at least one year. We configure **one year (365 days)** for security and audit logs, stored on the India-hosted server.

## 9. Differences from the Rinisha checklist

| # | Checklist says | Primary source says | Impact |
| --- | --- | --- | --- |
| R1 | "13 May 2027: notice, consent, security, breach, children's data and penalties all apply" | Correct per S2/S3, but **SPDI Rules and E-Commerce Rules apply today**, and CERT-In since 2022. Possible 14 May 2027 reading (Q-1). | Checklist under-states today's obligations. |
| R2 | "Data complaints are answered within 90 days at the latest" | Rule 14(3) says within a reasonable period **not exceeding** 90 days, and only from May 2027. SPDI Rules require one month **today**. Intermediary Rules require 24 h acknowledgement / 15 days for content complaints. | We use the stricter timelines. |
| R3 | "Access logs kept for at least 1 year" (Rule 6) | Rule 6(e) says logs and personal data for one year **unless another law requires otherwise**; CERT-In requires **180 days rolling within India** (today). | Keep 1 year, in India. |
| R4 | "Cyber incidents reported to CERT-In within 6 hours" | Correct (S11), and in force **since 27 Jun 2022**, not 2027. Applies to the listed incident types. | P0, not P1. |
| R5 | "Inform the Data Protection Board, with a detailed report within 72 hours" | Rule 7: initial intimation **without delay**, detailed report within 72 hours **of becoming aware**, extendable by the Board on written request. | Two-step Board notice in the breach plan. |
| R6 | Check 7 implies every site must ask for age/DOB and get parental consent | s.9 applies only when a fiduciary processes children's data. An adults-only service with an age gate is a design choice, and Rule 12 Fourth Schedule Part B exempts age-confirmation processing. Sufficiency of a self-declaration is untested. | 7.2 marked Not applicable by design; Q-13. |
| R7 | "Large platforms: erase inactive users' data after 3 years" | Third Schedule applies only to e-commerce and social media with **≥2 crore registered users** and gaming with **≥50 lakh**; access to the user account and virtual tokens are carved out. | Does not bind GroundKart by law. |
| R8 | Cookie banner with Accept/Reject/Choose (4.1) | DPDP has **no cookie-specific rule** (the checklist says so too). A banner is only needed if non-essential trackers are used. | GroundKart uses none, so 4.1 and 4.2 are met by not tracking; we record why (test proves no third-party requests on first load). |
| R9 | Penalty table | Matches the Schedule (S1). Checklist omits the ₹10,000 penalty on Data Principals and that penalties are per instance and only from 13 May 2027. | None. |
| R10 | "Dark patterns: ... fake reviews" (6.5) | Fake reviews are not one of the 13 specified dark patterns; they fall under E-Commerce Rules r.4(3)/r.6 and unfair trade practice. | Same fix (verified reviews). |
| R11 | Checklist does not mention the **E-Commerce (Amendment) Rules 2026** (in force 1 Jan 2027) | S6 | Adds annual dark-pattern audit, bundled-fee and ranking disclosures, seller ID details. Added to the calendar. |
| R12 | Checklist does not mention the **Intermediary Rules 2021** grievance clock | S10 | 24 h / 15 days for user-content complaints. |
| R13 | Checklist does not mention the **Eighth Schedule language** right in s.5(3) | S1 | Notice must be available in English or any Eighth Schedule language on request; we ship English and Hindi (D-06). |
| R14 | Checklist is "as of October 2026" | S.O. 5458(E) (6 Oct 2026) reported; not mentioned. | Q-2. |
| R15 | 6.1 asks for "Shipping/Delivery and Warranty" policies | GroundKart sells a service; there is no shipping, return or warranty. E-Commerce r.5(3) asks for return, refund, exchange, warranty, delivery information "as applicable". | We publish Refund and Cancellation, and state that shipping, exchange and warranty do not apply. |
| R16 | 6.4 "Product country of origin" | Applies to imported goods (r.5(3)(c), and r.4 as amended). Venue hire has no country of origin. | Not applicable; we show the mandatory service details instead (venue address, owner business name, inclusions, rules). |

## 10. Questions for a lawyer

1. **Q-1 Commencement dates.** Is the operative publication date 13 or 14 November 2025, i.e. do the core duties start on 13 or 14 May 2027, and Rule 4 on 13 or 14 November 2026?
2. **Q-2 S.O. 5458(E).** What exactly did the Removal of Difficulties Order of 6 Oct 2026 change in s.9(1) and s.10(2)(c)(ii), and does it affect an adults-only platform?
3. **Q-3 Legacy notice.** Does s.5(2) require a fresh notice to every user who signed up before 13 May 2027 (we plan an in-app notice and re-acceptance banner)?
4. **Q-4 Ground for booking data.** For account holders and guests, should booking data rest on consent (s.6) or on legitimate use s.7(a) (voluntarily provided for a specified purpose)? The choice changes what withdrawal does to an active booking.
5. **Q-5 Owners as fiduciaries.** Are venue owners independent Data Fiduciaries for the customer details we pass to them, or our processors? What contract terms should bind them (purpose limitation, deletion after the event, breach notice)?
6. **Q-6 SDF risk.** Is there any realistic route to SDF designation for a venue marketplace at our scale, and should we prepare a DPIA anyway?
7. **Q-7 Hosting location.** Must the database, backups and logs stay in India (CERT-In logs within Indian jurisdiction; possible Rule 15 restrictions), and are there contractual requirements for a VPS provider?
8. **Q-8 E-Commerce Rules scope.** Confirm GroundKart is a marketplace e-commerce entity for venue hire with offline payment, and which seller details must be shown before booking (owner's legal name, address, phone, GSTIN?).
9. **Q-9 2026 amendment.** Which provisions of G.S.R. 789(E) apply to a services marketplace, especially bundled/optional fees, seller government ID disclosure, annual dark-pattern audit and NCH convergence, and in what form?
10. **Q-10 Dark-pattern self-declaration.** Should GroundKart publish a self-declaration of its dark-pattern self-audit, and in what form?
11. **Q-11 Payments.** Before online payments: do we need a PA licence or a licensed PA's nodal account for collecting on behalf of owners? Any TCS/GST registration duty as an e-commerce operator?
12. **Q-12 Retention for tax and accounts.** Which periods apply to booking, payment, refund, payout and commission records (GST, Income-tax, Companies Act s.128), so the erasure service can keep them with a recorded reason?
13. **Q-13 Adults-only design.** Is an unticked "I confirm I am 18 years or older" declaration, with no date of birth, enough to treat GroundKart as not processing children's data under s.9 and Rule 10, given that a minor could still tick the box? What should we do on discovering a minor's account (we plan suspend and erase on request)? Do bookings for children's events (a birthday party, a school team) entered by an adult raise s.9 issues if the booker mentions the children in notes?
14. **Q-14 SPDI today.** Until 13 May 2027, do we need written consent for collecting passwords and owner bank details under SPDI r.5, and is the checkbox at sign-up enough?
15. **Q-15 Intermediary status.** Confirm GroundKart is an intermediary for owner listings and reviews, the applicable grievance timelines (24 h / 15 days, 72 h for some content), and the 180-day retention after takedown.
16. **Q-16 Identity documents.** Owners upload Aadhaar, PAN, passport or similar. Are there Aadhaar Act restrictions on storing Aadhaar numbers or copies (masking to last 4 digits, offline verification), and should we stop accepting Aadhaar entirely?
17. **Q-17 Grievance Officer.** Can one person act as the DPDP contact (s.8(9)), the E-Commerce grievance officer, the Intermediary Rules grievance officer and the SPDI grievance officer? Must they be resident in India?
18. **Q-18 Governing law and jurisdiction.** Which city's courts, and should consumer disputes reference the consumer commissions and the National Consumer Helpline explicitly?
19. **Q-19 Language.** Is an English and Hindi notice with "other Eighth Schedule languages on request within N days" sufficient for s.5(3)?
20. **Q-20 Breach thresholds.** Which incidents trigger the Board, users and CERT-In respectively (DPDP has no harm threshold; CERT-In lists incident types)? Can one form serve both?
21. **Q-21 Venue videos.** Owner-added YouTube or Vimeo embeds send the visitor's IP to those companies when the player loads. Is a click-to-load player with a one-line notice enough, or is consent needed?
22. **Q-22 Cancellation charges.** E-Commerce r.4(10) forbids cancellation charges unless similar charges are borne by the entity when it cancels. Our tiers keep 50% or 100% when the customer cancels late, and refund 100% when the venue owner cancels (`backend/app/modules/booking/refund_service.py`, tier `full_refund_owner_cancellation`). Is that compliant, or must a reciprocal compensation be offered?
