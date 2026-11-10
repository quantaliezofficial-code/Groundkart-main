import React, { useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { History, Search } from 'lucide-react';
import {
  platformApi,
  type BookingRegisterRow,
  type RegisterFilters,
  type VenueRegisterRow,
} from '../../lib/api/platform';
import { useDebounce } from '../../hooks/useDebounce';
import { count, dateOnly, dateTime, errorText, humanize, money, percent, slotLabel } from '../../lib/format';
import { StatusBadge } from '../dashboard';
import { Button, DataTable, ExportButton, Modal, Notice, Panel, Tabs, inputClass, inlineInputClass, type Column } from '../dashboard/kit';

/**
 * Records & exports: the operational register.
 *
 * One row per listing and one row per booking, with the owner, referral
 * partner, payment, platform commission and partner commission already
 * joined in. Filters here are the same ones the CSV export uses, so a
 * download always matches the table on screen. Every download is itself
 * written to the audit log.
 */

type View = 'bookings' | 'venues' | 'exports';
const PAGE = 50;

export default function RecordsTab() {
  const [view, setView] = useState<View>('bookings');
  return (
    <div className="space-y-5">
      <Tabs<View>
        value={view}
        onChange={setView}
        items={[
          { id: 'bookings', label: 'Booking register' },
          { id: 'venues', label: 'Venue register' },
          { id: 'exports', label: 'All exports' },
        ]}
      />
      {view === 'bookings' && <BookingRegister />}
      {view === 'venues' && <VenueRegister />}
      {view === 'exports' && <ExportsList />}
    </div>
  );
}

function useBrokers() {
  return useQuery({ queryKey: ['admin-brokers', '', ''], queryFn: () => platformApi.listBrokers() });
}

function FilterBar({ children }: { children: React.ReactNode }) {
  return <div className="flex flex-wrap items-end gap-2 border-b border-surface-container px-5 py-3">{children}</div>;
}

function Pager({ page, setPage, hasMore }: { page: number; setPage: (n: number) => void; hasMore: boolean }) {
  if (page === 0 && !hasMore) return null;
  return (
    <div className="flex items-center justify-end gap-2 border-t border-surface-container px-5 py-3 text-sm">
      <Button disabled={page === 0} onClick={() => setPage(page - 1)}>
        Previous
      </Button>
      <span className="text-on-surface-variant tabular">Page {page + 1}</span>
      <Button disabled={!hasMore} onClick={() => setPage(page + 1)}>
        Next
      </Button>
    </div>
  );
}

const BOOKING_STATUSES = ['pending_payment', 'confirmed', 'completed', 'cancelled', 'refunded', 'expired', 'rejected', 'under_admin_review'];

function BookingRegister() {
  const brokers = useBrokers();
  const [search, setSearch] = useState('');
  const debounced = useDebounce(search, 300);
  const [status, setStatus] = useState('');
  const [payment, setPayment] = useState<'' | 'received' | 'awaiting'>('');
  const [brokerId, setBrokerId] = useState('');
  const [dateBasis, setDateBasis] = useState<'booked' | 'event'>('booked');
  const [from, setFrom] = useState('');
  const [to, setTo] = useState('');
  const [page, setPage] = useState(0);
  const [open, setOpen] = useState<BookingRegisterRow | null>(null);

  const filters: RegisterFilters = {
    search: debounced || undefined,
    status: status || undefined,
    payment: payment || undefined,
    broker_id: brokerId || undefined,
    date_basis: dateBasis,
    date_from: from || undefined,
    date_to: to || undefined,
  };
  const key = JSON.stringify(filters);
  const rows = useQuery({
    queryKey: ['records-bookings', key, page],
    queryFn: () => platformApi.bookingRegister({ ...filters, limit: PAGE + 1, offset: page * PAGE }),
  });
  React.useEffect(() => setPage(0), [key]);
  const data = (rows.data ?? []).slice(0, PAGE);
  const hasMore = (rows.data?.length ?? 0) > PAGE;

  const totals = useMemo(
    () =>
      data.reduce(
        (a, r) => {
          a.amount += Number(r.amount);
          a.received += Number(r.amount_received);
          a.commission += Number(r.platform_commission);
          a.partner += Number(r.broker_commission ?? 0);
          return a;
        },
        { amount: 0, received: 0, commission: 0, partner: 0 },
      ),
    [data],
  );

  const columns: Column<BookingRegisterRow>[] = [
    {
      key: 'ref',
      header: 'Booking',
      cell: (r) => (
        <span>
          <span className="font-medium tabular">{r.reference}</span>
          <span className="block whitespace-nowrap text-xs text-on-surface-variant">{dateTime(r.booked_at)}</span>
        </span>
      ),
    },
    {
      key: 'venue',
      header: 'Venue',
      cell: (r) => (
        <span>
          {r.venue_name}
          <span className="block text-xs text-on-surface-variant">{r.venue_city}</span>
        </span>
      ),
    },
    {
      key: 'event',
      header: 'Event',
      cell: (r) => (
        <span className="whitespace-nowrap">
          {dateOnly(r.event_date)}
          <span className="block text-xs text-on-surface-variant">{slotLabel(r.start_time, r.end_time)}</span>
        </span>
      ),
    },
    {
      key: 'customer',
      header: 'Customer',
      cell: (r) => (
        <span>
          {r.customer_name || '—'}
          <span className="block text-xs text-on-surface-variant">{r.customer_phone || r.customer_email || ''}</span>
        </span>
      ),
    },
    { key: 'status', header: 'Status', cell: (r) => <StatusBadge status={r.status} /> },
    { key: 'amount', header: 'Amount', align: 'right', cell: (r) => money(r.amount) },
    {
      key: 'paid',
      header: 'Received',
      align: 'right',
      cell: (r) =>
        r.payment_received ? (
          <span>
            {money(r.amount_received)}
            <span className="block text-xs text-on-surface-variant">{humanize(r.payment_method)}</span>
          </span>
        ) : (
          <span className="text-on-surface-variant">Not yet</span>
        ),
    },
    { key: 'comm', header: 'Platform', align: 'right', cell: (r) => (r.payment_received ? money(r.platform_commission) : '—') },
    {
      key: 'partner',
      header: 'Partner',
      align: 'right',
      cell: (r) =>
        r.broker_name ? (
          <span>
            {r.broker_commission ? money(r.broker_commission) : '—'}
            <span className="block text-xs text-on-surface-variant">{r.broker_name}</span>
          </span>
        ) : (
          '—'
        ),
    },
  ];

  return (
    <Panel
      title="Every booking, with its money trail"
      description="Click a row for the full record."
      actions={<ExportButton onExport={() => platformApi.downloadExport('bookings', filters)} label="Export these bookings" variant="primary" />}
      padded={false}
    >
      <FilterBar>
        <label className="relative min-w-[200px] flex-1">
          <span className="sr-only">Search</span>
          <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-on-surface-variant" aria-hidden="true" />
          <input className={`${inputClass} pl-9`} placeholder="Reference, venue, customer or phone" value={search} onChange={(e) => setSearch(e.target.value)} />
        </label>
        <select aria-label="Status" className={inlineInputClass} value={status} onChange={(e) => setStatus(e.target.value)}>
          <option value="">Any status</option>
          {BOOKING_STATUSES.map((s) => (
            <option key={s} value={s}>
              {humanize(s)}
            </option>
          ))}
        </select>
        <select aria-label="Payment" className={inlineInputClass} value={payment} onChange={(e) => setPayment(e.target.value as typeof payment)}>
          <option value="">Paid or not</option>
          <option value="received">Payment received</option>
          <option value="awaiting">Awaiting payment</option>
        </select>
        <select aria-label="Referral partner" className={inlineInputClass} value={brokerId} onChange={(e) => setBrokerId(e.target.value)}>
          <option value="">Any partner</option>
          {(brokers.data ?? []).map((b) => (
            <option key={b.id} value={b.id}>
              {b.name}
            </option>
          ))}
        </select>
        <select aria-label="Date basis" className={inlineInputClass} value={dateBasis} onChange={(e) => setDateBasis(e.target.value as 'booked' | 'event')}>
          <option value="booked">Booked between</option>
          <option value="event">Event between</option>
        </select>
        <input aria-label="From" type="date" className={inlineInputClass} value={from} onChange={(e) => setFrom(e.target.value)} />
        <input aria-label="To" type="date" className={inlineInputClass} value={to} onChange={(e) => setTo(e.target.value)} />
      </FilterBar>
      {rows.isError ? (
        <div className="p-5">
          <Notice tone="error">{errorText(rows.error)}</Notice>
        </div>
      ) : (
        <DataTable rows={data} columns={columns} rowKey={(r) => r.id} loading={rows.isLoading} onRowClick={(r) => setOpen(r)} empty="No bookings match these filters." />
      )}
      {data.length > 0 ? (
        <div className="flex flex-wrap gap-x-6 gap-y-1 border-t border-surface-container px-5 py-3 text-sm text-on-surface-variant">
          <span>This page: {count(data.length)} bookings</span>
          <span>Booked value {money(totals.amount)}</span>
          <span>Received {money(totals.received)}</span>
          <span>Platform commission {money(totals.commission)}</span>
          <span>Partner commission {money(totals.partner)}</span>
        </div>
      ) : null}
      <Pager page={page} setPage={setPage} hasMore={hasMore} />
      {open ? <BookingRecord row={open} onClose={() => setOpen(null)} /> : null}
    </Panel>
  );
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="grid grid-cols-5 gap-3 py-1.5 text-[15px]">
      <dt className="col-span-2 text-on-surface-variant">{label}</dt>
      <dd className="col-span-3 break-words text-ink">{children ?? '—'}</dd>
    </div>
  );
}

function BookingRecord({ row: r, onClose }: { row: BookingRegisterRow; onClose: () => void }) {
  return (
    <Modal title={`Booking ${r.reference}`} onClose={onClose} wide>
      <div className="grid grid-cols-1 gap-x-8 md:grid-cols-2">
        <dl>
          <h3 className="mb-1 mt-1 text-sm font-semibold text-ink">Booking</h3>
          <Row label="Status"><StatusBadge status={r.status} /></Row>
          <Row label="Booked on">{dateTime(r.booked_at)}</Row>
          <Row label="Venue">{r.venue_name}, {r.venue_city}</Row>
          <Row label="Owner">{r.owner_name}</Row>
          <Row label="Event">{dateOnly(r.event_date)}, {slotLabel(r.start_time, r.end_time)}</Row>
          <Row label="Rental mode">{humanize(r.rental_mode)}</Row>
          <Row label="Guests">{r.guest_count ?? '—'}</Row>
          <Row label="Customer">{r.customer_name} ({r.customer_type === 'guest' ? 'guest checkout' : 'account'})</Row>
          <Row label="Contact">{[r.customer_phone, r.customer_email].filter(Boolean).join(', ') || '—'}</Row>
          {r.cancelled_at ? <Row label="Cancelled">{dateTime(r.cancelled_at)}{r.cancellation_reason ? `: ${r.cancellation_reason}` : ''}</Row> : null}
        </dl>
        <dl>
          <h3 className="mb-1 mt-1 text-sm font-semibold text-ink">Money</h3>
          <Row label="Booking amount">{money(r.amount)}</Row>
          <Row label="Payment">{r.payment_received ? `Received ${dateTime(r.payment_recorded_at)}` : 'Not received'}</Row>
          <Row label="Method">{humanize(r.payment_method)}</Row>
          <Row label="Reference">{r.payment_reference || '—'}</Row>
          <Row label="Refunded">{money(r.refund_amount)}</Row>
          <Row label="Net received">{money(r.amount_received)}</Row>
          <Row label="Platform commission">{money(r.platform_commission)}</Row>
          <Row label="Owner share">{money(r.owner_share)}</Row>
          <Row label="Referral partner">{r.broker_name || 'None'}</Row>
          {r.broker_name ? (
            <Row label="Partner commission">
              {r.broker_commission ? `${money(r.broker_commission)} at ${percent(r.broker_commission_rate)}` : 'Not earned'}
              {r.broker_commission_status ? <span className="ml-2"><StatusBadge status={r.broker_commission_status} /></span> : null}
            </Row>
          ) : null}
        </dl>
      </div>
    </Modal>
  );
}

const VENUE_STATUSES = ['active', 'pending_review', 'draft', 'suspended', 'archived'];

function VenueRegister() {
  const brokers = useBrokers();
  const [search, setSearch] = useState('');
  const debounced = useDebounce(search, 300);
  const [status, setStatus] = useState('');
  const [brokerId, setBrokerId] = useState('');
  const [referred, setReferred] = useState<'' | 'yes' | 'no'>('');
  const [from, setFrom] = useState('');
  const [to, setTo] = useState('');
  const [page, setPage] = useState(0);
  const [history, setHistory] = useState<VenueRegisterRow | null>(null);

  const filters: RegisterFilters = {
    search: debounced || undefined,
    status: status || undefined,
    broker_id: brokerId || undefined,
    referred: referred === '' ? undefined : referred === 'yes',
    date_from: from || undefined,
    date_to: to || undefined,
  };
  const key = JSON.stringify(filters);
  const rows = useQuery({
    queryKey: ['records-venues', key, page],
    queryFn: () => platformApi.venueRegister({ ...filters, limit: PAGE + 1, offset: page * PAGE }),
  });
  React.useEffect(() => setPage(0), [key]);
  const data = (rows.data ?? []).slice(0, PAGE);
  const hasMore = (rows.data?.length ?? 0) > PAGE;

  const columns: Column<VenueRegisterRow>[] = [
    {
      key: 'name',
      header: 'Venue',
      cell: (r) => (
        <span>
          <span className="font-medium">{r.name}</span>
          <span className="block text-xs text-on-surface-variant">{humanize(r.category)}, {r.city}</span>
        </span>
      ),
    },
    {
      key: 'owner',
      header: 'Owner',
      cell: (r) => (
        <span>
          {r.owner_name}
          <span className="block text-xs text-on-surface-variant">{r.owner_phone}</span>
        </span>
      ),
    },
    {
      key: 'status',
      header: 'Status',
      cell: (r) => (
        <span>
          <StatusBadge status={r.status} />
          {r.status_note ? <span className="mt-1 block max-w-[200px] text-xs text-on-surface-variant">{r.status_note}</span> : null}
        </span>
      ),
    },
    { key: 'partner', header: 'Partner', cell: (r) => r.broker_name || '—' },
    { key: 'listed', header: 'Listed', cell: (r) => <span className="whitespace-nowrap">{dateOnly(r.listed_at)}</span> },
    { key: 'approved', header: 'Approved', cell: (r) => <span className="whitespace-nowrap">{dateOnly(r.approved_at)}</span> },
    { key: 'bookings', header: 'Bookings', align: 'right', cell: (r) => `${r.confirmed_booking_count} / ${r.booking_count}` },
    { key: 'received', header: 'Received', align: 'right', cell: (r) => money(r.amount_received) },
    { key: 'commission', header: 'Platform', align: 'right', cell: (r) => money(r.platform_commission) },
    {
      key: 'history',
      header: '',
      cell: (r) => (
        <Button
          variant="ghost"
          onClick={(e) => {
            e.stopPropagation();
            setHistory(r);
          }}
        >
          <History size={15} aria-hidden="true" /> History
        </Button>
      ),
    },
  ];

  return (
    <Panel
      title="Every listing, from first draft to today"
      actions={<ExportButton onExport={() => platformApi.downloadExport('venues', filters)} label="Export these venues" variant="primary" />}
      padded={false}
    >
      <FilterBar>
        <label className="relative min-w-[200px] flex-1">
          <span className="sr-only">Search</span>
          <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-on-surface-variant" aria-hidden="true" />
          <input className={`${inputClass} pl-9`} placeholder="Venue, city, owner or phone" value={search} onChange={(e) => setSearch(e.target.value)} />
        </label>
        <select aria-label="Status" className={inlineInputClass} value={status} onChange={(e) => setStatus(e.target.value)}>
          <option value="">Any status</option>
          {VENUE_STATUSES.map((s) => (
            <option key={s} value={s}>
              {humanize(s === 'pending_review' ? 'in_review' : s)}
            </option>
          ))}
        </select>
        <select aria-label="Referral" className={inlineInputClass} value={referred} onChange={(e) => setReferred(e.target.value as typeof referred)}>
          <option value="">Referred or not</option>
          <option value="yes">Via a partner</option>
          <option value="no">Direct</option>
        </select>
        <select aria-label="Partner" className={inlineInputClass} value={brokerId} onChange={(e) => setBrokerId(e.target.value)}>
          <option value="">Any partner</option>
          {(brokers.data ?? []).map((b) => (
            <option key={b.id} value={b.id}>
              {b.name}
            </option>
          ))}
        </select>
        <input aria-label="Listed from" type="date" className={inlineInputClass} value={from} onChange={(e) => setFrom(e.target.value)} />
        <input aria-label="Listed to" type="date" className={inlineInputClass} value={to} onChange={(e) => setTo(e.target.value)} />
      </FilterBar>
      {rows.isError ? (
        <div className="p-5">
          <Notice tone="error">{errorText(rows.error)}</Notice>
        </div>
      ) : (
        <DataTable rows={data} columns={columns} rowKey={(r) => r.id} loading={rows.isLoading} onRowClick={(r) => setHistory(r)} empty="No venues match these filters." />
      )}
      <Pager page={page} setPage={setPage} hasMore={hasMore} />
      {history ? <VenueHistoryModal venue={history} onClose={() => setHistory(null)} /> : null}
    </Panel>
  );
}

/** A listing's full timeline, plus the one correction admins make most:
 * attaching or changing its referral partner. */
export function VenueHistoryModal({ venue, onClose }: { venue: { id: string; name: string; broker_id: string | null }; onClose: () => void }) {
  const qc = useQueryClient();
  const history = useQuery({ queryKey: ['venue-history', venue.id], queryFn: () => platformApi.venueHistory(venue.id) });
  const brokers = useBrokers();
  const [brokerId, setBrokerId] = useState(venue.broker_id ?? '');
  const assign = useMutation({
    mutationFn: () => platformApi.setVenueBroker(venue.id, brokerId || null),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['venue-history', venue.id] });
      qc.invalidateQueries({ queryKey: ['records-venues'] });
      qc.invalidateQueries({ queryKey: ['admin-brokers'] });
    },
  });
  const h = history.data;

  return (
    <Modal title={`History: ${venue.name}`} onClose={onClose} wide>
      {history.isError ? <Notice tone="error">{errorText(history.error)}</Notice> : null}
      {h ? (
        <p className="mb-4 text-sm text-on-surface-variant">
          Now <StatusBadge status={h.status} /> · {h.booking_count} bookings
          {h.first_booking_at ? `, first ${dateOnly(h.first_booking_at)}, latest ${dateOnly(h.last_booking_at)}` : ''}
        </p>
      ) : null}
      <ol className="relative space-y-4 border-l border-surface-container-highest pl-5">
        {(h?.timeline ?? []).map((e, i) => (
          <li key={`${e.at}-${i}`} className="relative">
            <span className="absolute -left-[26px] top-1.5 h-2.5 w-2.5 rounded-full bg-pitch ring-4 ring-chalk" aria-hidden="true" />
            <p className="text-[15px] font-medium text-ink">{e.label}</p>
            <p className="text-sm text-on-surface-variant">
              {dateTime(e.at)}
              {e.actor_name ? ` · ${e.actor_name}` : ''}
              {e.actor_role ? ` (${e.actor_role})` : ''}
            </p>
            <EventDetails details={e.details} />
          </li>
        ))}
        {history.isLoading ? <li className="h-16 rounded shimmer" /> : null}
      </ol>

      <div className="mt-6 rounded-lg border border-surface-container-highest p-4">
        <p className="text-sm font-semibold text-ink">Referral partner</p>
        <p className="mt-0.5 text-xs text-on-surface-variant">
          Applies to payments confirmed from now on. Commission already recorded stays with whoever earned it.
        </p>
        <div className="mt-3 flex flex-wrap gap-2">
          <select aria-label="Referral partner" className={`${inlineInputClass} min-w-[220px]`} value={brokerId} onChange={(e) => setBrokerId(e.target.value)}>
            <option value="">No partner</option>
            {(brokers.data ?? []).map((b) => (
              <option key={b.id} value={b.id}>
                {b.name} ({b.referral_code})
              </option>
            ))}
          </select>
          <Button variant="primary" loading={assign.isPending} disabled={(venue.broker_id ?? '') === brokerId && !assign.isSuccess} onClick={() => assign.mutate()}>
            Save partner
          </Button>
        </div>
        {assign.isError ? <p className="mt-2 text-sm text-clay">{errorText(assign.error)}</p> : null}
        {assign.isSuccess ? <p className="mt-2 text-sm text-primary-container">Saved and added to the history.</p> : null}
      </div>
    </Modal>
  );
}

function EventDetails({ details }: { details: Record<string, unknown> }) {
  const entries = Object.entries(details || {}).filter(([k, v]) => v !== null && v !== undefined && v !== '' && k !== 'broker_id' && k !== 'previous_broker_id');
  if (entries.length === 0) return null;
  return (
    <p className="mt-0.5 text-sm text-ink/80">
      {entries
        .map(([k, v]) => `${humanize(k)}: ${Array.isArray(v) ? v.map((x) => humanize(String(x))).join(', ') : typeof v === 'object' ? '…' : humanize(String(v))}`)
        .join(' · ')}
    </p>
  );
}

function ExportsList() {
  const list = useQuery({ queryKey: ['records-exports'], queryFn: platformApi.listExports });
  const [from, setFrom] = useState('');
  const [to, setTo] = useState('');
  return (
    <Panel
      title="Download a register"
      description="CSV files open in Excel and Google Sheets. Amounts are in rupees, times in IST. Leave the dates empty for everything."
      actions={
        <>
          <input aria-label="From" type="date" className={inlineInputClass} value={from} onChange={(e) => setFrom(e.target.value)} />
          <input aria-label="To" type="date" className={inlineInputClass} value={to} onChange={(e) => setTo(e.target.value)} />
        </>
      }
      padded={false}
    >
      {list.isError ? (
        <div className="p-5">
          <Notice tone="error">{errorText(list.error)}</Notice>
        </div>
      ) : null}
      <ul className="divide-y divide-surface-container">
        {(list.data ?? []).map((e) => (
          <li key={e.kind} className="flex flex-wrap items-center gap-4 px-5 py-4">
            <div className="min-w-0 flex-1">
              <p className="font-medium text-ink">{e.title}</p>
              <p className="text-sm text-on-surface-variant">
                {count(e.row_count)} rows in total · {e.columns.length} columns: {e.columns.slice(0, 6).join(', ')}
                {e.columns.length > 6 ? '…' : ''}
              </p>
            </div>
            <ExportButton onExport={() => platformApi.downloadExport(e.kind, { date_from: from || undefined, date_to: to || undefined })} label="Download" />
          </li>
        ))}
        {list.isLoading ? <li className="m-5 h-16 rounded shimmer" /> : null}
      </ul>
    </Panel>
  );
}
