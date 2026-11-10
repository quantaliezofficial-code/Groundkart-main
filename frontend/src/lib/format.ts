/** Display formatting shared by every dashboard. Indian conventions:
 * lakh/crore digit grouping, ₹, day-month-year. */

const inr = new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 });
const inrPaise = new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', minimumFractionDigits: 2 });
const number = new Intl.NumberFormat('en-IN');

/** ₹1,25,000. Shows paise only when the amount actually has them. */
export function money(value: string | number | null | undefined): string {
  if (value === null || value === undefined || value === '') return '—';
  const n = typeof value === 'number' ? value : Number(value);
  if (!Number.isFinite(n)) return '—';
  return Number.isInteger(n) ? inr.format(n) : inrPaise.format(n);
}

export function count(value: number | null | undefined): string {
  return value === null || value === undefined ? '—' : number.format(value);
}

/** "5%" / "2.5%" from "5.00" / "2.50". */
export function percent(value: string | number | null | undefined): string {
  if (value === null || value === undefined || value === '') return '—';
  const n = Number(value);
  return Number.isFinite(n) ? `${parseFloat(n.toFixed(2))}%` : '—';
}

/** 12 Nov 2026 */
export function dateOnly(iso: string | null | undefined): string {
  if (!iso) return '—';
  // A bare YYYY-MM-DD is a calendar date, not an instant: parse it as local
  // so it can never slip to the previous day in a western time zone.
  const d = /^\d{4}-\d{2}-\d{2}$/.test(iso) ? new Date(`${iso}T00:00:00`) : new Date(iso);
  if (Number.isNaN(d.getTime())) return '—';
  return d.toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' });
}

/** 12 Nov 2026, 3:40 pm */
export function dateTime(iso: string | null | undefined): string {
  if (!iso) return '—';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '—';
  return d.toLocaleString('en-IN', { day: 'numeric', month: 'short', year: 'numeric', hour: 'numeric', minute: '2-digit' });
}

/** "18:00:00" -> "6:00 pm" */
export function timeOfDay(hms: string | null | undefined): string {
  if (!hms) return '';
  const [h, m] = hms.split(':').map(Number);
  if (!Number.isFinite(h)) return '';
  const d = new Date(2000, 0, 1, h, m || 0);
  return d.toLocaleTimeString('en-IN', { hour: 'numeric', minute: '2-digit' });
}

export function slotLabel(start: string | null | undefined, end: string | null | undefined): string {
  if (!start) return 'Full day';
  return end ? `${timeOfDay(start)} – ${timeOfDay(end)}` : timeOfDay(start);
}

const UNIT: Record<string, string> = { hour: 'hour', half_day: 'half day', full_day: 'day' };
export function perUnit(unitType: string | null | undefined): string {
  return `per ${UNIT[unitType || ''] || 'booking'}`;
}

/** snake_case / kebab-case -> "Sentence case" */
const ACRONYMS: Record<string, string> = { upi: 'UPI', ifsc: 'IFSC', gst: 'GST', id: 'ID' };

export function humanize(value: string | null | undefined): string {
  if (!value) return '—';
  if (ACRONYMS[value.toLowerCase()]) return ACRONYMS[value.toLowerCase()];
  const text = value.replace(/[_-]+/g, ' ').trim();
  return text.charAt(0).toUpperCase() + text.slice(1);
}

export function errorText(err: unknown, fallback = 'Something went wrong. Please try again.'): string {
  if (err && typeof err === 'object' && 'detail' in err && typeof (err as any).detail === 'string') {
    return (err as any).detail;
  }
  if (err instanceof Error && err.message) return err.message;
  return fallback;
}
