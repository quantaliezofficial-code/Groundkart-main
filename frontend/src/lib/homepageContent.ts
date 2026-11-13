import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from './api/client';

/**
 * Homepage copy and images. The super admin edits overrides in
 * Admin › Website (backend: app/modules/site/content.py); anything not
 * overridden falls back to these defaults, so "Reset" means "back to this
 * file". Text is always rendered as plain text, never as HTML.
 *
 * Promises with numbers (hold time, refund tiers, platform fee) are not
 * here on purpose: the page reads them from the live booking rules.
 */

export interface OccasionItem {
  key: string;
  label: string;
  /** Value understood by the search page's category filter. */
  category: string;
  image_url: string;
  alt: string;
}

export interface TimelineItem {
  years: string;
  org: string;
  role: string;
}

export interface FaqItem {
  q: string;
  a: string;
}

export interface HomepageContent {
  hero: {
    eyebrow: string;
    title: string;
    title_highlight: string;
    subtitle: string;
    image_url: string;
    image_alt: string;
    show_occasion_chips: boolean;
  };
  occasions: OccasionItem[];
  sections: {
    occasions: boolean;
    protections: boolean;
    preview: boolean;
    reviews: boolean;
    owners: boolean;
    partners: boolean;
    founder: boolean;
    faq: boolean;
    closing: boolean;
  };
  protections: { title: string; intro: string };
  preview: { title: string; intro: string };
  reviews: { title: string; intro: string };
  owners: { title: string; bullets: string[]; image_url: string; image_alt: string; cta_label: string };
  founder: {
    eyebrow: string;
    title: string;
    body: string;
    name: string;
    role: string;
    link_url: string;
    link_label: string;
    timeline: TimelineItem[];
  };
  faq: FaqItem[];
  closing: { title: string; cta_label: string };
}

export type HomepageOverrides = {
  [K in keyof HomepageContent]?: HomepageContent[K] extends unknown[] ? HomepageContent[K] : Partial<HomepageContent[K]>;
};

/** Built-in photo sets with responsive sizes (public/img/photos). */
export const RESPONSIVE_IMAGES: Record<string, { srcSet: string; width: number; height: number }> = {
  '/img/photos/hero-1600.webp': {
    srcSet: '/img/photos/hero-960.webp 960w, /img/photos/hero-1600.webp 1600w, /img/photos/hero-2400.webp 2400w',
    width: 1600,
    height: 900,
  },
  '/img/photos/owners-960.webp': { srcSet: '/img/photos/owners-560.webp 560w, /img/photos/owners-960.webp 960w', width: 960, height: 720 },
  ...Object.fromEntries(
    ['weddings', 'corporate', 'sports', 'parties', 'resorts', 'outdoor'].map((k) => [
      `/img/photos/occ-${k}-720.webp`,
      { srcSet: `/img/photos/occ-${k}-400.webp 400w, /img/photos/occ-${k}-720.webp 720w`, width: 720, height: 900 },
    ]),
  ),
};

/** Built-in images the super admin can pick without uploading anything. */
export const BUILT_IN_IMAGES: { url: string; label: string }[] = [
  { url: '/img/photos/hero-1600.webp', label: 'Hero: wedding hall' },
  { url: '/img/photos/occ-weddings-720.webp', label: 'Weddings: ballroom' },
  { url: '/img/photos/occ-corporate-720.webp', label: 'Office: meeting room' },
  { url: '/img/photos/occ-sports-720.webp', label: 'Sports: football turf' },
  { url: '/img/photos/occ-parties-720.webp', label: 'Parties: toast' },
  { url: '/img/photos/occ-resorts-720.webp', label: 'Resorts: pool' },
  { url: '/img/photos/occ-outdoor-720.webp', label: 'Outdoor: palms and pool' },
  { url: '/img/photos/owners-960.webp', label: 'Owners: banquet hall' },
  { url: '/img/photos/placeholder-800.webp', label: 'Sports court' },
  { url: '/img/photos/celebration-900.webp', label: 'Celebration' },
];

export const OCCASION_CATEGORIES: { value: string; label: string }[] = [
  { value: 'sports', label: 'Any sports venue' },
  { value: 'cricket', label: 'Cricket ground' },
  { value: 'football', label: 'Football turf' },
  { value: 'badminton', label: 'Badminton court' },
  { value: 'tennis', label: 'Tennis court' },
  { value: 'swimming', label: 'Swimming pool' },
  { value: 'banquet', label: 'Banquet hall' },
  { value: 'wedding_lawn', label: 'Wedding lawn' },
  { value: 'reception', label: 'Reception venue' },
  { value: 'party_hall', label: 'Party hall' },
  { value: 'birthday', label: 'Birthday venue' },
  { value: 'lounge', label: 'Lounge' },
  { value: 'corporate', label: 'Corporate (any)' },
  { value: 'meeting_room', label: 'Meeting room' },
  { value: 'conference', label: 'Conference hall' },
  { value: 'coworking', label: 'Coworking space' },
  { value: 'farmhouse', label: 'Farmhouse' },
  { value: 'resort', label: 'Resort' },
  { value: 'photography', label: 'Photo studio' },
  { value: 'dance_studio', label: 'Dance studio' },
];

export const DEFAULT_HOMEPAGE: HomepageContent = {
  hero: {
    eyebrow: 'Grounds · Banquet halls · Resorts · Meeting rooms',
    title: 'Book the right venue',
    title_highlight: 'for every occasion.',
    subtitle:
      'Compare photos, prices and open dates for verified venues. Send a request, pay the way you agreed, and get a confirmed booking with a reference number.',
    image_url: '/img/photos/hero-1600.webp',
    image_alt: '',
    show_occasion_chips: true,
  },
  occasions: [
    { key: 'weddings', label: 'Weddings', category: 'banquet', image_url: '/img/photos/occ-weddings-720.webp', alt: 'A ballroom set for a wedding reception, with round tables and chandeliers' },
    { key: 'corporate', label: 'Office & meetings', category: 'corporate', image_url: '/img/photos/occ-corporate-720.webp', alt: 'Colleagues around a table in a bright meeting room' },
    { key: 'sports', label: 'Sports grounds', category: 'sports', image_url: '/img/photos/occ-sports-720.webp', alt: 'A green football turf with goalposts' },
    { key: 'parties', label: 'Parties', category: 'party_hall', image_url: '/img/photos/occ-parties-720.webp', alt: 'Friends raising their glasses at a celebration' },
    { key: 'resorts', label: 'Resorts', category: 'resort', image_url: '/img/photos/occ-resorts-720.webp', alt: 'A resort pool with loungers beside it' },
    { key: 'outdoor', label: 'Farmhouses & outdoor', category: 'farmhouse', image_url: '/img/photos/occ-outdoor-720.webp', alt: 'An open-air pool lined with palm trees' },
  ],
  sections: {
    occasions: true,
    protections: true,
    preview: true,
    reviews: true,
    owners: true,
    partners: true,
    founder: true,
    faq: true,
    closing: true,
  },
  protections: {
    title: 'What protects your booking',
    intro: 'Plain rules, the same for every venue, and shown to you before you send a request.',
  },
  preview: {
    title: 'How booking works',
    intro: 'A booking is a request first and a confirmed reservation once it is paid. Step through it before you start.',
  },
  reviews: {
    title: 'From people who booked',
    intro: 'Every review here comes from a customer whose booking at that venue was completed.',
  },
  owners: {
    title: 'List your venue for free',
    bullets: [
      'Your listing is reviewed by our team before it goes live.',
      'Pricing, open dates and blocked days in one dashboard.',
      'A commission only on bookings that come through GroundKart.',
    ],
    image_url: '/img/photos/owners-960.webp',
    image_alt: 'An empty banquet hall laid out with tables, ready for guests',
    cta_label: 'List your venue',
  },
  founder: {
    eyebrow: 'Who is behind GroundKart',
    title: 'Built by a team you can reach',
    body: 'GroundKart is a product of Quantaliez. We built it so that booking a venue works the way it should: real photos, prices that say what they cover, and a named team behind every booking that you can write to.',
    name: 'Avanish Agnihotri',
    role: 'Founder and CEO, Quantaliez',
    link_url: 'https://www.quantaliez.com',
    link_label: 'quantaliez.com',
    timeline: [
      { years: '2010 – 2022', org: 'Accenture', role: 'Twelve years leading service transitions, including programmes in Italy, France and the Philippines.' },
      { years: '2022 – 2024', org: 'Infosys', role: 'Senior Manager, Transition and Cloud Migration.' },
      { years: 'Today', org: 'Quantaliez', role: 'Founder and CEO. Quantaliez builds and runs GroundKart.' },
    ],
  },
  faq: [
    {
      q: 'Is my booking confirmed as soon as I send the request?',
      a: 'No. Sending a request holds the slot for you. The booking is confirmed once your payment has been received and recorded, and you will see it marked confirmed in My Bookings.',
    },
    {
      q: 'How do I pay?',
      a: 'After you send a request, our team shares payment details. You can pay by UPI, bank transfer or cash, as agreed for that venue. Card payments on the site are not available yet.',
    },
    {
      q: 'Can I cancel?',
      a: 'Yes. How much is refunded depends on how far ahead of the event you cancel. The cancellation terms are shown before you send a request and again on your booking.',
    },
    {
      q: 'How are venues checked?',
      a: 'Owners verify their identity before they can list, and every listing is reviewed by our team before it is published. Changes to key details go back for review.',
    },
    {
      q: 'I own a venue. What does it cost to list?',
      a: 'Listing is free. GroundKart keeps a commission only on bookings made through the platform, and every payout is recorded against the bookings it covers.',
    },
  ],
  closing: { title: 'Have a date in mind? See which venues are open.', cta_label: 'Browse venues' },
};

function isPlainObject(v: unknown): v is Record<string, unknown> {
  return typeof v === 'object' && v !== null && !Array.isArray(v);
}

/** Defaults with the published overrides on top. Arrays are replaced whole;
 * empty strings fall back to the default. */
export function mergeHomepage(overrides: unknown): HomepageContent {
  const out = JSON.parse(JSON.stringify(DEFAULT_HOMEPAGE)) as HomepageContent;
  if (!isPlainObject(overrides)) return out;
  for (const [key, value] of Object.entries(overrides)) {
    if (!(key in out) || value === null || value === undefined) continue;
    const k = key as keyof HomepageContent;
    if (Array.isArray(value)) {
      if (value.length) (out as unknown as Record<string, unknown>)[k] = value;
    } else if (isPlainObject(value) && isPlainObject(out[k])) {
      const target = out[k] as unknown as Record<string, unknown>;
      for (const [f, v] of Object.entries(value)) {
        if (v === null || v === undefined || v === '') continue;
        if (Array.isArray(v) && v.length === 0) continue;
        target[f] = v;
      }
    }
  }
  return out;
}

/** Only what differs from the defaults, so future default improvements
 * still reach fields the super admin never changed. */
export function diffFromDefaults(content: HomepageContent): HomepageOverrides {
  const out: Record<string, unknown> = {};
  for (const key of Object.keys(DEFAULT_HOMEPAGE) as (keyof HomepageContent)[]) {
    const def = DEFAULT_HOMEPAGE[key] as unknown;
    const cur = content[key] as unknown;
    if (Array.isArray(def)) {
      if (JSON.stringify(def) !== JSON.stringify(cur)) out[key] = cur;
    } else if (isPlainObject(def) && isPlainObject(cur)) {
      const changed: Record<string, unknown> = {};
      for (const f of Object.keys(def)) {
        if (JSON.stringify(def[f]) !== JSON.stringify(cur[f])) changed[f] = cur[f];
      }
      if (Object.keys(changed).length) out[key] = changed;
    }
  }
  return out as HomepageOverrides;
}

export interface PublishedContent {
  data: HomepageOverrides;
  version: number;
  updated_at: string | null;
  can_edit?: boolean;
}

export function useHomepageContent(): HomepageContent {
  const { data } = useQuery({
    queryKey: ['site-homepage'],
    queryFn: () => api.get<PublishedContent>('/api/v1/site/homepage', { skipAuth: true }),
    staleTime: 60_000,
  });
  return useMemo(() => mergeHomepage(data?.data), [data]);
}

export function responsiveImage(url: string) {
  return RESPONSIVE_IMAGES[url];
}
