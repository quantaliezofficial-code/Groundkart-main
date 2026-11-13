import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { platformApi } from '../lib/api/platform';
import { isSafeInternalPath } from '../lib/safeUrl';

/** Admin-managed line above search results (placement "search_top"). */
export default function SearchTopBanner({ onNavigate }: { onNavigate: (path: string) => void }) {
  const { data = [] } = useQuery({
    queryKey: ['public-banners'],
    queryFn: () => platformApi.publicBanners(),
    staleTime: 60_000,
  });
  const banner = data.find((b) => b.placement === 'search_top');
  if (!banner) return null;
  const url = banner.cta_url;
  const internal = isSafeInternalPath(url);
  return (
    <div className="mb-6 flex flex-wrap items-center gap-x-3 gap-y-1 rounded-xl border border-marigold/40 bg-marigold/10 px-4 py-3 text-sm text-pitch">
      <span className="font-semibold">{banner.title}</span>
      {banner.subtitle ? <span className="text-ink/80">{banner.subtitle}</span> : null}
      {url && banner.cta_label ? (
        <a
          href={url}
          {...(internal
            ? { onClick: (e: React.MouseEvent) => { e.preventDefault(); onNavigate(url); } }
            : { target: '_blank', rel: 'noopener noreferrer' })}
          className="font-semibold underline underline-offset-4"
        >
          {banner.cta_label}
        </a>
      ) : null}
    </div>
  );
}
