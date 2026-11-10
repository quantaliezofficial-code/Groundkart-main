import React from 'react';
import { ArrowRight, Calendar, Grid3x3, MapPin, Search } from 'lucide-react';
import GroundSelect from './ui/GroundSelect';

/**
 * Homepage hero: the search on the left, the six occasions on the right.
 *
 * The occasion photos double as the main way in: each one opens search
 * already filtered to that kind of venue. Nothing here animates in or
 * rotates on a timer, so the first paint is the finished page and there is
 * no layout movement while someone is reaching for the search box.
 */

export interface Occasion {
  key: string;
  label: string;
  /** Value understood by the search page's category filter. */
  category: string;
  image: string;
  imageSmall: string;
  alt: string;
}

export const OCCASIONS: Occasion[] = [
  {
    key: 'weddings',
    label: 'Weddings',
    category: 'banquet',
    image: '/img/occasions/night-weddings.webp',
    imageSmall: '/img/occasions/night-weddings-sm.webp',
    alt: 'A floral wedding mandap lit with chandeliers and fairy lights',
  },
  {
    key: 'corporate',
    label: 'Office parties',
    category: 'corporate',
    image: '/img/occasions/night-corporate.webp',
    imageSmall: '/img/occasions/night-corporate-sm.webp',
    alt: 'Colleagues at an evening office gathering in a modern hall',
  },
  {
    key: 'sports',
    label: 'Sports & cricket grounds',
    category: 'sports',
    image: '/img/occasions/night-sports.webp',
    imageSmall: '/img/occasions/night-sports-sm.webp',
    alt: 'A floodlit cricket ground during an evening match',
  },
  {
    key: 'parties',
    label: 'Parties',
    category: 'party_hall',
    image: '/img/occasions/night-parties.webp',
    imageSmall: '/img/occasions/night-parties-sm.webp',
    alt: 'Guests dancing under stage lights and confetti',
  },
  {
    key: 'resorts',
    label: 'Resorts',
    category: 'resort',
    image: '/img/occasions/night-resorts.webp',
    imageSmall: '/img/occasions/night-resorts-sm.webp',
    alt: 'A resort pool lit up at dusk, lined with palms and loungers',
  },
  {
    key: 'outdoor',
    label: 'Farmhouses & outdoor',
    category: 'farmhouse',
    image: '/img/occasions/night-beach.webp',
    imageSmall: '/img/occasions/night-beach-sm.webp',
    alt: 'An open-air seating area with draped canopies at sunset',
  },
];

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
}: HeroProps) {
  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    onSearchSubmit();
  };

  return (
    <section className="relative bg-pitch text-chalk overflow-hidden" aria-labelledby="hero-heading">
      {/* Quiet depth behind the content; no imagery, so it costs nothing to paint. */}
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0"
        style={{
          background:
            'radial-gradient(60% 70% at 85% 30%, rgba(20,90,62,0.55) 0%, rgba(6,40,29,0) 70%), radial-gradient(40% 50% at 0% 100%, rgba(244,181,68,0.08) 0%, rgba(6,40,29,0) 70%)',
        }}
      />

      <div className={`relative mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 ${belowStrip ? 'pt-10 lg:pt-14' : 'pt-[104px] lg:pt-[120px]'} pb-14 lg:pb-20`}>
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-10 lg:gap-12 items-center">
          {/* ---- Copy + search ---- */}
          <div className="lg:col-span-6 min-w-0 gk-rise">
            <h1
              id="hero-heading"
              className="font-display text-[40px] leading-[1.04] sm:text-[52px] lg:text-[60px] font-semibold tracking-tight text-chalk"
              style={{ overflowWrap: 'break-word' }}
            >
              Book the right venue <span className="text-marigold">for every occasion.</span>
            </h1>
            <p className="mt-5 max-w-xl text-[17px] leading-relaxed text-chalk/80">
              Grounds, banquet halls, party spaces, resorts and meeting rooms. Compare photos and prices, check
              open dates, then request your booking.
            </p>

            <form
              onSubmit={submit}
              role="search"
              aria-label="Find a venue"
              className="mt-8 rounded-2xl bg-mist p-2 text-pitch shadow-[0_20px_50px_-20px_rgba(0,0,0,0.5)]"
            >
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-1">
                <label className="flex flex-col justify-center rounded-xl px-4 py-3 hover:bg-black/[0.03] focus-within:bg-white cursor-text">
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
                <label className="flex flex-col justify-center rounded-xl px-4 py-3 hover:bg-black/[0.03] focus-within:bg-white cursor-pointer">
                  <span className="flex items-center gap-1.5 text-[13px] font-semibold text-pitch/70">
                    <Calendar size={14} aria-hidden="true" /> Date
                  </span>
                  <input
                    id="hero-date"
                    type="date"
                    min={todayIso()}
                    value={dateInput}
                    onChange={(e) => onDateChange(e.target.value)}
                    className="mt-1 w-full bg-transparent text-[15px] font-semibold text-pitch focus:outline-none cursor-pointer"
                  />
                </label>
              </div>
              <div className="mt-1 flex flex-col sm:flex-row gap-1">
                <div className="flex-1 min-w-0">
                  <GroundSelect
                    label="What are you planning?"
                    labelIcon={<Grid3x3 size={14} className="text-pitch/70" aria-hidden="true" />}
                    value={categoryInput}
                    onValueChange={onCategoryChange}
                    placeholder="Any occasion"
                    options={OCCASION_OPTIONS}
                    className="w-full h-full flex flex-col justify-center rounded-xl hover:bg-black/[0.03] focus-within:bg-white"
                  />
                </div>
                <button
                  type="submit"
                  className="flex h-14 sm:h-auto sm:min-h-[64px] items-center justify-center gap-2 rounded-xl bg-pitch px-7 text-[15px] font-semibold text-chalk transition-colors hover:bg-ink cursor-pointer"
                >
                  <Search size={17} aria-hidden="true" />
                  Search venues
                </button>
              </div>
            </form>

            <p className="mt-5 text-[15px] text-chalk/70">
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

          {/* ---- Occasions ---- */}
          <nav aria-label="Browse by occasion" className="lg:col-span-6 min-w-0">
            <ul className="grid grid-cols-2 sm:grid-cols-3 gap-3 sm:gap-4">
              {OCCASIONS.map((o, i) => (
                <li key={o.key} className="min-w-0">
                  <button
                    type="button"
                    onClick={() => onOccasion(o.category)}
                    className="group relative block w-full aspect-square overflow-hidden rounded-2xl ring-1 ring-marigold/40 bg-ink cursor-pointer text-left"
                  >
                    <img
                      src={o.image}
                      srcSet={`${o.imageSmall} 264w, ${o.image} 496w`}
                      sizes="(min-width: 1280px) 190px, (min-width: 1024px) 15vw, (min-width: 640px) 30vw, 46vw"
                      alt={o.alt}
                      width={496}
                      height={496}
                      // The first row is above the fold on desktop; let the browser fetch it right away.
                      loading={i < 3 ? 'eager' : 'lazy'}
                      fetchPriority={i < 3 ? 'high' : 'auto'}
                      decoding="async"
                      className="absolute inset-0 h-full w-full object-cover transition-transform duration-500 ease-out group-hover:scale-[1.04]"
                    />
                    <span aria-hidden="true" className="absolute inset-x-0 bottom-0 h-1/2 bg-gradient-to-t from-black/70 to-transparent" />
                    <span className="absolute inset-x-2 bottom-2 sm:inset-x-3 sm:bottom-3 rounded-full border border-marigold/60 bg-pitch/85 px-3 py-1.5 text-center text-[13px] sm:text-sm font-semibold text-chalk backdrop-blur-sm">
                      {o.label}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          </nav>
        </div>
      </div>
    </section>
  );
}
