import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../../lib/api/client';

/**
 * Shown whenever the database holds seed rows (is_demo). Production refuses
 * to start in that state, so real customers never see sample venues or
 * sample reviews presented as real.
 */
export default function DemoBanner() {
  const { data } = useQuery({
    queryKey: ['meta-demo'],
    queryFn: () => api.get<{ demo_data_present: boolean }>('/api/v1/meta/demo', { skipAuth: true }),
    staleTime: 10 * 60 * 1000,
  });
  if (!data?.demo_data_present) return null;
  return (
    // A small pill pinned bottom-right: the fixed header and the dashboard
    // sidebars can never cover it, and it covers nothing important.
    <div
      data-testid="demo-banner"
      role="note"
      className="pointer-events-none fixed bottom-3 right-3 z-[60] max-w-[calc(100vw-1.5rem)] rounded-full bg-ink/95 px-3.5 py-1.5 text-[11px] font-semibold tracking-wide text-chalk shadow-lg"
    >
      DEMO DATA · Venues, people and reviews on this site are samples for testing.
    </div>
  );
}
