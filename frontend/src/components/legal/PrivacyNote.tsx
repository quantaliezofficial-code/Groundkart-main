import React from 'react';
import { ShieldCheck } from 'lucide-react';

/**
 * The line every form carries (checklist item 1.1): what happens to what you
 * type, with the Privacy Notice one tap away. Links open in a new tab so a
 * half-filled form is never lost.
 */
export default function PrivacyNote({ children, tone = 'light', className = '' }: { children?: React.ReactNode; tone?: 'light' | 'dark'; className?: string }) {
  const text = tone === 'dark' ? 'text-chalk/75' : 'text-on-surface-variant';
  const link = tone === 'dark' ? 'text-chalk underline' : 'text-pitch underline';
  return (
    <p data-testid="privacy-note" className={`flex items-start gap-2 text-xs leading-5 ${text} ${className}`}>
      <ShieldCheck size={14} className="mt-0.5 shrink-0 opacity-70" aria-hidden />
      <span>
        {children ?? 'We use these details only to handle this request.'}{' '}
        See our{' '}
        <a href="/privacy" target="_blank" rel="noopener" className={`${link} font-medium underline-offset-2`}>
          Privacy Notice
        </a>
        .
      </span>
    </p>
  );
}
