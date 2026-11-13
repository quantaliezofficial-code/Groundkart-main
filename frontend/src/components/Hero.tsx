import React from 'react';
import { ArrowRight, Calendar, Grid3x3, MapPin, Search } from 'lucide-react';
import GroundSelect from './ui/GroundSelect';
import { DEFAULT_HOMEPAGE, responsiveImage, type HomepageContent, type OccasionItem } from '../lib/homepageContent';

/**
 * Homepage hero: one full-bleed photo, a centred headline and a single wide
 * search bar. The six occasions sit below it as photo cards (OccasionGrid).
 *
 * Nothing rotates on a timer and nothing waits for a scroll animation, so
 * the first paint is the finished page and there is no layout movement
 * while someone is reaching for the search box.
 */

export type Occasion = OccasionItem;

/** The default six occasions (the super admin can change them). */
export const OCCASIONS: Occasion[] = DEFAULT_HOMEPAGE.occasions;

export const OCCASION_OPTIONS = [
  { value: 'g_sports', label: 'Sports & fitness', isGroupHeader: true },
  { value: 'sports', label: 'Any sports venue' },
  { value: 'cricket', label: 'Cricket ground' },
  { value: 'football', label: 'Football turf' },
  { value: 'badminton', label: 'Badminton court' },
  { value: 'tennis', label: 'Tennis court' },
  { value: 'swimming', label: 'Swimming pool' },
  { value: 'g_wedding', label: 'Weddings & functions', isGroupHeader: true },
  { value: 'banquet', label: 'Banquet hall' },
  { value: 'wedding_lawn', label: 'Wedding lawn' },
  { value: 'reception', label: 'Reception venue' },
  { value: 'g_party', label: 'Parties & celebrations', isGroupHeader: true },
  { value: 'party_hall', label: 'Party hall' },
  { value: 'birthday', label: 'Birthday venue' },
  { value: 'lounge', label: 'Lounge' },
  { value: 'g_corp', label: 'Work & business', isGroupHeader: true },
  { value: 'meeting_room', label: 'Meeting room' },
  { value: 'conference', label: 'Conference hall' },
  { value: 'coworking', label: 'Coworking space' },
  { value: 'g_outdoor', label: 'Stays & outdoor', isGroupHeader: true },
  { value: 'farmhouse', label: 'Farmhouse' },
  { value: 'resort', label: 'Resort' },
  { value: 'g_creative', label: 'Studios', isGroupHeader: true },
  { value: 'photography', label: 'Photo studio' },
  { value: 'dance_studio', label: 'Dance studio' },
];

interface HeroProps {
  locationInput: string;
  onLocationChange: (val: string) => void;
  dateInput: string;
  onDateChange: (val: string) => void;
  categoryInput: string;
  onCategoryChange: (val: string) => void;
  onSearchSubmit: () => void;
  onOccasion: (category: string) => void;
  onListVenue: () => void;
  /** True when an announcement strip already sits between the header and the hero. */
  belowStrip?: boolean;
  /** Editable copy and images (Admin › Website). Defaults when omitted. */
  content?: Pick<HomepageContent, 'hero' | 'occasions'>;
}

function todayIso(): string {
  return new Date().toLocaleDateString('en-CA');
}

export default function Hero({
  locationInput,
  onLocationChange,
  dateInput,
  onDateChange,
  categoryInput,
  onCategoryChange,
  onSearchSubmit,
  onOccasion,
  onListVenue,
  belowStrip = false,
  content = DEFAULT_HOMEPAGE,
}: HeroProps) {
  const hero = content.hero;
  const heroImg = responsiveImage(hero.image_url);
  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    onSearchSubmit();
  };

  return (
    <section className="relative isolate overflow-hidden bg-pitch text-chalk" aria-labelledby="hero-heading">
      {/* Full-bleed photo. Self-hosted, sized per screen, fetched first. */}
      <img
        src={hero.image_url}
        srcSet={heroImg?.srcSet}
        sizes={heroImg ? '100vw' : undefined}
        alt={hero.image_alt}
        width={heroImg?.width ?? 1600}
        height={heroImg?.height ?? 900}
        fetchPriority="high"
        decoding="async"
        className="absolute inset-0 -z-20 h-full w-full object-cover"
      />
      {/* Even, quiet shade so the headline and search read on any part of the photo. */}
      <div
        aria-hidden="true"
        className="absolute inset-0 -z-10 bg-gradient-to-b from-[#03201799] via-[#06281Dad] to-[#06281Df2]"
      />

      <div
        className={`mx-auto flex min-h-[620px] max-w-5xl flex-col items-center justify-center px-4 text-center sm:px-6 lg:min-h-[700px] ${
          belowStrip ? 'pt-12' : 'pt-[120px]'
        } pb-16 lg:pb-24`}
      >
        <div className="gk-rise w-full">
          {hero.eyebrow ? (
            <p className="hidden text-[13px] font-semibold uppercase tracking-[0.18em] text-marigold sm:block">{hero.eyebrow}</p>
          ) : null}
          <h1
            id="hero-heading"
            className="mx-auto max-w-3xl font-display sm:mt-4 text-[40px] font-semibold leading-[1.05] tracking-tight sm:text-[56px] lg:text-[68px]"
            style={{ overflowWrap: 'break-word' }}
          >
            {hero.title} {hero.title_highlight ? <span className="text-marigold">{hero.title_highlight}</span> : null}
          </h1>
          <p className="mx-auto mt-5 max-w-2xl text-[17px] leading-relaxed text-chalk/85">{hero.subtitle}</p>

          <form
            onSubmit={submit}
            role="search"
            aria-label="Find a venue"
            className="mx-auto mt-9 w-full max-w-4xl rounded-[28px] bg-chalk p-2 text-left text-pitch shadow-[0_30px_80px_-30px_rgba(0,0,0,0.7)] lg:rounded-full"
          >
            <div className="flex flex-col gap-1 lg:flex-row lg:items-stretch lg:gap-0">
              <label className="flex min-w-0 flex-1 cursor-text flex-col justify-center rounded-2xl px-5 py-3 hover:bg-black/[0.03] focus-within:bg-white lg:rounded-full">
                <span className="flex items-center gap-1.5 text-[13px] font-semibold text-pitch/70">
                  <MapPin size={14} aria-hidden="true" /> City or area
                </span>
                <input
                  id="hero-location"
                  type="text"
                  autoComplete="address-level2"
                  placeholder="e.g. Lucknow, Gomti Nagar"
                  value={locationInput}
                  onChange={(e) => onLocationChange(e.target.value)}
                  className="mt-1 w-full bg-transparent text-[15px] font-semibold text-pitch placeholder:text-pitch/40 focus:outline-none"
                />
              </label>
              <span aria-hidden="true" className="hidden w-px self-stretch bg-ink/10 my-3 lg:block" />
              <label className="flex cursor-pointer flex-col justify-center rounded-2xl px-5 py-3 hover:bg-black/[0.03] focus-within:bg-white lg:w-[190px] lg:rounded-full">
                <span className="flex items-center gap-1.5 text-[13px] font-semibold text-pitch/70">
                  <Calendar size={14} aria-hidden="true" /> Date
                </span>
                <input
                  id="hero-date"
                  type="date"
                  min={todayIso()}
                  value={dateInput}
                  onChange={(e) => onDateChange(e.target.value)}
                  className="mt-1 w-full cursor-pointer bg-transparent text-[15px] font-semibold text-pitch focus:outline-none"
                />
              </label>
              <span aria-hidden="true" className="hidden w-px self-stretch bg-ink/10 my-3 lg:block" />
              <div className="min-w-0 lg:w-[250px]">
                <GroundSelect
                  label="What are you planning?"
                  labelIcon={<Grid3x3 size={14} className="text-pitch/70" aria-hidden="true" />}
                  value={categoryInput}
                  onValueChange={onCategoryChange}
                  placeholder="Any occasion"
                  options={OCCASION_OPTIONS}
                  className="flex h-full w-full flex-col justify-center rounded-2xl hover:bg-black/[0.03] focus-within:bg-white lg:rounded-full"
                />
              </div>
              <button
                type="submit"
                className="flex h-14 items-center justify-center gap-2 rounded-2xl bg-pitch px-7 text-[15px] font-semibold text-chalk transition-colors hover:bg-ink cursor-pointer lg:h-auto lg:min-h-[64px] lg:rounded-full"
              >
                <Search size={17} aria-hidden="true" />
                Search venues
              </button>
            </div>
          </form>

          {hero.show_occasion_chips ? (
          <nav aria-label="Popular occasions" className="mx-auto mt-6 hidden max-w-3xl sm:flex flex-wrap items-center justify-center gap-2">
            {content.occasions.map((o) => (
              <button
                key={o.key}
                type="button"
                onClick={() => onOccasion(o.category)}
                className="rounded-full border border-chalk/25 bg-chalk/10 px-3.5 py-1.5 text-[13px] font-semibold text-chalk backdrop-blur-sm transition-colors hover:border-marigold hover:text-marigold cursor-pointer"
              >
                {o.label}
              </button>
            ))}
          </nav>
          ) : null}

          <p className="mt-7 text-[15px] text-chalk/75">
            Own a venue?{' '}
            <button
              type="button"
              onClick={onListVenue}
              className="inline-flex items-center gap-1 font-semibold text-marigold underline-offset-4 hover:underline cursor-pointer"
            >
              List it on GroundKart <ArrowRight size={15} aria-hidden="true" />
            </button>
          </p>
        </div>
      </div>
    </section>
  );
}

/** Six portrait photo cards, one per occasion; each opens a filtered search. */
export function OccasionGrid({
  onOccasion,
  occasions = DEFAULT_HOMEPAGE.occasions,
}: {
  onOccasion: (category: string) => void;
  occasions?: OccasionItem[];
}) {
  return (
    <section aria-labelledby="occasions-heading" className="mx-auto mt-16 max-w-7xl px-4 sm:mt-20 sm:px-6 lg:px-8">
      <div className="mb-8 max-w-2xl">
        <h2 id="occasions-heading" className="font-display text-3xl font-semibold text-ink sm:text-4xl">
          Browse by occasion
        </h2>
        <p className="mt-2 text-[15px] text-on-surface-variant">Start with what you are planning. Every card opens live listings for that kind of venue.</p>
      </div>
      <nav aria-label="Browse by occasion">
        <ul className="grid grid-cols-2 gap-3 sm:gap-5 md:grid-cols-3 xl:grid-cols-6">
          {occasions.map((o) => {
            const img = responsiveImage(o.image_url);
            return (
            <li key={o.key} className="min-w-0">
              <button
                type="button"
                onClick={() => onOccasion(o.category)}
                className="group relative block aspect-[4/5] w-full overflow-hidden rounded-2xl bg-ink text-left cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-marigold focus-visible:ring-offset-2"
              >
                <img
                  src={o.image_url}
                  srcSet={img?.srcSet}
                  sizes={img ? '(min-width: 1280px) 200px, (min-width: 768px) 30vw, 46vw' : undefined}
                  alt={o.alt}
                  width={720}
                  height={900}
                  loading="lazy"
                  decoding="async"
                  className="absolute inset-0 h-full w-full object-cover transition-transform duration-700 ease-out group-hover:scale-[1.05]"
                />
                <span aria-hidden="true" className="absolute inset-0 bg-gradient-to-t from-black/75 via-black/10 to-transparent" />
                <span className="absolute inset-x-3 bottom-3 flex items-end justify-between gap-2 sm:inset-x-4 sm:bottom-4">
                  <span className="text-[15px] font-semibold leading-tight text-chalk sm:text-base">{o.label}</span>
                  <ArrowRight
                    size={16}
                    aria-hidden="true"
                    className="mb-0.5 shrink-0 text-marigold transition-transform duration-300 group-hover:translate-x-0.5"
                  />
                </span>
              </button>
            </li>
            );
          })}
        </ul>
      </nav>
    </section>
  );
}
