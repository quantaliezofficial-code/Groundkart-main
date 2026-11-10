# GroundKart business strategy

*Working document, November 2026. Owner: Quantaliez.*

## 1. What GroundKart is

A marketplace where people find and book a venue for an occasion — a cricket ground for Sunday, a banquet hall for a wedding, a farmhouse for a birthday, a meeting room for an offsite — and where venue owners get bookings without running their own website, calendar or payment follow-up.

The product today: searchable listings with photos, pricing units (hour / half day / day), capacity and house rules; date and slot availability; booking requests that hold a slot; offline payment (UPI, bank transfer, cash) confirmed by the GroundKart team; owner dashboard for listings, calendars, blocked dates and payouts; admin console for review, payments, refunds, payouts, records; and referral partners who bring venue owners on board.

## 2. Market and competitors

The Indian venue market is split by occasion, and the incumbents each own one slice:

| Segment | Typical players | How they earn | Gap GroundKart can use |
|---|---|---|---|
| Sports turfs and courts | Playo, Hudle, Turf Town, KheloMore | Commission per booking, plus software for venue owners | Sports-only; no weddings, parties or corporate use of the same grounds |
| Weddings and banquets | WedMeGood, Weddingz, VenueLook, ShaadiSaga | Listing subscriptions and paid leads | Lead-based: the customer still negotiates by phone; no live availability, no booking record |
| Hourly spaces (global) | Peerspace, Giggster, Tagvenue | Service fee on each booking, typically charged to the host and the guest | Not present in Tier 2 Indian cities |

Two observations matter most:

1. **Many venues serve several occasions.** A farmhouse hosts weddings, birthdays and corporate offsites; a cricket ground hosts tournaments and company sports days. No one lists them across occasions.
2. **Tier 2 cities are under-served.** Large platforms concentrate on metros. In cities like Lucknow, venue discovery still runs on phone calls, WhatsApp and local brokers.

## 3. Positioning

> **"Every kind of venue, one booking record."**

- For customers: compare real options for any occasion, see open dates, and get a booking that is written down — reference number, amount, cancellation terms.
- For owners: free listing, a calendar that stops double bookings, and a recorded payout trail.
- Start city: **Lucknow**, then neighbouring Tier 2 cities (Kanpur, Prayagraj, Varanasi), then metros.

Be honest in all copy. The site does not claim instant confirmation, invented review counts or "verified" badges that are not backed by an actual check. Trust is the product.

## 4. Revenue model

| Stream | Now | Later |
|---|---|---|
| Booking commission (default 10%, set in *Rules and fees*) | ✅ live | Tiered by category (sports lower, weddings higher) |
| Featured placement on homepage and search | Admin-curated now (Homepage venues, Banners) | Paid placement packages for owners |
| Owner software subscription (calendar, multi-venue) | — | For owners who also take direct bookings |
| Online payment convenience fee | — | When online payments are added |
| Event add-ons (decor, catering, photography leads) | — | Partner commission |

Unit economics to watch per city: average booking value, commission rate, partner commission, and the cost of the ops team confirming offline payments.

## 5. Supply growth: referral partners

Supply is the hard side of this marketplace. The fastest route in Tier 2 India is the people who already know the owners: event planners, decorators, property brokers, sports coaches.

How the partner programme works (built into the product):

- Partners are added only by the admin team; the super admin sets each partner's rate.
- Each partner gets a code and a listing link. Owners enter the code on the first step of listing.
- The partner earns a percentage of every **paid** booking at that venue — either of the booking amount or of GroundKart's commission (chosen per partner).
- Earnings become payable after the event date; refunds reverse them automatically.
- Partners see their venues, review status, bookings, money received and their wallet in their own dashboard, and can export everything.

Suggested starting terms:

| Partner type | Basis | Rate |
|---|---|---|
| Standard field partner | Booking amount | 2% |
| High-volume partner (10+ live venues) | Booking amount | 3% |
| Partner bringing premium wedding venues | GroundKart commission | 20–25% |

Basing a partner on *GroundKart's commission* protects margin when booking values are high; basing on *booking amount* is simpler to explain to field partners. Review rates every quarter using the *Partner commissions* export.

## 6. Demand growth

1. **Search pages that rank.** Category and city pages (`/categories/sports`, `/search?city=Lucknow`) with real listings. Each venue page has structured data and its own share preview.
2. **WhatsApp sharing.** Most venue decisions in India are made in family and office WhatsApp groups. Every venue link now shows its own photo, price and city when shared.
3. **Seasonal banners.** Wedding season (Oct–Feb), summer cricket, Diwali office parties, New Year. Schedule them ahead in *Banners*.
4. **Corporate accounts.** HR teams booking offsites and sports days repeatedly: offer an account manager and monthly invoicing once volume justifies it.

## 7. Operations

Daily in the admin console:

1. **Approval queue** — review new listings and owner verifications within one working day.
2. **Bookings** — confirm offline payments as they arrive; the booking and the partner commission are recorded together.
3. **Support tickets** — disputes and booking questions.

Weekly: owner payouts; partner payouts (*Referral partners → Record payout*); download the booking register for accounts.

Monthly: export *Booking register*, *Payments*, *Owner payouts*, *Partner commissions* and *Partner payouts* for reconciliation and GST filing. Every export is itself recorded in the audit log.

## 8. Metrics

| Metric | Why it matters |
|---|---|
| Live venues per city, by category | Supply depth |
| Search → booking request rate | Is the catalogue relevant |
| Request → paid rate, and time to confirm | Ops speed; offline payment friction |
| Gross booking value and net revenue | Business health |
| Cancellation and refund rate | Trust and policy fit |
| Venues and paid bookings per partner | Partner programme ROI |
| Repeat customers (90 days) | Retention |

## 9. Roadmap

**Next 90 days**
- Launch in Lucknow with 100+ live venues across sports, banquet, farmhouse and corporate.
- Recruit 10–15 referral partners.
- Fix the review SLA at under 24 hours.

**3–6 months**
- Online payments (gateway with UPI) — removes the manual confirmation step.
- WhatsApp notifications for owners and customers.
- Paid featured placements.

**6–12 months**
- Second and third cities.
- Owner subscription for multi-venue operators.
- Event add-on partners (decor, catering).

## 10. Risks

| Risk | Mitigation |
|---|---|
| Owners take customers off-platform | Keep the value on-platform: calendar, recorded payments, dispute help, payout record |
| Offline payment slows confirmation | Clear SLA now; online payments next |
| Partner disputes over attribution | Code fixed at listing; only admins can change it; every change is in the venue's history |
| Fake or poor listings | Owner verification and listing review before publish |
| Seasonality | Mix of sports (year-round) and weddings (seasonal) |
