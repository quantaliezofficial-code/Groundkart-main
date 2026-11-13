import React, { useState } from 'react';
import { X } from 'lucide-react';
import { useAuth } from '../../lib/auth';
import { api } from '../../lib/api/client';
import { LEGAL_VERSIONS } from '../../lib/legal';
import { errorText } from '../../lib/format';
import AgeDeclaration from './AgeDeclaration';

/**
 * Shown to a signed-in account that has not accepted the current Privacy
 * Notice and Terms (accounts made before they existed, or after a new
 * version). DPDP s.5(2): people whose data we already hold get the notice
 * too. Nothing is pre-ticked; the person can read both pages first.
 *
 * It can be closed. Closing it is remembered on this browser for this
 * notice version, so it does not come back on every page or visit; the
 * person is asked again only when the notice changes, and checkout still
 * asks for the 18+ confirmation and shows the agreement line.
 */
const DISMISS_KEY = 'groundkart_notice_dismissed';

function dismissedVersion(): string | null {
  try {
    return localStorage.getItem(DISMISS_KEY);
  } catch {
    return null;
  }
}
export default function NoticeUpdateBanner({ onNavigate }: { onNavigate: (path: string) => void }) {
  const { user, refreshUser } = useAuth();
  const [age, setAge] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const versionKey = `${LEGAL_VERSIONS.notice}/${LEGAL_VERSIONS.terms}`;
  const [closed, setClosed] = useState(() => dismissedVersion() === versionKey);

  if (!user || user.role === 'admin' || closed) return null;
  const needsTerms = user.accepted_terms_version !== LEGAL_VERSIONS.terms;
  const needsAge = !user.age_confirmed;
  if (!needsTerms && !needsAge) return null;

  const close = () => {
    setClosed(true);
    try {
      localStorage.setItem(DISMISS_KEY, versionKey);
    } catch {
      /* private mode: closed for this page view only */
    }
  };

  const accept = async () => {
    setBusy(true);
    setError(null);
    try {
      await api.post('/api/v1/me/consents/accept', { accept: true, age_confirmed: age });
      await refreshUser();
    } catch (e) {
      setError(errorText(e));
    } finally {
      setBusy(false);
    }
  };

  const link = (path: string, label: string) => (
    <a
      href={path}
      onClick={(e) => {
        e.preventDefault();
        onNavigate(path);
      }}
      className="font-semibold underline underline-offset-4"
    >
      {label}
    </a>
  );

  return (
    <div role="region" aria-label="Updated privacy notice and terms" data-testid="notice-update-banner" className="fixed inset-x-0 bottom-0 z-[55] border-t border-pitch/15 bg-chalk shadow-[0_-12px_40px_-20px_rgba(6,40,29,0.4)]">
      <div className="mx-auto flex max-w-5xl flex-col gap-3 px-4 py-4 sm:px-6 md:flex-row md:items-center md:justify-between">
        <div className="min-w-0 text-sm text-ink">
          <p className="font-semibold">Please review our Privacy Notice and Terms</p>
          <p className="mt-0.5 text-on-surface-variant">
            They explain what we collect, why, and your rights. Read the {link('/privacy', 'Privacy Notice')} and{' '}
            {link('/terms', 'Terms of Use')}, then accept to keep using your account.
          </p>
          {needsAge ? (
            <div className="mt-2">
              <AgeDeclaration id="notice-age-confirm" checked={age} onChange={setAge} />
            </div>
          ) : null}
          {error ? <p className="mt-1 text-clay" role="alert">{error}</p> : null}
        </div>
        <div className="flex shrink-0 items-center gap-2">
          <button
            type="button"
            onClick={close}
            className="rounded-full px-4 py-2.5 text-sm font-semibold text-pitch hover:bg-pitch/5 cursor-pointer"
          >
            Not now
          </button>
          <button
            type="button"
            onClick={accept}
            disabled={busy || (needsAge && !age)}
            className="rounded-full bg-pitch px-5 py-2.5 text-sm font-semibold text-chalk hover:bg-ink disabled:cursor-not-allowed disabled:opacity-50 cursor-pointer"
          >
            {busy ? 'Saving…' : 'I accept'}
          </button>
          <button
            type="button"
            onClick={close}
            aria-label="Close"
            className="rounded-full p-2 text-on-surface-variant hover:bg-pitch/5 cursor-pointer"
          >
            <X size={16} aria-hidden="true" />
          </button>
        </div>
      </div>
    </div>
  );
}
