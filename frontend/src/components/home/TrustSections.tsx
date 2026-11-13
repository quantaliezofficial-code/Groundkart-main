import React, { useId, useRef, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  ArrowRight,
  BadgeCheck,
  CalendarClock,
  CheckCircle2,
  Clock,
  ExternalLink,
  LifeBuoy,
  MapPin,
  ReceiptText,
  ShieldCheck,
  Star,
  Undo2,
  Wallet,
} from 'lucide-react';
import { api } from '../../lib/api/client';
import { useLegalProfile } from '../../lib/legal';
import { DEFAULT_HOMEPAGE, type HomepageContent } from '../../lib/homepageContent';

type Copy = { title: string; intro: string };

/**
 * The trust sections of the homepage. Every sentence here describes
 * something the product actually does today; the numbers (hold time,
 * refund tiers) come from the live booking configuration, not from copy,
 * so they cannot drift from what checkout enforces.
 */

function formatHold(minutes: number | undefined): string {
  if (!minutes) return 'a set time';
  if (minutes % 60 === 0) {
    const h = minutes / 60;
    return `${h} hour${h === 1 ? '' : 's'}`;
  }
  return `${minutes} minutes`;
}

function linkTo(onNavigate: (p: string) => void, path: string) {
  return (e: React.MouseEvent) => {
    e.preventDefault();
    onNavigate(path);
  };
}

/* ------------------------------------------------------------------ */
/* Booking protections                                                 */
/* ------------------------------------------------------------------ */

export function BookingProtections({ onNavigate, copy = DEFAULT_HOMEPAGE.protections }: { onNavigate: (p: string) => void; copy?: Copy }) {
  const { data: profile } = useLegalProfile();
  const bt = profile?.booking_terms;

  const items = [
    {
      icon: CalendarClock,
      title: 'Your date is held while you pay',
      body: `Sending a request holds the slot for ${formatHold(bt?.hold_minutes)}, so nobody else can book it while payment is arranged.`,
    },
    {
      icon: Wallet,
      title: 'No card details on the site',
      body: 'You pay by UPI, bank transfer or cash, as agreed for the venue. GroundKart never asks for your card number.',
    },
    {
      icon: Undo2,
      title: 'Refund rules shown before you book',
      body: bt
        ? `Cancel ${bt.full_refund_hours} hours or more ahead for a full refund, or ${bt.partial_refund_hours} hours ahead for ${bt.partial_refund_percent}%. If the venue cancels, you get 100% back.`
        : 'The refund you would get is shown at checkout and on your booking. If the venue cancels, you get 100% back.',
      link: { label: 'Refund policy', path: '/refunds' },
    },
    {
      icon: ShieldCheck,
      title: 'Owners verify who they are',
      body: 'Every owner completes an identity check before listing, and our team reviews each listing before it goes live.',
    },
    {
      icon: BadgeCheck,
      title: 'Reviews only from real bookings',
      body: 'Only customers whose booking at that venue was completed can leave a review, and ratings count those reviews only.',
    },
    {
      icon: LifeBuoy,
      title: 'A named person answers',
      body: 'Every message gets a ticket number and a reply within 48 hours. Complaints can go to our Grievance Officer.',
      link: { label: 'How complaints work', path: '/grievance' },
    },
  ];

  return (
    <section aria-labelledby="protections-heading" className="mx-auto mt-20 max-w-7xl px-4 sm:mt-28 sm:px-6 lg:px-8" data-testid="booking-protections">
      <div className="grid grid-cols-1 gap-10 lg:grid-cols-12">
        <div className="lg:col-span-4">
          <h2 id="protections-heading" className="font-display text-3xl font-semibold leading-tight text-ink sm:text-4xl">
            {copy.title}
          </h2>
          <p className="mt-3 max-w-sm text-[15px] leading-relaxed text-on-surface-variant">{copy.intro}</p>
        </div>
        <ul className="grid grid-cols-1 gap-x-8 gap-y-8 sm:grid-cols-2 lg:col-span-8">
          {items.map(({ icon: Icon, title, body, link }) => (
            <li key={title} className="flex gap-4">
              <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-pitch/[0.06] text-pitch">
                <Icon size={19} aria-hidden="true" />
              </span>
              <div className="min-w-0">
                <h3 className="text-[16px] font-semibold text-ink">{title}</h3>
                <p className="mt-1.5 text-[15px] leading-relaxed text-on-surface-variant">{body}</p>
                {link ? (
                  <a
                    href={link.path}
                    onClick={linkTo(onNavigate, link.path)}
                    className="mt-2 inline-flex items-center gap-1 text-sm font-semibold text-pitch underline-offset-4 hover:underline"
                  >
                    {link.label} <ArrowRight size={14} aria-hidden="true" />
                  </a>
                ) : null}
              </div>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}

/* ------------------------------------------------------------------ */
/* Guided booking preview                                              */
/* ------------------------------------------------------------------ */

const PREVIEW_STEPS = [
  {
    key: 'search',
    label: 'Search',
    title: 'Search and compare',
    body: 'Filter by city, date, guests and budget. Each listing shows real photos, what the price covers, capacity and house rules.',
  },
  {
    key: 'request',
    label: 'Request',
    title: 'Request your date',
    body: 'Pick a slot or a full day and see the full price before you send. Nothing is pre-ticked and there are no hidden fees.',
  },
  {
    key: 'pay',
    label: 'Pay',
    title: 'Pay the way you agreed',
    body: 'Our team shares payment details. Pay by UPI, bank transfer or cash while your slot is held for you.',
  },
  {
    key: 'confirmed',
    label: 'Confirmed',
    title: 'Get a confirmed booking',
    body: 'Once the payment is recorded, the booking turns confirmed in My Bookings, with a reference number you can quote.',
  },
] as const;

function PreviewPanel({ step, holdText }: { step: (typeof PREVIEW_STEPS)[number]['key']; holdText: string }) {
  const card = 'rounded-2xl bg-white p-5 shadow-[0_20px_50px_-30px_rgba(6,40,29,0.45)] ring-1 ring-ink/5';
  if (step === 'search') {
    return (
      <div className={`${card} p-0 overflow-hidden`}>
        <div className="relative aspect-[16/10]">
          <img
            src="/img/photos/placeholder-800.webp"
            srcSet="/img/photos/placeholder-400.webp 400w, /img/photos/placeholder-800.webp 800w"
            sizes="(min-width: 1024px) 420px, 90vw"
            alt="An outdoor clay court with floodlights, lined with palm trees"
            loading="lazy"
            decoding="async"
            width={800}
            height={500}
            className="absolute inset-0 h-full w-full object-cover"
          />
          <span className="absolute left-3 top-3 rounded-full bg-white/95 px-2.5 py-1 text-[12px] font-semibold text-pitch">Sample listing</span>
        </div>
        <div className="p-5">
          <p className="font-semibold text-ink">Floodlit sports court</p>
          <p className="mt-1 flex items-center gap-1 text-sm text-on-surface-variant">
            <MapPin size={14} aria-hidden="true" /> Your city
          </p>
          <div className="mt-4 flex flex-wrap gap-2 text-[12px] font-semibold text-pitch">
            {['Up to 12 players', 'Floodlights', 'Parking'].map((t) => (
              <span key={t} className="rounded-full bg-mist px-2.5 py-1">
                {t}
              </span>
            ))}
          </div>
        </div>
      </div>
    );
  }
  if (step === 'request') {
    return (
      <div className={card}>
        <p className="text-sm font-semibold text-ink">Price breakup</p>
        <dl className="mt-3 space-y-2 text-[15px]">
          {[
            ['Venue charge', 'As listed'],
            ['Platform fee', '₹0'],
            ['Taxes', 'Shown at checkout'],
          ].map(([k, v]) => (
            <div key={k} className="flex justify-between gap-4">
              <dt className="text-on-surface-variant">{k}</dt>
              <dd className="font-semibold text-ink">{v}</dd>
            </div>
          ))}
          <div className="flex justify-between gap-4 border-t border-ink/10 pt-2">
            <dt className="font-semibold text-ink">Total</dt>
            <dd className="font-semibold text-ink">Before you send</dd>
          </div>
        </dl>
        <div className="mt-4 flex items-start gap-2 rounded-xl bg-mist p-3 text-[13px] text-pitch">
          <span aria-hidden="true" className="mt-0.5 h-4 w-4 shrink-0 rounded border border-pitch/40 bg-white" />
          You tick the boxes yourself. Nothing is pre-selected.
        </div>
      </div>
    );
  }
  if (step === 'pay') {
    return (
      <div className={card}>
        <div className="flex items-center justify-between gap-3">
          <p className="text-sm font-semibold text-ink">Booking request</p>
          <span className="inline-flex items-center gap-1 rounded-full bg-marigold/20 px-2.5 py-1 text-[12px] font-semibold text-pitch">
            <Clock size={13} aria-hidden="true" /> Held for {holdText}
          </span>
        </div>
        <p className="mt-4 text-[13px] font-semibold uppercase tracking-wide text-on-surface-variant">Ways to pay</p>
        <ul className="mt-2 grid grid-cols-3 gap-2 text-center text-sm font-semibold text-pitch">
          {['UPI', 'Bank transfer', 'Cash'].map((m) => (
            <li key={m} className="rounded-xl bg-mist px-2 py-3">
              {m}
            </li>
          ))}
        </ul>
        <p className="mt-4 text-[13px] leading-relaxed text-on-surface-variant">No card details are asked for on GroundKart.</p>
      </div>
    );
  }
  return (
    <div className={card}>
      <div className="flex items-center gap-3">
        <span className="flex h-10 w-10 items-center justify-center rounded-full bg-pitch text-marigold">
          <CheckCircle2 size={20} aria-hidden="true" />
        </span>
        <div>
          <p className="font-semibold text-ink">Booking confirmed</p>
          <p className="text-sm text-on-surface-variant">Payment recorded by our team</p>
        </div>
      </div>
      <dl className="mt-5 space-y-2 text-[15px]">
        <div className="flex justify-between gap-4">
          <dt className="text-on-surface-variant">Reference</dt>
          <dd className="font-mono text-[14px] font-semibold text-ink">GK-XXXXXX</dd>
        </div>
        <div className="flex justify-between gap-4">
          <dt className="text-on-surface-variant">Status</dt>
          <dd className="font-semibold text-pitch">Confirmed</dd>
        </div>
      </dl>
      <p className="mt-4 flex items-center gap-1.5 text-[13px] text-on-surface-variant">
        <ReceiptText size={14} aria-hidden="true" /> Cancellation terms stay on the booking.
      </p>
    </div>
  );
}

export function GuidedBookingPreview({ copy = DEFAULT_HOMEPAGE.preview }: { copy?: Copy }) {
  const [active, setActive] = useState(0);
  const tabs = useRef<(HTMLButtonElement | null)[]>([]);
  const baseId = useId();
  const { data: profile } = useLegalProfile();
  const holdText = formatHold(profile?.booking_terms.hold_minutes);

  const onKey = (e: React.KeyboardEvent) => {
    const last = PREVIEW_STEPS.length - 1;
    let next = active;
    if (e.key === 'ArrowRight' || e.key === 'ArrowDown') next = active === last ? 0 : active + 1;
    else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') next = active === 0 ? last : active - 1;
    else if (e.key === 'Home') next = 0;
    else if (e.key === 'End') next = last;
    else return;
    e.preventDefault();
    setActive(next);
    tabs.current[next]?.focus();
  };

  const step = PREVIEW_STEPS[active];

  return (
    <section aria-labelledby="how-heading" className="mx-auto mt-20 max-w-7xl px-4 sm:mt-28 sm:px-6 lg:px-8" data-testid="booking-preview">
      <div className="overflow-hidden rounded-3xl bg-mist ring-1 ring-ink/5">
        <div className="grid grid-cols-1 gap-10 p-6 sm:p-10 lg:grid-cols-12 lg:p-14">
          <div className="lg:col-span-6">
            <h2 id="how-heading" className="font-display text-3xl font-semibold leading-tight text-ink sm:text-4xl">
              {copy.title}
            </h2>
            <p className="mt-3 max-w-md text-[15px] leading-relaxed text-on-surface-variant">{copy.intro}</p>

            <div role="tablist" aria-label="Booking steps" aria-orientation="vertical" className="mt-8 space-y-2" onKeyDown={onKey}>
              {PREVIEW_STEPS.map((s, i) => {
                const selected = i === active;
                return (
                  <button
                    key={s.key}
                    ref={(el) => {
                      tabs.current[i] = el;
                    }}
                    role="tab"
                    id={`${baseId}-tab-${s.key}`}
                    aria-selected={selected}
                    aria-controls={`${baseId}-panel`}
                    tabIndex={selected ? 0 : -1}
                    onClick={() => setActive(i)}
                    className={`flex w-full items-start gap-4 rounded-2xl px-4 py-4 text-left transition-colors cursor-pointer ${
                      selected ? 'bg-white shadow-sm ring-1 ring-ink/5' : 'hover:bg-white/60'
                    }`}
                  >
                    <span
                      className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-sm font-semibold tabular ${
                        selected ? 'bg-pitch text-marigold' : 'bg-pitch/10 text-pitch'
                      }`}
                    >
                      {i + 1}
                    </span>
                    <span className="min-w-0">
                      <span className="block text-[16px] font-semibold text-ink">{s.title}</span>
                      {selected ? <span className="mt-1 block text-[15px] leading-relaxed text-on-surface-variant">{s.body}</span> : null}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>

          <div
            role="tabpanel"
            id={`${baseId}-panel`}
            aria-labelledby={`${baseId}-tab-${step.key}`}
            className="flex items-center lg:col-span-6"
          >
            <div key={step.key} className="gk-rise mx-auto w-full max-w-[420px]">
              <PreviewPanel step={step.key} holdText={holdText} />
              <p className="mt-3 text-center text-[12px] text-on-surface-variant">Illustration of the booking screens</p>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

/* ------------------------------------------------------------------ */
/* Verified reviews                                                    */
/* ------------------------------------------------------------------ */

interface RecentReview {
  id: string;
  venue_name: string;
  venue_slug: string | null;
  venue_city: string | null;
  user_name: string;
  rating: number;
  content: string;
  created_at: string | null;
  verified_booking: boolean;
}

export function VerifiedReviews({ onOpenVenue, copy = DEFAULT_HOMEPAGE.reviews }: { onOpenVenue: (slug: string) => void; copy?: Copy }) {
  const { data: reviews = [] } = useQuery({
    queryKey: ['recent-verified-reviews'],
    queryFn: () => api.get<RecentReview[]>('/api/v1/reviews/recent', { query: { limit: 6 }, skipAuth: true }),
    staleTime: 5 * 60 * 1000,
  });
  const shown = reviews.filter((r) => r.verified_booking).slice(0, 3);
  // No verified reviews yet: show nothing rather than filler.
  if (shown.length === 0) return null;

  return (
    <section aria-labelledby="reviews-heading" className="mx-auto mt-20 max-w-7xl px-4 sm:mt-28 sm:px-6 lg:px-8" data-testid="verified-reviews">
      <div className="mb-8 max-w-2xl">
        <h2 id="reviews-heading" className="font-display text-3xl font-semibold text-ink sm:text-4xl">
          {copy.title}
        </h2>
        <p className="mt-2 text-[15px] text-on-surface-variant">{copy.intro}</p>
      </div>
      <ul className="grid grid-cols-1 gap-6 md:grid-cols-3">
        {shown.map((r) => (
          <li key={r.id} className="flex flex-col rounded-2xl bg-chalk p-6 ring-1 ring-ink/5">
            <div className="flex items-center justify-between gap-3">
              <div className="flex items-center gap-0.5" role="img" aria-label={`${r.rating} out of 5`}>
                {Array.from({ length: 5 }).map((_, i) => (
                  <Star
                    key={i}
                    size={15}
                    aria-hidden="true"
                    className={i < r.rating ? 'fill-marigold text-marigold' : 'text-ink/15'}
                  />
                ))}
              </div>
              <span className="inline-flex shrink-0 items-center gap-1 rounded-full bg-pitch/[0.06] px-2.5 py-1 text-[12px] font-semibold text-pitch">
                <BadgeCheck size={13} aria-hidden="true" /> Verified booking
              </span>
            </div>
            <blockquote className="mt-4 flex-1 text-[15px] leading-relaxed text-ink">{r.content}</blockquote>
            <div className="mt-5 min-w-0 border-t border-ink/10 pt-4">
              <p className="text-sm font-semibold text-ink">{r.user_name}</p>
              {r.venue_slug ? (
                <button
                  type="button"
                  onClick={() => onOpenVenue(r.venue_slug as string)}
                  className="block max-w-full truncate text-left text-[13px] text-on-surface-variant underline-offset-4 hover:underline cursor-pointer"
                >
                  {r.venue_name}
                  {r.venue_city ? `, ${r.venue_city}` : ''}
                </button>
              ) : (
                <p className="truncate text-[13px] text-on-surface-variant">{r.venue_name}</p>
              )}
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}

/* ------------------------------------------------------------------ */
/* Founder and team                                                    */
/* ------------------------------------------------------------------ */

export function FounderStory({ onNavigate, founder = DEFAULT_HOMEPAGE.founder }: { onNavigate: (p: string) => void; founder?: HomepageContent['founder'] }) {
  const initials = founder.name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((w) => w[0]?.toUpperCase())
    .join('');
  const external = founder.link_url.startsWith('https://');
  return (
    <section aria-labelledby="team-heading" className="mx-auto mt-20 max-w-7xl px-4 sm:mt-28 sm:px-6 lg:px-8" data-testid="founder-story">
      <div className="grid grid-cols-1 overflow-hidden rounded-3xl bg-pitch text-chalk lg:grid-cols-12">
        <div className="p-7 sm:p-10 lg:col-span-7 lg:p-14">
          <p className="text-[13px] font-semibold uppercase tracking-[0.18em] text-marigold">{founder.eyebrow}</p>
          <h2 id="team-heading" className="mt-3 font-display text-3xl font-semibold leading-tight sm:text-4xl">
            {founder.title}
          </h2>
          <p className="mt-5 max-w-xl whitespace-pre-line text-[16px] leading-relaxed text-chalk/85">{founder.body}</p>

          <div className="mt-8 flex items-center gap-4">
            <span
              aria-hidden="true"
              className="flex h-14 w-14 shrink-0 items-center justify-center rounded-full bg-marigold font-display text-xl font-semibold text-pitch"
            >
              {initials}
            </span>
            <div>
              <p className="text-[17px] font-semibold">{founder.name}</p>
              <p className="text-sm text-chalk/70">{founder.role}</p>
            </div>
          </div>

          <div className="mt-8 flex flex-wrap gap-3">
            <a
              href="/contact"
              onClick={linkTo(onNavigate, '/contact')}
              className="inline-flex items-center gap-2 rounded-full bg-marigold px-5 py-2.5 text-sm font-semibold text-pitch hover:brightness-105"
            >
              Talk to us <ArrowRight size={16} aria-hidden="true" />
            </a>
            {founder.link_url ? (
              <a
                href={founder.link_url}
                {...(external ? { target: '_blank', rel: 'noopener noreferrer' } : { onClick: linkTo(onNavigate, founder.link_url) })}
                className="inline-flex items-center gap-2 rounded-full border border-chalk/25 px-5 py-2.5 text-sm font-semibold text-chalk hover:bg-chalk/10"
              >
                {founder.link_label || founder.link_url} {external ? <ExternalLink size={15} aria-hidden="true" /> : null}
              </a>
            ) : null}
          </div>
        </div>

        <div className="border-t border-chalk/10 bg-ink/40 p-7 sm:p-10 lg:col-span-5 lg:border-l lg:border-t-0 lg:p-14">
          <h3 className="text-sm font-semibold uppercase tracking-wide text-chalk/60">Founder's background</h3>
          <ol className="mt-6 space-y-6 border-l border-chalk/15 pl-6">
            {founder.timeline.map((t) => (
              <li key={`${t.years}-${t.org}`} className="relative">
                <span aria-hidden="true" className="absolute -left-[29px] top-1.5 h-2.5 w-2.5 rounded-full bg-marigold" />
                <p className="text-[13px] font-semibold text-marigold tabular">{t.years}</p>
                <p className="mt-0.5 text-[16px] font-semibold">{t.org}</p>
                <p className="mt-1 text-[15px] leading-relaxed text-chalk/75">{t.role}</p>
              </li>
            ))}
          </ol>
        </div>
      </div>
    </section>
  );
}
