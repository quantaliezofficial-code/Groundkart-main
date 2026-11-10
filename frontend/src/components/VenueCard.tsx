import React, { useMemo } from 'react';
import { Heart, MapPin, Star } from 'lucide-react';
import { SafeImage } from './dashboard';
import { Venue } from '../types';

interface VenueCardProps {
  key?: React.Key;
  venue: Venue;
  onClick: (venueId: string) => void;
  onToggleFavorite: (venueId: string, e: React.MouseEvent) => void;
  isFavorite: boolean;
}

const UNIT_SHORT: Record<string, string> = { hour: 'hr', half_day: 'half day', full_day: 'day' };
const priceFormat = new Intl.NumberFormat('en-IN', { maximumFractionDigits: 0 });

/**
 * Listing card used on the homepage and in search results.
 *
 * Hover feedback is a shadow change only. The previous card animated its
 * position, every badge faded in on mount and the rating chip popped in
 * after a delay, which made long result lists flicker while scrolling.
 */
export default function VenueCard({ venue, onClick, onToggleFavorite, isFavorite }: VenueCardProps) {
  const isNew = useMemo(() => {
    if (!venue.createdAt) return false;
    const created = new Date(venue.createdAt);
    if (Number.isNaN(created.getTime())) return false;
    const days = (Date.now() - created.getTime()) / 86_400_000;
    return days >= 0 && days <= 60;
  }, [venue.createdAt]);

  const title = venue.displayName || venue.name;
  const place = venue.district && venue.district !== venue.city ? `${venue.city}, ${venue.district}` : venue.city || venue.district;
  const capacityLabel = venue.capacity ? `Up to ${venue.capacity} guests` : `${venue.capacityGroup} Cap`;
  const showUseCase =
    venue.useCases &&
    venue.useCases.length > 0 &&
    (!venue.venueType || venue.useCases[0].trim().toLowerCase() !== venue.venueType.trim().toLowerCase());

  return (
    <article
      onClick={() => onClick(venue.id)}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          onClick(venue.id);
        }
      }}
      tabIndex={0}
      role="link"
      aria-label={`${title}, ${place}`}
      className={`group flex h-full cursor-pointer flex-col overflow-hidden rounded-2xl bg-chalk ring-1 ring-ink/5 shadow-sm transition-shadow duration-200 hover:shadow-[0_16px_32px_-12px_rgba(6,40,29,0.22)] ${
        venue.isFullyBookedToday ? 'opacity-85' : ''
      }`}
    >
      <div className="relative aspect-[4/3] w-full overflow-hidden bg-surface-container-high">
        <SafeImage
          src={venue.image}
          alt={`${title}, ${venue.category} in ${venue.city}`}
          className="h-full w-full object-cover transition-transform duration-500 ease-out group-hover:scale-[1.03]"
        />

        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            onToggleFavorite(venue.id, e);
          }}
          onKeyDown={(e) => e.stopPropagation()}
          className="absolute left-3 top-3 z-10 flex h-9 w-9 items-center justify-center rounded-full bg-chalk/90 shadow-sm hover:bg-chalk cursor-pointer"
          aria-label={isFavorite ? 'Remove from saved venues' : 'Save venue'}
          aria-pressed={isFavorite}
        >
          <Heart size={17} className={isFavorite ? 'fill-clay text-clay' : 'text-on-surface-variant'} aria-hidden="true" />
        </button>

        {isNew && (
          <span className="absolute left-14 top-3.5 z-10 rounded-full bg-pitch/90 px-2.5 py-1 text-[11px] font-semibold text-chalk">
            NEW
          </span>
        )}

        {venue.rating > 0 && (
          <span className="absolute right-3 top-3 flex items-center gap-1 rounded-full bg-ink/85 px-2.5 py-1 text-chalk">
            <Star size={12} className="fill-marigold text-marigold" aria-hidden="true" />
            <span className="text-xs font-semibold">{venue.rating.toFixed(1)}</span>
            {venue.reviewCount > 0 && <span className="text-[11px] text-chalk/80">({venue.reviewCount})</span>}
          </span>
        )}

        {venue.isFullyBookedToday && (
          <div className="absolute inset-0 z-20 flex items-center justify-center bg-ink/40">
            <span className="rounded-full bg-chalk px-4 py-2 text-xs font-semibold text-pitch">Fully booked today</span>
          </div>
        )}
      </div>

      <div className="flex flex-grow flex-col p-4">
        <div className="mb-1 flex items-start justify-between gap-2">
          <h3 className="line-clamp-1 text-base font-semibold text-ink group-hover:text-pitch">{title}</h3>
          <span className="shrink-0 text-base font-semibold text-pitch tabular">
            {venue.currency || '₹'}
            {priceFormat.format(venue.basePrice)}
            <span className="text-sm font-normal text-on-surface-variant">/{UNIT_SHORT[venue.unitType] ?? 'booking'}</span>
          </span>
        </div>

        {venue.tagline && <p className="mb-1.5 line-clamp-1 text-[13px] text-on-surface-variant">{venue.tagline}</p>}

        <p className="mb-3 flex items-center gap-1 text-[13px] text-on-surface-variant">
          <MapPin size={13} className="shrink-0 text-pitch/70" aria-hidden="true" />
          <span className="truncate">{place}</span>
        </p>

        <div className="mt-auto border-t border-ink/5 pt-3">
          <div className="flex min-w-0 flex-wrap items-center gap-1.5">
            {venue.venueType && (
              <span className="shrink-0 whitespace-nowrap rounded-full bg-mist px-2.5 py-0.5 text-xs font-medium text-ink">{venue.venueType}</span>
            )}
            {showUseCase && (
              <span
                className="max-w-[140px] truncate whitespace-nowrap rounded-full bg-pitch/10 px-2.5 py-0.5 text-xs font-medium text-pitch"
                title={venue.useCases![0]}
              >
                {venue.useCases![0]}
              </span>
            )}
            <span className="shrink-0 whitespace-nowrap rounded-full bg-mist px-2.5 py-0.5 text-xs font-medium text-ink">{capacityLabel}</span>
          </div>
        </div>
      </div>
    </article>
  );
}
