import React from 'react';

/**
 * Adults-only rule (owner decision D-12). Always unticked by default; the
 * server refuses sign-up and guest checkout without it.
 */
export default function AgeDeclaration({
  id,
  checked,
  onChange,
  error,
  tone = 'light',
}: {
  id: string;
  checked: boolean;
  onChange: (v: boolean) => void;
  error?: string | null;
  tone?: 'light' | 'dark';
}) {
  const label = tone === 'dark' ? 'text-chalk' : 'text-ink';
  return (
    <div>
      <label htmlFor={id} className={`flex cursor-pointer items-start gap-2.5 text-sm ${label}`}>
        <input
          id={id}
          type="checkbox"
          checked={checked}
          onChange={(e) => onChange(e.target.checked)}
          aria-describedby={error ? `${id}-error` : undefined}
          aria-invalid={!!error}
          className="mt-0.5 h-4 w-4 shrink-0 rounded border-ink/30 text-pitch accent-pitch focus:ring-2 focus:ring-pitch/40"
        />
        <span>I confirm I am 18 years or older.</span>
      </label>
      {error && (
        <p id={`${id}-error`} role="alert" className="mt-1.5 pl-6 text-xs font-medium text-clay">
          {error}
        </p>
      )}
    </div>
  );
}

export const AGE_REQUIRED = 'Please confirm you are 18 years or older. GroundKart is for adults only.';
