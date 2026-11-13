import React, { useEffect, useState } from 'react';
import { Play } from 'lucide-react';
import { externalMediaAllowed } from '../../lib/legal';

/** youtube.com/watch?v=, youtu.be/, /shorts/ and Vimeo links -> privacy-friendlier embed URL. */
export function embedUrlFor(url: string): { provider: 'YouTube' | 'Vimeo'; src: string } | null {
  try {
    const u = new URL(url);
    const host = u.hostname.replace(/^www\./, '');
    if (host === 'youtu.be') return { provider: 'YouTube', src: `https://www.youtube-nocookie.com/embed/${u.pathname.slice(1)}` };
    if (host.endsWith('youtube.com') || host.endsWith('youtube-nocookie.com')) {
      const id = u.searchParams.get('v') || u.pathname.split('/').filter(Boolean).pop();
      return id ? { provider: 'YouTube', src: `https://www.youtube-nocookie.com/embed/${id}` } : null;
    }
    if (host.endsWith('vimeo.com')) {
      const id = u.pathname.split('/').filter(Boolean).pop();
      return id ? { provider: 'Vimeo', src: `https://player.vimeo.com/video/${id}?dnt=1` } : null;
    }
  } catch {
    /* not a URL */
  }
  return null;
}

/**
 * Click-to-load player (Cookie and Third-party Notice; checklist 4.2): the
 * YouTube or Vimeo iframe, which sends the visitor's IP to that company, is
 * created only when the visitor presses play, unless they switched on
 * "Load venue videos automatically" in Cookie settings.
 */
export default function VideoEmbed({ url, title }: { url: string; title: string }) {
  const embed = embedUrlFor(url);
  const [loaded, setLoaded] = useState(() => externalMediaAllowed());

  useEffect(() => {
    const onChange = (e: Event) => setLoaded((prev) => prev || Boolean((e as CustomEvent).detail));
    window.addEventListener('groundkart:external-media', onChange);
    return () => window.removeEventListener('groundkart:external-media', onChange);
  }, []);

  if (!embed) return null;
  if (loaded) {
    return (
      <iframe
        src={`${embed.src}${embed.src.includes('?') ? '&' : '?'}autoplay=1`}
        title={title}
        className="h-full w-full"
        allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
        allowFullScreen
        referrerPolicy="strict-origin-when-cross-origin"
        loading="lazy"
      />
    );
  }
  return (
    <button
      type="button"
      data-testid="video-facade"
      onClick={() => setLoaded(true)}
      className="group relative grid h-full w-full place-items-center bg-gradient-to-br from-[#0d2a1f] to-pitch text-chalk"
      aria-label={`Play video: ${title}`}
    >
      <span className="grid h-16 w-16 place-items-center rounded-full bg-chalk/95 text-pitch shadow-lg transition-transform group-hover:scale-105">
        <Play size={26} className="ml-1" fill="currentColor" />
      </span>
      <span className="absolute inset-x-0 bottom-0 bg-ink/40 px-4 py-2 text-left text-xs text-chalk/85">
        Plays from {embed.provider}, which will receive your IP address.{' '}
        <a href="/cookies" onClick={(e) => e.stopPropagation()} className="underline">Details</a>
      </span>
    </button>
  );
}
