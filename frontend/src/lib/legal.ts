/**
 * Legal texts, business facts and live booking terms.
 *
 * The page sources live in src/content/legal/*.md (copied to
 * docs/compliance/drafts/ for the lawyer). Two kinds of slot are filled at
 * render time:
 *   [[OWNER TO FILL: label]]  business facts from Admin → Settings → Legal
 *                             (left visible as-is until the owner fills them)
 *   {{token}}                 live booking settings (refund tiers, hold time)
 */
import { useQuery } from '@tanstack/react-query';
import { api } from './api/client';

import privacyEn from '../content/legal/privacy.en.md?raw';
import privacyHi from '../content/legal/privacy.hi.md?raw';
import termsEn from '../content/legal/terms.en.md?raw';
import refundsEn from '../content/legal/refunds.en.md?raw';
import cookiesEn from '../content/legal/cookies.en.md?raw';
import grievanceEn from '../content/legal/grievance.en.md?raw';
import dataRightsEn from '../content/legal/data-rights.en.md?raw';

/** Must match backend/app/modules/privacy/versions.py (checked by tests). */
export const LEGAL_VERSIONS = { notice: '1.0', terms: '1.0' } as const;

export type LegalDocKey = 'privacy' | 'terms' | 'refunds' | 'cookies' | 'grievance' | 'data-rights';
export type LegalLang = 'en' | 'hi';

export const LEGAL_DOCS: Record<LegalDocKey, { path: string; title: string; sources: Partial<Record<LegalLang, string>> }> = {
  privacy: { path: '/privacy', title: 'Privacy Notice', sources: { en: privacyEn, hi: privacyHi } },
  terms: { path: '/terms', title: 'Terms of Service', sources: { en: termsEn } },
  refunds: { path: '/refunds', title: 'Refund and Cancellation Policy', sources: { en: refundsEn } },
  cookies: { path: '/cookies', title: 'Cookie and Third-party Notice', sources: { en: cookiesEn } },
  grievance: { path: '/grievance', title: 'Grievance Redressal', sources: { en: grievanceEn } },
  'data-rights': { path: '/your-data', title: 'Your Data Rights', sources: { en: dataRightsEn } },
};

export interface LegalProfile {
  legal_name: string | null;
  cin: string | null;
  registered_address: string | null;
  grievance_officer_name: string | null;
  grievance_officer_designation: string | null;
  grievance_email: string | null;
  grievance_phone: string | null;
  grievance_hours: string | null;
  customer_care_phone: string | null;
  customer_care_hours: string | null;
  jurisdiction_city: string | null;
  hosting_provider: string | null;
  payment_modes: string | null;
  tax_statement: string | null;
  refund_processing_time: string | null;
  notice_version: string;
  terms_version: string;
  notice_date: string;
  platform_fee: number;
  booking_terms: {
    hold_minutes: number;
    full_refund_hours: number;
    partial_refund_hours: number;
    partial_refund_percent: number;
  };
  /** placeholder label -> profile key */
  placeholders: Record<string, keyof LegalProfile>;
  missing: string[];
}

export const LEGAL_PROFILE_FIELDS: { key: keyof LegalProfile; label: string; hint?: string; multiline?: boolean }[] = [
  { key: 'legal_name', label: 'Legal company name', hint: 'As registered, e.g. "Example Ventures Private Limited"' },
  { key: 'cin', label: 'CIN / LLPIN', hint: 'Company or LLP identification number' },
  { key: 'registered_address', label: 'Registered office address', multiline: true },
  { key: 'grievance_officer_name', label: 'Grievance Officer name' },
  { key: 'grievance_officer_designation', label: 'Grievance Officer designation' },
  { key: 'grievance_email', label: 'Grievance email' },
  { key: 'grievance_phone', label: 'Grievance phone' },
  { key: 'grievance_hours', label: 'Grievance Officer working hours', hint: 'e.g. Mon–Sat, 10:00–18:00 IST' },
  { key: 'customer_care_phone', label: 'Customer care phone' },
  { key: 'customer_care_hours', label: 'Customer care hours' },
  { key: 'jurisdiction_city', label: 'Jurisdiction city (courts)' },
  { key: 'hosting_provider', label: 'Hosting provider and data-centre region' },
  { key: 'payment_modes', label: 'Accepted payment modes', hint: 'Shown at checkout', multiline: true },
  { key: 'tax_statement', label: 'Tax statement at checkout', hint: 'e.g. "Prices include any GST charged by the venue."', multiline: true },
  { key: 'refund_processing_time', label: 'Refund processing time', hint: 'e.g. "7 working days"' },
];

export function placeholder(label: string) {
  return `[[OWNER TO FILL: ${label}]]`;
}

export function useLegalProfile() {
  return useQuery({
    queryKey: ['legal-profile'],
    queryFn: () => api.get<LegalProfile>('/api/v1/legal/profile', { skipAuth: true }),
    staleTime: 5 * 60 * 1000,
  });
}

/** A business fact, or its visible placeholder when the owner has not filled it. */
export function fact(profile: LegalProfile | undefined, key: keyof LegalProfile, label: string): string {
  const v = profile?.[key];
  return typeof v === 'string' && v.trim() ? v : placeholder(label);
}

export function fillLegalText(md: string, profile: LegalProfile | undefined): string {
  let out = md;
  if (profile) {
    const bt = profile.booking_terms;
    const tokens: Record<string, string | number> = {
      hold_minutes: bt.hold_minutes,
      full_refund_hours: bt.full_refund_hours,
      partial_refund_hours: bt.partial_refund_hours,
      partial_refund_percent: bt.partial_refund_percent,
    };
    out = out.replace(/\{\{(\w+)\}\}/g, (m, k) => (k in tokens ? String(tokens[k]) : m));
    out = out.replace(/\[\[OWNER TO FILL: ([^\]]+)\]\]/g, (m, label: string) => {
      const key = profile.placeholders?.[label];
      const v = key ? profile[key] : null;
      return typeof v === 'string' && v.trim() ? v : m;
    });
  } else {
    // Before the profile loads, show a neutral dash rather than "{{token}}".
    out = out.replace(/\{\{(\w+)\}\}/g, '…');
  }
  return out;
}

export const EXTERNAL_MEDIA_KEY = 'groundkart_external_media';

export function externalMediaAllowed(): boolean {
  try {
    return localStorage.getItem(EXTERNAL_MEDIA_KEY) === 'on';
  } catch {
    return false;
  }
}

export function setExternalMediaAllowed(on: boolean) {
  try {
    if (on) localStorage.setItem(EXTERNAL_MEDIA_KEY, 'on');
    else localStorage.removeItem(EXTERNAL_MEDIA_KEY);
  } catch {
    /* storage unavailable: setting just won't persist */
  }
  window.dispatchEvent(new CustomEvent('groundkart:external-media', { detail: on }));
}
