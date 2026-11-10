import React, { useEffect, useState } from 'react';
import { BadgeCheck, Loader2 } from 'lucide-react';
import { platformApi } from '../../../lib/api/platform';
import { useDebounce } from '../../../hooks/useDebounce';

export const REFERRAL_STORAGE_KEY = 'groundkart_referral_code';

/** A code that arrived on a partner's link (…/owner?ref=GK-ABC-1234). */
export function storedReferralCode(): string {
  try {
    return localStorage.getItem(REFERRAL_STORAGE_KEY) || '';
  } catch {
    return '';
  }
}

interface Props {
  value: string;
  onChange: (code: string) => void;
  /** The venue already has a partner; show it instead of an input. */
  lockedPartner?: string | null;
}

/**
 * Optional referral partner code on the first listing step. It is checked
 * as the owner types so a typo is caught here, not after the listing is
 * created. The code is attached when the listing is first saved and can't
 * be changed by the owner afterwards.
 */
export default function ReferralCodeField({ value, onChange, lockedPartner }: Props) {
  const code = value.trim().toUpperCase();
  const debounced = useDebounce(code, 400);
  const [state, setState] = useState<{ status: 'idle' | 'checking' | 'valid' | 'invalid' | 'error'; partner?: string | null }>({
    status: 'idle',
  });

  useEffect(() => {
    if (lockedPartner !== undefined && lockedPartner !== null) return;
    if (debounced.length < 4) {
      setState({ status: 'idle' });
      return;
    }
    let cancelled = false;
    setState({ status: 'checking' });
    platformApi
      .checkReferralCode(debounced)
      .then((r) => !cancelled && setState({ status: r.valid ? 'valid' : 'invalid', partner: r.partner_name }))
      .catch(() => !cancelled && setState({ status: 'error' }));
    return () => {
      cancelled = true;
    };
  }, [debounced, lockedPartner]);

  if (lockedPartner) {
    return (
      <div className="rounded-xl border border-surface-container bg-mist p-4 text-sm">
        <p className="font-semibold text-ink">Referral partner</p>
        <p className="mt-1 flex items-center gap-1.5 text-on-surface-variant">
          <BadgeCheck className="h-4 w-4 text-primary-container" aria-hidden="true" /> Listed with {lockedPartner}
        </p>
      </div>
    );
  }

  return (
    <div>
      <label htmlFor="referral-code" className="mb-1.5 block text-sm font-semibold text-ink">
        Referral code <span className="font-normal text-on-surface-variant">(optional)</span>
      </label>
      <input
        id="referral-code"
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value.toUpperCase().replace(/\s+/g, ''))}
        maxLength={24}
        autoComplete="off"
        spellCheck={false}
        placeholder="e.g. GK-RAV-4K7P"
        aria-describedby="referral-code-help"
        className="w-full max-w-sm rounded-xl border border-surface-container-highest px-4 py-3 uppercase tracking-wide text-ink focus:border-pitch focus:outline-none focus:ring-2 focus:ring-marigold/70"
      />
      <p id="referral-code-help" className="mt-1.5 text-xs text-on-surface-variant" aria-live="polite">
        {state.status === 'checking' ? (
          <span className="inline-flex items-center gap-1">
            <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" /> Checking code…
          </span>
        ) : state.status === 'valid' ? (
          <span className="inline-flex items-center gap-1 font-medium text-primary-container">
            <BadgeCheck className="h-3.5 w-3.5" aria-hidden="true" /> Code from {state.partner}. It is saved with your listing.
          </span>
        ) : state.status === 'invalid' ? (
          <span className="font-medium text-clay">We don't recognise this code. Check it with the person who gave it to you, or leave it empty.</span>
        ) : state.status === 'error' ? (
          'Could not check the code right now. It will be checked again when you continue.'
        ) : (
          'If a GroundKart partner helped you list, enter their code. It can only be added now.'
        )}
      </p>
    </div>
  );
}
