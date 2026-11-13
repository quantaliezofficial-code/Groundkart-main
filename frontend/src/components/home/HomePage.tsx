import React, { useEffect, useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ArrowRight, ChevronLeft, ChevronRight, X } from 'lucide-react';
import Hero, { OccasionGrid } from '../Hero';
import { BookingProtections, FounderStory, GuidedBookingPreview, VerifiedReviews } from './TrustSections';
import VenueCard from '../VenueCard';
import { platformApi, type PublicBanner } from '../../lib/api/platform';
import type { ApiHomepageResponse } from '../../lib/api/types';
import type { Venue } from '../../types';
import { isSafeInternalPath } from '../../lib/safeUrl';
import { DEFAULT_HOMEPAGE, responsiveImage, useHomepageContent } from '../../lib/homepageContent';

/**
 * The homepage. What it does and does not contain is deliberate:
 *
 * - Every claim is one the product actually keeps. No invented reviews,
 *   counts, logos or "instant confirmation": bookings are requests that are
 *   confirmed once payment is recorded, and the page says so. Reviews shown
 *   come only from completed bookings, and the section hides when there are
 *   none.
 * - Content is visible on first paint. Nothing waits for a scroll
 *   animation, so search engines, slow phones and screen readers all get
 *   the whole page.
 * - Banners, featured venues and their order come from the admin console,
 *   so the page can change without a deploy.
 */

interface HomePageProps {
  venues: Venue[];
  isVenuesLoading: boolean;
  homepage?: ApiHomepageResponse;
  favorites: string[];
  onToggleFavorite: (venueId: string, e: React.MouseEvent) => void;
  onOpenVenue: (slugOrId: string) => void;
  onBrowseAll: () => void;
  onOccasion: (category: string) => void;
  onListVenue: () => void;
  onNavigate: (path: string) => void;
  search: {
    location: string;
    setLocation: (v: string) => void;
    date: string;
    setDate: (v: string) => void;
    category: string;
    setCategory: (v: string) => void;
    submit: () => void;
  };
}

const STRIP_DISMISS_KEY = 'groundkart_dismissed_strip';

const isInternal = isSafeInternalPath;

function BannerLink({
  banner,
  onNavigate,
  className,
  children,
}: {
  banner: PublicBanner;
  onNavigate: (path: string) => void;
  className: string;
  children: React.ReactNode;
}) {
  const url = banner.cta_url;
  if (!url) return null;
  if (isInternal(url)) {
    return (
      <a
        href={url}
        onClick={(e) => {
          e.preventDefault();
          onNavigate(url);
        }}
        className={className}
      >
        {children}
      </a>
    );
  }
  return (
    <a href={url} target="_blank" rel="noopener noreferrer" className={className}>
      {children}
    </a>
  );
}

function AnnouncementStrip({ banner, onNavigate }: { banner: PublicBanner; onNavigate: (p: string) => void }) {
  // Closed once means closed on this browser until the admin publishes a
  // different announcement (a new id), not just until the tab is closed.
  const [dismissed, setDismissed] = useState(() => {
    try {
      return localStorage.getItem(STRIP_DISMISS_KEY) === banner.id;
    } catch {
      return false;
    }
  });
  if (dismissed) return null;
  return (
    <div className="bg-marigold text-pitch">
      <div className="mx-auto flex max-w-7xl items-center gap-3 px-4 py-2.5 sm:px-6 lg:px-8">
        <p className="min-w-0 flex-1 text-sm font-medium">
          <span className="font-semibold">{banner.title}</span>
          {banner.subtitle ? <span className="hidden sm:inline"> {banner.subtitle}</span> : null}
          {banner.cta_url && banner.cta_label ? (
            <>
              {' '}
              <BannerLink banner={banner} onNavigate={onNavigate} className="font-semibold underline underline-offset-4">
                {banner.cta_label}
              </BannerLink>
            </>
          ) : null}
        </p>
        <button
          type="button"
          onClick={() => {
            setDismissed(true);
            try {
              localStorage.setItem(STRIP_DISMISS_KEY, banner.id);
            } catch {
              /* ignore */
            }
          }}
          aria-label="Dismiss announcement"
          className="shrink-0 rounded-full p-1 hover:bg-pitch/10 cursor-pointer"
        >
          <X size={16} aria-hidden="true" />
        </button>
      </div>
    </div>
  );
}

/** Admin-managed promotional slides. Advances only when asked: no timer,
 * so nothing moves while someone is reading. */
function PromoBanners({ banners, onNavigate }: { banners: PublicBanner[]; onNavigate: (p: string) => void }) {
  const [index, setIndex] = useState(0);
  useEffect(() => setIndex(0), [banners.length]);
  if (banners.length === 0) return null;
  const b = banners[Math.min(index, banners.length - 1)];
  const many = banners.length > 1;

  return (
    <section aria-label="Offers and announcements" className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 mt-12">
      <div className="relative grid grid-cols-1 md:grid-cols-12 overflow-hidden rounded-3xl bg-ink text-chalk ring-1 ring-marigold/30">
        {b.image_url ? (
          <div className="relative md:col-span-6 aspect-[16/9] md:aspect-auto md:min-h-[260px]">
            <img
              src={b.image_url}
              alt=""
              loading="lazy"
              decoding="async"
              className="absolute inset-0 h-full w-full object-cover"
            />
          </div>
        ) : null}
        <div className={`flex flex-col justify-center gap-3 p-7 sm:p-10 ${b.image_url ? 'md:col-span-6' : 'md:col-span-12'}`}>
          <h2 className="font-display text-2xl sm:text-3xl font-semibold leading-tight">{b.title}</h2>
          {b.subtitle ? <p className="text-[15px] leading-relaxed text-chalk/80 max-w-lg">{b.subtitle}</p> : null}
          {b.cta_url ? (
            <BannerLink
              banner={b}
              onNavigate={onNavigate}
              className="mt-2 inline-flex w-fit items-center gap-2 rounded-full bg-marigold px-5 py-2.5 text-sm font-semibold text-pitch hover:brightness-105"
            >
              {b.cta_label || 'Learn more'} <ArrowRight size={16} aria-hidden="true" />
            </BannerLink>
          ) : null}
          {many ? (
            <div className="mt-4 flex items-center gap-2">
              <button
                type="button"
                onClick={() => setIndex((i) => (i - 1 + banners.length) % banners.length)}
                aria-label="Previous"
                className="rounded-full border border-chalk/20 p-2 hover:bg-chalk/10 cursor-pointer"
              >
                <ChevronLeft size={16} aria-hidden="true" />
              </button>
              <span className="text-sm text-chalk/70 tabular" aria-live="polite">
                {index + 1} of {banners.length}
              </span>
              <button
                type="button"
                onClick={() => setIndex((i) => (i + 1) % banners.length)}
                aria-label="Next"
                className="rounded-full border border-chalk/20 p-2 hover:bg-chalk/10 cursor-pointer"
              >
                <ChevronRight size={16} aria-hidden="true" />
              </button>
            </div>
          ) : null}
        </div>
      </div>
    </section>
  );
}

function VenueGridSkeleton() {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6" aria-hidden="true">
      {Array.from({ length: 4 }).map((_, i) => (
        <div key={i} className="overflow-hidden rounded-2xl bg-chalk ring-1 ring-ink/5">
          <div className="aspect-[4/3] shimmer" />
          <div className="space-y-2 p-4">
            <div className="h-4 w-3/4 rounded shimmer" />
            <div className="h-3 w-1/2 rounded shimmer" />
          </div>
        </div>
      ))}
    </div>
  );
}

export const HOME_FAQ = DEFAULT_HOMEPAGE.faq;

export default function HomePage({
  venues,
  isVenuesLoading,
  homepage,
  favorites,
  onToggleFavorite,
  onOpenVenue,
  onBrowseAll,
  onOccasion,
  onListVenue,
  onNavigate,
  search,
}: HomePageProps) {
  const { data: banners = [] } = useQuery({
    queryKey: ['public-banners'],
    queryFn: () => platformApi.publicBanners(),
    staleTime: 60_000,
  });
  const content = useHomepageContent();
  const show = content.sections;
  const ownersImg = responsiveImage(content.owners.image_url);
  const heroBanners = banners.filter((b) => b.placement === 'home_hero');
  const strip = banners.find((b) => b.placement === 'home_strip');

  // Admin-curated order first (featured, then trending, popular…), then
  // the rest of the live catalogue, de-duplicated, eight at most.
  const featured = useMemo(() => {
    const byId = new Map(venues.map((v) => [v.id, v]));
    const curated: Venue[] = [];
    const seen = new Set<string>();
    const sections: (keyof ApiHomepageResponse)[] = ['featured', 'trending', 'popular', 'recommended', 'new'];
    for (const section of sections) {
      for (const card of homepage?.[section] ?? []) {
        const v = byId.get(card.id);
        if (v && !seen.has(v.id)) {
          curated.push(v);
          seen.add(v.id);
        }
      }
    }
    for (const v of venues) {
      if (curated.length >= 8) break;
      if (!seen.has(v.id)) {
        curated.push(v);
        seen.add(v.id);
      }
    }
    return curated.slice(0, 8);
  }, [venues, homepage]);

  return (
    <div className="flex-grow">
      {strip ? (
        <div className="pt-[72px] bg-pitch">
          <AnnouncementStrip banner={strip} onNavigate={onNavigate} />
        </div>
      ) : null}

      <Hero
        locationInput={search.location}
        onLocationChange={search.setLocation}
        dateInput={search.date}
        onDateChange={search.setDate}
        categoryInput={search.category}
        onCategoryChange={search.setCategory}
        onSearchSubmit={search.submit}
        onOccasion={onOccasion}
        onListVenue={onListVenue}
        belowStrip={Boolean(strip)}
        content={content}
      />

      {show.occasions ? <OccasionGrid onOccasion={onOccasion} occasions={content.occasions} /> : null}

      <PromoBanners banners={heroBanners} onNavigate={onNavigate} />

      {/* ---- Venues ---- */}
      {(isVenuesLoading || featured.length > 0) && (
        <section aria-labelledby="venues-heading" className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 mt-16 sm:mt-20" id="trending-section">
          <div className="mb-8 flex flex-wrap items-end justify-between gap-4">
            <div>
              <h2 id="venues-heading" className="font-display text-3xl sm:text-4xl font-semibold text-ink">
                Venues to book now
              </h2>
              <p className="mt-2 text-[15px] text-on-surface-variant">Live listings with open dates. Open one to see photos, pricing and availability.</p>
            </div>
            <button
              type="button"
              onClick={onBrowseAll}
              className="inline-flex items-center gap-1.5 rounded-full px-4 py-2 text-sm font-semibold text-pitch hover:bg-pitch/5 cursor-pointer"
            >
              See all venues <ArrowRight size={16} aria-hidden="true" />
            </button>
          </div>
          {isVenuesLoading && featured.length === 0 ? (
            <VenueGridSkeleton />
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
              {featured.map((venue) => (
                <VenueCard
                  key={venue.id}
                  venue={venue}
                  onClick={() => onOpenVenue(venue.slug || venue.id)}
                  onToggleFavorite={onToggleFavorite}
                  isFavorite={favorites.includes(venue.id)}
                />
              ))}
            </div>
          )}
        </section>
      )}

      {show.protections ? <BookingProtections onNavigate={onNavigate} copy={content.protections} /> : null}

      {show.preview ? <GuidedBookingPreview copy={content.preview} /> : null}

      {show.reviews ? <VerifiedReviews onOpenVenue={onOpenVenue} copy={content.reviews} /> : null}

      {/* ---- Owners and partners ---- */}
      {show.owners || show.partners ? (
      <section aria-labelledby="owners-heading" className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 mt-20 sm:mt-28">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {show.owners ? (
          <div className={`${show.partners ? 'lg:col-span-8' : 'lg:col-span-12'} grid grid-cols-1 md:grid-cols-2 overflow-hidden rounded-3xl bg-pitch text-chalk`}>
            <div className="relative min-h-[240px]">
              <img
                src={content.owners.image_url}
                srcSet={ownersImg?.srcSet}
                sizes={ownersImg ? '(min-width: 1024px) 33vw, (min-width: 768px) 50vw, 100vw' : undefined}
                alt={content.owners.image_alt}
                loading="lazy"
                decoding="async"
                width={ownersImg?.width ?? 960}
                height={ownersImg?.height ?? 720}
                className="absolute inset-0 h-full w-full object-cover"
              />
            </div>
            <div className="flex flex-col justify-center p-7 sm:p-9">
              <h2 id="owners-heading" className="font-display text-2xl sm:text-3xl font-semibold leading-tight">
                {content.owners.title}
              </h2>
              <ul className="mt-5 space-y-3 text-[15px] text-chalk/85">
                {content.owners.bullets.map((b) => (
                  <li key={b}>{b}</li>
                ))}
              </ul>
              <button
                type="button"
                onClick={onListVenue}
                className="mt-7 inline-flex w-fit items-center gap-2 rounded-full bg-marigold px-5 py-2.5 text-sm font-semibold text-pitch hover:brightness-105 cursor-pointer"
              >
                {content.owners.cta_label} <ArrowRight size={16} aria-hidden="true" />
              </button>
            </div>
          </div>
          ) : null}
          {show.partners ? (
          <div className={`${show.owners ? 'lg:col-span-4' : 'lg:col-span-12'} flex flex-col justify-between rounded-3xl bg-chalk p-7 sm:p-9 ring-1 ring-ink/5`}>
            <div>
              <h2 className="font-display text-2xl font-semibold text-ink leading-tight">Referral partners</h2>
              <p className="mt-3 text-[15px] leading-relaxed text-on-surface-variant">
                Know venue owners in your city? Partners earn a share of every paid booking at the venues they bring on,
                and track it all in their own dashboard.
              </p>
              <p className="mt-3 text-[15px] leading-relaxed text-on-surface-variant">
                Listing with a partner's code? Enter it on the first step of the listing form.
              </p>
            </div>
            <a
              href="/contact"
              onClick={(e) => {
                e.preventDefault();
                onNavigate('/contact');
              }}
              className="mt-6 inline-flex w-fit items-center gap-2 rounded-full border border-pitch/20 px-5 py-2.5 text-sm font-semibold text-pitch hover:bg-pitch hover:text-chalk"
            >
              Become a partner <ArrowRight size={16} aria-hidden="true" />
            </a>
          </div>
          ) : null}
        </div>
      </section>
      ) : null}

      {show.founder ? <FounderStory onNavigate={onNavigate} founder={content.founder} /> : null}

      {/* ---- Questions ---- */}
      {show.faq && content.faq.length ? (
      <section aria-labelledby="faq-heading" className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 mt-20 sm:mt-28">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-10">
          <h2 id="faq-heading" className="lg:col-span-4 font-display text-3xl sm:text-4xl font-semibold text-ink leading-tight">
            Questions people ask
          </h2>
          <div className="lg:col-span-8 divide-y divide-ink/10 border-y border-ink/10">
            {content.faq.map((item) => (
              <details key={item.q} className="group py-5">
                <summary className="flex cursor-pointer list-none items-center justify-between gap-4 text-[17px] font-semibold text-ink [&::-webkit-details-marker]:hidden">
                  {item.q}
                  <span
                    aria-hidden="true"
                    className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-mist text-pitch transition-transform group-open:rotate-45"
                  >
                    +
                  </span>
                </summary>
                <p className="mt-3 max-w-2xl text-[15px] leading-relaxed text-on-surface-variant">{item.a}</p>
              </details>
            ))}
          </div>
        </div>
      </section>
      ) : null}

      {/* ---- Closing ---- */}
      {show.closing ? (
      <section className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 mt-20 sm:mt-28 mb-20">
        <div className="flex flex-col items-start justify-between gap-6 rounded-3xl bg-pitch px-7 py-10 sm:flex-row sm:items-center sm:px-12">
          <h2 className="font-display text-2xl sm:text-3xl font-semibold text-chalk max-w-xl leading-tight">
            {content.closing.title}
          </h2>
          <button
            type="button"
            onClick={onBrowseAll}
            className="inline-flex shrink-0 items-center gap-2 rounded-full bg-marigold px-6 py-3 text-[15px] font-semibold text-pitch hover:brightness-105 cursor-pointer"
          >
            {content.closing.cta_label} <ArrowRight size={16} aria-hidden="true" />
          </button>
        </div>
      </section>
      ) : <div className="mb-20" />}
    </div>
  );
}
