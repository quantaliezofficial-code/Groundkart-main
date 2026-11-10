/**
 * Small building blocks shared by the newer dashboard screens (team,
 * partners, banners, records, partner dashboard), so they look and behave
 * the same: one panel style, one table style, one way to show a one-time
 * link, one export button.
 */
import React, { useState } from 'react';
import { Check, Copy, Download, Loader2, X } from 'lucide-react';
import { errorText } from '../../lib/format';

export function Panel({
  title,
  description,
  actions,
  children,
  className = '',
  padded = true,
}: {
  title?: React.ReactNode;
  description?: React.ReactNode;
  actions?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
  padded?: boolean;
}) {
  return (
    <section className={`rounded-2xl border border-surface-container bg-surface-container-lowest ${className}`}>
      {(title || actions) && (
        <header className="flex flex-wrap items-start justify-between gap-3 border-b border-surface-container px-5 py-4">
          <div className="min-w-0">
            {title ? <h2 className="text-base font-semibold text-ink">{title}</h2> : null}
            {description ? <p className="mt-0.5 text-sm text-on-surface-variant">{description}</p> : null}
          </div>
          {actions ? <div className="flex flex-wrap items-center gap-2">{actions}</div> : null}
        </header>
      )}
      <div className={padded ? 'p-5' : ''}>{children}</div>
    </section>
  );
}

type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger' | 'accent';

const VARIANT: Record<ButtonVariant, string> = {
  primary: 'bg-pitch text-chalk hover:bg-ink',
  accent: 'bg-marigold text-pitch hover:brightness-105',
  secondary: 'border border-surface-container-highest bg-chalk text-ink hover:bg-surface-container-low',
  ghost: 'text-pitch hover:bg-pitch/5',
  danger: 'border border-clay/30 bg-chalk text-clay hover:bg-clay/5',
};

export function Button({
  variant = 'secondary',
  loading = false,
  className = '',
  children,
  disabled,
  ...rest
}: React.ButtonHTMLAttributes<HTMLButtonElement> & { variant?: ButtonVariant; loading?: boolean }) {
  return (
    <button
      type="button"
      {...rest}
      disabled={disabled || loading}
      className={`inline-flex items-center justify-center gap-1.5 rounded-lg px-3.5 py-2 text-sm font-semibold transition-colors disabled:cursor-not-allowed disabled:opacity-50 cursor-pointer ${VARIANT[variant]} ${className}`}
    >
      {loading ? <Loader2 size={15} className="animate-spin" aria-hidden="true" /> : null}
      {children}
    </button>
  );
}

export function Field({
  label,
  hint,
  error,
  children,
  className = '',
}: {
  label: string;
  hint?: React.ReactNode;
  error?: string | null;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <label className={`block ${className}`}>
      <span className="mb-1 block text-sm font-medium text-ink">{label}</span>
      {children}
      {error ? (
        <span className="mt-1 block text-sm text-clay">{error}</span>
      ) : hint ? (
        <span className="mt-1 block text-xs text-on-surface-variant">{hint}</span>
      ) : null}
    </label>
  );
}

export const inputClass =
  'w-full rounded-lg border border-surface-container-highest bg-chalk px-3 py-2 text-[15px] text-ink placeholder:text-on-surface-variant/60 focus:border-pitch focus:outline-none focus:ring-2 focus:ring-pitch/15 disabled:bg-surface-container-low';

export function Notice({ tone = 'info', children }: { tone?: 'info' | 'error' | 'success'; children: React.ReactNode }) {
  const style =
    tone === 'error'
      ? 'border-clay/30 bg-clay/5 text-clay'
      : tone === 'success'
        ? 'border-primary-container/30 bg-primary-container/5 text-primary-container'
        : 'border-info/25 bg-info/5 text-ink';
  return (
    <div role={tone === 'error' ? 'alert' : 'status'} className={`rounded-lg border px-3.5 py-2.5 text-sm ${style}`}>
      {children}
    </div>
  );
}

export function CopyButton({ text, label = 'Copy', className = '' }: { text: string; label?: string; className?: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <Button
      variant="secondary"
      className={className}
      onClick={async () => {
        try {
          await navigator.clipboard.writeText(text);
          setCopied(true);
          setTimeout(() => setCopied(false), 1800);
        } catch {
          window.prompt('Copy this:', text);
        }
      }}
    >
      {copied ? <Check size={15} aria-hidden="true" /> : <Copy size={15} aria-hidden="true" />}
      {copied ? 'Copied' : label}
    </Button>
  );
}

/** Downloads a CSV through the authenticated client and reports failures inline. */
export function ExportButton({
  onExport,
  label = 'Export CSV',
  variant = 'secondary',
}: {
  onExport: () => Promise<unknown>;
  label?: string;
  variant?: ButtonVariant;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  return (
    <span className="inline-flex flex-col items-end">
      <Button
        variant={variant}
        loading={busy}
        onClick={async () => {
          setBusy(true);
          setError(null);
          try {
            await onExport();
          } catch (err) {
            setError(errorText(err, 'Export failed'));
          } finally {
            setBusy(false);
          }
        }}
      >
        {!busy ? <Download size={15} aria-hidden="true" /> : null}
        {label}
      </Button>
      {error ? <span className="mt-1 text-xs text-clay">{error}</span> : null}
    </span>
  );
}

export function Modal({
  title,
  onClose,
  children,
  footer,
  wide = false,
}: {
  title: string;
  onClose: () => void;
  children: React.ReactNode;
  footer?: React.ReactNode;
  wide?: boolean;
}) {
  React.useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

  return (
    <div className="fixed inset-0 z-[60] flex items-end justify-center bg-pitch/50 p-0 sm:items-center sm:p-4" onMouseDown={onClose}>
      <div
        role="dialog"
        aria-modal="true"
        aria-label={title}
        onMouseDown={(e) => e.stopPropagation()}
        className={`flex max-h-[92vh] w-full flex-col overflow-hidden rounded-t-2xl bg-chalk shadow-2xl sm:rounded-2xl ${wide ? 'sm:max-w-3xl' : 'sm:max-w-lg'}`}
      >
        <header className="flex items-center justify-between border-b border-surface-container px-5 py-4">
          <h2 className="text-base font-semibold text-ink">{title}</h2>
          <button type="button" onClick={onClose} aria-label="Close" className="rounded-md p-1 text-on-surface-variant hover:bg-surface-container cursor-pointer">
            <X size={18} aria-hidden="true" />
          </button>
        </header>
        <div className="min-h-0 flex-1 overflow-y-auto px-5 py-4" data-lenis-prevent>
          {children}
        </div>
        {footer ? <footer className="flex flex-wrap justify-end gap-2 border-t border-surface-container px-5 py-3">{footer}</footer> : null}
      </div>
    </div>
  );
}

/** Shows a one-time account set-up link. It is never stored anywhere, so
 * this is the only chance to copy it. */
export function SetupLinkModal({
  name,
  url,
  hours,
  onClose,
}: {
  name: string;
  url: string;
  hours: number;
  onClose: () => void;
}) {
  return (
    <Modal title="Share the set-up link" onClose={onClose} footer={<Button variant="primary" onClick={onClose}>Done</Button>}>
      <p className="text-[15px] text-ink">
        Send this link to <strong>{name}</strong>. They open it, choose their own password and can then sign in with
        their phone number or email.
      </p>
      <div className="mt-4 rounded-lg border border-surface-container-highest bg-surface-container-low p-3">
        <code className="block break-all text-sm text-ink">{url}</code>
      </div>
      <div className="mt-3 flex flex-wrap items-center gap-2">
        <CopyButton text={url} label="Copy link" />
        <a
          className="inline-flex items-center gap-1.5 rounded-lg border border-surface-container-highest px-3.5 py-2 text-sm font-semibold text-ink hover:bg-surface-container-low"
          href={`https://wa.me/?text=${encodeURIComponent(`Your GroundKart account is ready. Set your password here (valid ${hours} hours): ${url}`)}`}
          target="_blank"
          rel="noopener noreferrer"
        >
          Share on WhatsApp
        </a>
      </div>
      <Notice>
        The link works once and expires in {hours} hours. It is not saved anywhere, so copy it now. You can issue a new
        one later if it is lost.
      </Notice>
    </Modal>
  );
}

export interface Column<T> {
  key: string;
  header: React.ReactNode;
  cell: (row: T) => React.ReactNode;
  align?: 'left' | 'right';
  className?: string;
}

export function DataTable<T>({
  rows,
  columns,
  rowKey,
  empty,
  onRowClick,
  loading = false,
}: {
  rows: T[];
  columns: Column<T>[];
  rowKey: (row: T) => string;
  empty?: React.ReactNode;
  onRowClick?: (row: T) => void;
  loading?: boolean;
}) {
  if (loading) {
    return (
      <div className="space-y-2 p-5" aria-busy="true">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="h-9 rounded shimmer" />
        ))}
      </div>
    );
  }
  if (rows.length === 0) {
    return <div className="px-5 py-12 text-center text-sm text-on-surface-variant">{empty ?? 'Nothing to show yet.'}</div>;
  }
  return (
    <div className="overflow-x-auto custom-scrollbar">
      <table className="w-full text-left text-sm">
        <thead className="bg-surface-container-low text-on-surface-variant">
          <tr>
            {columns.map((c) => (
              <th
                key={c.key}
                scope="col"
                className={`whitespace-nowrap px-4 py-2.5 font-medium ${c.align === 'right' ? 'text-right' : ''} ${c.className ?? ''}`}
              >
                {c.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-surface-container">
          {rows.map((row) => (
            <tr
              key={rowKey(row)}
              onClick={onRowClick ? () => onRowClick(row) : undefined}
              className={onRowClick ? 'cursor-pointer hover:bg-surface-container-low' : ''}
            >
              {columns.map((c) => (
                <td
                  key={c.key}
                  className={`px-4 py-3 align-top text-ink ${c.align === 'right' ? 'text-right tabular whitespace-nowrap' : ''} ${c.className ?? ''}`}
                >
                  {c.cell(row)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function Stat({
  label,
  value,
  hint,
  tone = 'default',
}: {
  label: string;
  value: React.ReactNode;
  hint?: React.ReactNode;
  tone?: 'default' | 'strong';
}) {
  return (
    <div
      className={`rounded-2xl border p-5 ${
        tone === 'strong' ? 'border-pitch bg-pitch text-chalk' : 'border-surface-container bg-surface-container-lowest'
      }`}
    >
      <p className={`text-sm ${tone === 'strong' ? 'text-chalk/75' : 'text-on-surface-variant'}`}>{label}</p>
      <p className={`mt-1 font-display text-2xl font-semibold tabular ${tone === 'strong' ? 'text-marigold' : 'text-pitch'}`}>
        {value}
      </p>
      {hint ? <p className={`mt-1 text-xs ${tone === 'strong' ? 'text-chalk/70' : 'text-on-surface-variant'}`}>{hint}</p> : null}
    </div>
  );
}

export function Tabs<T extends string>({
  value,
  onChange,
  items,
}: {
  value: T;
  onChange: (v: T) => void;
  items: { id: T; label: string; count?: number }[];
}) {
  return (
    <div role="tablist" className="flex flex-wrap gap-1 rounded-lg bg-surface-container p-1">
      {items.map((it) => (
        <button
          key={it.id}
          type="button"
          role="tab"
          aria-selected={value === it.id}
          onClick={() => onChange(it.id)}
          className={`rounded-md px-3 py-1.5 text-sm font-medium cursor-pointer ${
            value === it.id ? 'bg-chalk text-ink shadow-sm' : 'text-on-surface-variant hover:text-ink'
          }`}
        >
          {it.label}
          {typeof it.count === 'number' ? <span className="ml-1.5 text-on-surface-variant tabular">{it.count}</span> : null}
        </button>
      ))}
    </div>
  );
}
