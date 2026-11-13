import React, { useEffect, useRef, useState } from 'react';
import { X } from 'lucide-react';
import { externalMediaAllowed, setExternalMediaAllowed } from '../../lib/legal';

export const OPEN_COOKIE_SETTINGS = 'groundkart:cookie-settings';

export function openCookieSettings() {
  window.dispatchEvent(new Event(OPEN_COOKIE_SETTINGS));
}

/**
 * GroundKart sets one strictly necessary cookie and loads nothing from
 * other companies until the visitor asks, so there is no banner. This panel
 * (footer → Cookie settings) shows that, and holds the single optional
 * choice: loading venue videos automatically.
 */
export default function CookieSettings() {
  const [open, setOpen] = useState(false);
  const [media, setMedia] = useState(false);
  const closeRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    const onOpen = () => {
      setMedia(externalMediaAllowed());
      setOpen(true);
    };
    window.addEventListener(OPEN_COOKIE_SETTINGS, onOpen);
    return () => window.removeEventListener(OPEN_COOKIE_SETTINGS, onOpen);
  }, []);

  useEffect(() => {
    if (!open) return;
    closeRef.current?.focus();
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && setOpen(false);
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [open]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-[120] flex items-end justify-center bg-ink/40 p-4 sm:items-center" onClick={() => setOpen(false)}>
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="cookie-settings-title"
        className="w-full max-w-md rounded-2xl bg-chalk p-6 shadow-xl ring-1 ring-ink/10"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between gap-4">
          <h2 id="cookie-settings-title" className="font-display text-xl font-bold text-pitch">Cookie settings</h2>
          <button ref={closeRef} type="button" aria-label="Close" onClick={() => setOpen(false)} className="rounded-full p-1.5 text-ink/60 hover:bg-ink/5 hover:text-ink">
            <X size={18} />
          </button>
        </div>
        <p className="mt-2 text-sm leading-6 text-on-surface-variant">
          We use no analytics, advertising or tracking cookies, so there is nothing to accept or reject.
        </p>

        <div className="mt-5 divide-y divide-ink/10 rounded-xl ring-1 ring-ink/10">
          <div className="flex items-start justify-between gap-4 p-4">
            <div>
              <p className="text-sm font-semibold text-ink">Strictly necessary</p>
              <p className="mt-1 text-xs leading-5 text-on-surface-variant">One sign-in cookie, sent only to our server. Needed for the site to work.</p>
            </div>
            <span className="shrink-0 rounded-full bg-pitch/10 px-2.5 py-1 text-xs font-semibold text-pitch">Always on</span>
          </div>
          <div className="flex items-start justify-between gap-4 p-4">
            <div>
              <p id="media-switch-label" className="text-sm font-semibold text-ink">Load venue videos automatically</p>
              <p className="mt-1 text-xs leading-5 text-on-surface-variant">
                Videos come from YouTube or Vimeo, which receive your IP address. Off means a video loads only when you press play.
              </p>
            </div>
            <button
              type="button"
              role="switch"
              aria-checked={media}
              aria-labelledby="media-switch-label"
              data-setting
              onClick={() => {
                const next = !media;
                setMedia(next);
                setExternalMediaAllowed(next);
              }}
              className={`relative mt-0.5 inline-flex h-6 w-11 shrink-0 items-center rounded-full transition-colors ${media ? 'bg-pitch' : 'bg-ink/20'}`}
            >
              <span className={`inline-block h-5 w-5 rounded-full bg-chalk shadow transition-transform ${media ? 'translate-x-5' : 'translate-x-0.5'}`} />
            </button>
          </div>
        </div>

        <p className="mt-4 text-xs text-on-surface-variant">
          Details are in the{' '}
          <a href="/cookies" className="font-medium text-pitch underline underline-offset-2">Cookie and Third-party Notice</a>.
        </p>
        <div className="mt-5 flex justify-end">
          <button type="button" onClick={() => setOpen(false)} className="rounded-full bg-pitch px-5 py-2 text-sm font-semibold text-chalk hover:bg-pitch/90">
            Done
          </button>
        </div>
      </div>
    </div>
  );
}
