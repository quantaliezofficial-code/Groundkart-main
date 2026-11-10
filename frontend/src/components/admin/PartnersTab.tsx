import React, { useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Plus, Search } from 'lucide-react';
import {
  platformApi,
  type Broker,
  type BrokerCreateBody,
  type BrokerPayout,
  type Commission,
  type ReferredBooking,
  type ReferredVenue,
} from '../../lib/api/platform';
import { useAuth } from '../../lib/auth';
import { useDebounce } from '../../hooks/useDebounce';
import { dateOnly, dateTime, errorText, humanize, money, percent, perUnit, slotLabel } from '../../lib/format';
import { StatusBadge } from '../dashboard';
import {
  Button,
  CopyButton,
  DataTable,
  ExportButton,
  Field,
  Modal,
  Notice,
  Panel,
  SetupLinkModal,
  Stat,
  Tabs,
  inputClass,
  inlineInputClass,
  type Column,
} from '../dashboard/kit';

/**
 * Referral partners ("brokers") from the admin side.
 *
 * Admins add partners, keep their contact and payout details current,
 * follow their venues and bookings, and record payouts. Commission terms
 * (rate, what it is calculated on, active/paused) and code regeneration are
 * super admin only: the controls are hidden for other admins, and the
 * server refuses them regardless.
 */

const BASIS_TEXT: Record<string, string> = {
  booking_amount: 'of booking amount',
  platform_commission: 'of platform commission',
};

export default function PartnersTab() {
  const { user } = useAuth();
  const isSuper = Boolean(user?.is_super_admin);
  const [search, setSearch] = useState('');
  const [status, setStatus] = useState('');
  const debounced = useDebounce(search, 300);
  const [creating, setCreating] = useState(false);
  const [openId, setOpenId] = useState<string | null>(null);
  const [setup, setSetup] = useState<{ name: string; url: string; hours: number } | null>(null);

  const list = useQuery({
    queryKey: ['admin-brokers', debounced, status],
    queryFn: () => platformApi.listBrokers({ search: debounced || undefined, status: status || undefined }),
  });
  const rows = list.data ?? [];

  const totals = useMemo(
    () =>
      rows.reduce(
        (acc, b) => {
          acc.payable += Number(b.wallet.payable);
          acc.pending += Number(b.wallet.pending);
          acc.paid += Number(b.wallet.paid);
          acc.venues += b.venue_count;
          return acc;
        },
        { payable: 0, pending: 0, paid: 0, venues: 0 },
      ),
    [rows],
  );

  const columns: Column<Broker>[] = [
    {
      key: 'name',
      header: 'Partner',
      cell: (b) => (
        <span>
          <span className="font-medium">{b.name}</span>
          <span className="block text-xs text-on-surface-variant">
            {[b.company_name, b.city].filter(Boolean).join(', ') || b.phone}
          </span>
        </span>
      ),
    },
    { key: 'code', header: 'Code', cell: (b) => <span className="font-medium tabular">{b.referral_code}</span> },
    {
      key: 'rate',
      header: 'Rate',
      cell: (b) => (
        <span className="whitespace-nowrap">
          {percent(b.commission_percent)}
          <span className="block text-xs text-on-surface-variant">{BASIS_TEXT[b.commission_basis]}</span>
        </span>
      ),
    },
    {
      key: 'venues',
      header: 'Venues',
      align: 'right',
      cell: (b) => (
        <span>
          {b.venue_count}
          <span className="block text-xs text-on-surface-variant">{b.active_venue_count} live</span>
        </span>
      ),
    },
    { key: 'pending', header: 'Coming up', align: 'right', cell: (b) => money(b.wallet.pending) },
    { key: 'payable', header: 'Payable now', align: 'right', cell: (b) => <span className="font-semibold">{money(b.wallet.payable)}</span> },
    { key: 'paid', header: 'Paid', align: 'right', cell: (b) => money(b.wallet.paid) },
    {
      key: 'status',
      header: 'Status',
      cell: (b) => <StatusBadge status={b.suspended_at ? 'suspended' : b.status} />,
    },
  ];

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Stat label="Partners" value={rows.length} />
        <Stat label="Venues referred" value={totals.venues} />
        <Stat label="Payable now" value={money(totals.payable)} tone="strong" hint="Events already held" />
        <Stat label="Paid to partners" value={money(totals.paid)} />
      </div>

      <Panel
        title="Referral partners"
        description="Partners bring venue owners on board. Owners enter the partner's code while listing, and the partner earns on every paid booking at that venue."
        actions={
          <>
            <ExportButton onExport={() => platformApi.downloadExport('brokers')} label="Partners CSV" />
            <ExportButton onExport={() => platformApi.downloadExport('broker_commissions')} label="Commissions CSV" />
            <Button variant="primary" onClick={() => setCreating(true)}>
              <Plus size={15} aria-hidden="true" /> Add partner
            </Button>
          </>
        }
        padded={false}
      >
        <div className="flex flex-wrap gap-2 border-b border-surface-container px-5 py-3">
          <label className="relative min-w-[220px] flex-1">
            <span className="sr-only">Search partners</span>
            <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-on-surface-variant" aria-hidden="true" />
            <input
              className={`${inputClass} pl-9`}
              placeholder="Name, phone, code or business"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </label>
          <select aria-label="Status" className={inlineInputClass} value={status} onChange={(e) => setStatus(e.target.value)}>
            <option value="">All statuses</option>
            <option value="active">Active</option>
            <option value="paused">Paused</option>
          </select>
        </div>
        {list.isError ? (
          <div className="p-5">
            <Notice tone="error">{errorText(list.error)}</Notice>
          </div>
        ) : (
          <DataTable
            rows={rows}
            columns={columns}
            rowKey={(b) => b.id}
            loading={list.isLoading}
            onRowClick={(b) => setOpenId(b.id)}
            empty="No partners yet. Add your first referral partner to give them a code."
          />
        )}
      </Panel>

      {creating && (
        <CreatePartnerModal
          isSuper={isSuper}
          onClose={() => setCreating(false)}
          onCreated={(name, url, hours) => {
            setCreating(false);
            setSetup({ name, url, hours });
          }}
        />
      )}
      {setup && <SetupLinkModal name={setup.name} url={setup.url} hours={setup.hours} onClose={() => setSetup(null)} />}
      {openId && (
        <PartnerDrawer
          brokerId={openId}
          isSuper={isSuper}
          onClose={() => setOpenId(null)}
          onSetupLink={(name, url, hours) => setSetup({ name, url, hours })}
        />
      )}
    </div>
  );
}

function CreatePartnerModal({
  isSuper,
  onClose,
  onCreated,
}: {
  isSuper: boolean;
  onClose: () => void;
  onCreated: (name: string, url: string, hours: number) => void;
}) {
  const qc = useQueryClient();
  const settings = useQuery({ queryKey: ['admin-settings'], queryFn: platformApi.getSettings });
  const [form, setForm] = useState({
    name: '',
    phone: '',
    email: '',
    company_name: '',
    city: '',
    commission_percent: '',
    commission_basis: 'booking_amount',
    payout_method: '',
    payout_details: '',
    notes: '',
  });
  const create = useMutation({
    mutationFn: () => {
      const body: BrokerCreateBody = {
        name: form.name.trim(),
        phone: form.phone.trim(),
        email: form.email.trim() || null,
        company_name: form.company_name.trim() || null,
        city: form.city.trim() || null,
        payout_method: form.payout_method || null,
        payout_details: form.payout_details.trim() || null,
        notes: form.notes.trim() || null,
      };
      if (isSuper) {
        if (form.commission_percent !== '') body.commission_percent = form.commission_percent;
        body.commission_basis = form.commission_basis as BrokerCreateBody['commission_basis'];
      }
      return platformApi.createBroker(body);
    },
    onSuccess: (res) => {
      qc.invalidateQueries({ queryKey: ['admin-brokers'] });
      onCreated(res.broker.name, res.setup_url, res.setup_url_expires_in_hours);
    },
  });
  const set = (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) =>
    setForm({ ...form, [k]: e.target.value });
  const defaultRate = settings.data?.default_broker_commission_percent;

  return (
    <Modal
      title="Add a referral partner"
      onClose={onClose}
      wide
      footer={
        <>
          <Button onClick={onClose}>Cancel</Button>
          <Button
            variant="primary"
            loading={create.isPending}
            disabled={form.name.trim().length < 2 || form.phone.trim().length < 10}
            onClick={() => create.mutate()}
          >
            Add partner
          </Button>
        </>
      }
    >
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <Field label="Full name">
          <input className={inputClass} value={form.name} onChange={set('name')} autoFocus maxLength={120} />
        </Field>
        <Field label="Mobile number" hint="They sign in with this">
          <input className={inputClass} value={form.phone} onChange={set('phone')} inputMode="tel" placeholder="98765 43210" />
        </Field>
        <Field label="Email (optional)">
          <input className={inputClass} value={form.email} onChange={set('email')} type="email" />
        </Field>
        <Field label="Business name (optional)">
          <input className={inputClass} value={form.company_name} onChange={set('company_name')} maxLength={160} />
        </Field>
        <Field label="City">
          <input className={inputClass} value={form.city} onChange={set('city')} maxLength={80} />
        </Field>
        <Field label="Payout method">
          <select className={inputClass} value={form.payout_method} onChange={set('payout_method')}>
            <option value="">Not set yet</option>
            <option value="upi">UPI</option>
            <option value="bank_transfer">Bank transfer</option>
            <option value="cash">Cash</option>
          </select>
        </Field>
        <Field label="Payout details" hint="UPI ID, or account name, number and IFSC" className="sm:col-span-2">
          <input className={inputClass} value={form.payout_details} onChange={set('payout_details')} maxLength={300} />
        </Field>
        {isSuper ? (
          <>
            <Field label="Commission rate (%)" hint={defaultRate ? `Leave blank to use the default, ${percent(defaultRate)}` : undefined}>
              <input
                className={inputClass}
                value={form.commission_percent}
                onChange={set('commission_percent')}
                inputMode="decimal"
                placeholder={defaultRate ?? ''}
              />
            </Field>
            <Field label="Rate applies to">
              <select className={inputClass} value={form.commission_basis} onChange={set('commission_basis')}>
                <option value="booking_amount">The booking amount received</option>
                <option value="platform_commission">GroundKart's commission on the booking</option>
              </select>
            </Field>
          </>
        ) : (
          <div className="sm:col-span-2">
            <Notice>
              New partners start at the default rate{defaultRate ? ` of ${percent(defaultRate)} of the booking amount` : ''}. Only
              the super admin can change a partner's rate.
            </Notice>
          </div>
        )}
        <Field label="Internal notes (not shown to the partner)" className="sm:col-span-2">
          <textarea className={inputClass} rows={2} value={form.notes} onChange={set('notes')} maxLength={1000} />
        </Field>
      </div>
      {create.isError ? (
        <div className="mt-4">
          <Notice tone="error">{errorText(create.error)}</Notice>
        </div>
      ) : null}
    </Modal>
  );
}

type DrawerTab = 'venues' | 'bookings' | 'commissions' | 'payouts' | 'details';

function PartnerDrawer({
  brokerId,
  isSuper,
  onClose,
  onSetupLink,
}: {
  brokerId: string;
  isSuper: boolean;
  onClose: () => void;
  onSetupLink: (name: string, url: string, hours: number) => void;
}) {
  const qc = useQueryClient();
  const [tab, setTab] = useState<DrawerTab>('venues');
  const [paying, setPaying] = useState(false);
  const broker = useQuery({ queryKey: ['admin-broker', brokerId], queryFn: () => platformApi.getBroker(brokerId) });
  const venues = useQuery({ queryKey: ['admin-broker-venues', brokerId], queryFn: () => platformApi.brokerVenues(brokerId) });
  const bookings = useQuery({
    queryKey: ['admin-broker-bookings', brokerId],
    queryFn: () => platformApi.brokerBookings(brokerId),
    enabled: tab === 'bookings',
  });
  const commissions = useQuery({
    queryKey: ['admin-broker-commissions', brokerId],
    queryFn: () => platformApi.brokerCommissions(brokerId),
    enabled: tab === 'commissions',
  });
  const payouts = useQuery({
    queryKey: ['admin-broker-payouts', brokerId],
    queryFn: () => platformApi.brokerPayouts(brokerId),
    enabled: tab === 'payouts',
  });
  const refresh = () => {
    qc.invalidateQueries({ queryKey: ['admin-brokers'] });
    qc.invalidateQueries({ queryKey: ['admin-broker', brokerId] });
    qc.invalidateQueries({ queryKey: ['admin-broker-commissions', brokerId] });
    qc.invalidateQueries({ queryKey: ['admin-broker-payouts', brokerId] });
  };
  const reissue = useMutation({
    mutationFn: () => platformApi.reissueBrokerSetupLink(brokerId),
    onSuccess: (r) => onSetupLink(r.name, r.setup_url, r.setup_url_expires_in_hours),
  });
  const b = broker.data;

  return (
    <div className="fixed inset-0 z-[55] flex justify-end bg-pitch/40" onMouseDown={onClose}>
      <aside
        role="dialog"
        aria-modal="true"
        aria-label={b ? `Partner ${b.name}` : 'Partner'}
        onMouseDown={(e) => e.stopPropagation()}
        className="flex h-full w-full max-w-4xl flex-col bg-mist shadow-2xl"
      >
        <header className="flex flex-wrap items-start justify-between gap-3 border-b border-surface-container bg-chalk px-6 py-4">
          <div className="min-w-0">
            <h2 className="font-display text-xl font-semibold text-pitch">{b?.name ?? 'Loading…'}</h2>
            {b ? (
              <p className="mt-0.5 text-sm text-on-surface-variant">
                {b.phone}
                {b.email ? `, ${b.email}` : ''} · added {dateOnly(b.created_at)}
              </p>
            ) : null}
          </div>
          <div className="flex items-center gap-2">
            <Button onClick={() => reissue.mutate()} loading={reissue.isPending}>
              New sign-in link
            </Button>
            <Button onClick={onClose}>Close</Button>
          </div>
        </header>

        <div className="min-h-0 flex-1 space-y-5 overflow-y-auto p-6" data-lenis-prevent>
          {reissue.isError ? <Notice tone="error">{errorText(reissue.error)}</Notice> : null}
          {b ? (
            <>
              <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
                <div className="rounded-2xl border border-surface-container bg-chalk p-4">
                  <p className="text-sm text-on-surface-variant">Referral code</p>
                  <p className="mt-1 font-display text-xl font-semibold tabular text-pitch">{b.referral_code}</p>
                  <div className="mt-2">
                    <CopyButton text={b.referral_code} label="Copy" />
                  </div>
                </div>
                <Stat label="Coming up" value={money(b.wallet.pending)} />
                <Stat label="Payable now" value={money(b.wallet.payable)} tone="strong" />
                <Stat label="Paid" value={money(b.wallet.paid)} hint={Number(b.wallet.reversed) > 0 ? `${money(b.wallet.reversed)} reversed by refunds` : undefined} />
              </div>

              <div className="flex flex-wrap items-center justify-between gap-3">
                <Tabs<DrawerTab>
                  value={tab}
                  onChange={setTab}
                  items={[
                    { id: 'venues', label: 'Venues', count: b.venue_count },
                    { id: 'bookings', label: 'Bookings' },
                    { id: 'commissions', label: 'Commissions', count: b.wallet.commission_count },
                    { id: 'payouts', label: 'Payouts' },
                    { id: 'details', label: 'Details and terms' },
                  ]}
                />
                <Button variant="primary" disabled={Number(b.wallet.payable) <= 0} onClick={() => setPaying(true)}>
                  Record payout
                </Button>
              </div>

              {tab === 'venues' && <VenuesList rows={venues.data ?? []} loading={venues.isLoading} />}
              {tab === 'bookings' && <BookingsList rows={bookings.data ?? []} loading={bookings.isLoading} />}
              {tab === 'commissions' && (
                <Panel
                  padded={false}
                  title="Commission ledger"
                  actions={<ExportButton onExport={() => platformApi.downloadExport('broker_commissions', { broker_id: brokerId })} />}
                >
                  <CommissionList rows={commissions.data ?? []} loading={commissions.isLoading} />
                </Panel>
              )}
              {tab === 'payouts' && (
                <Panel
                  padded={false}
                  title="Payouts"
                  actions={<ExportButton onExport={() => platformApi.downloadExport('broker_payouts', { broker_id: brokerId })} />}
                >
                  <PayoutList rows={payouts.data ?? []} loading={payouts.isLoading} />
                </Panel>
              )}
              {tab === 'details' && <DetailsForm broker={b} isSuper={isSuper} onSaved={refresh} />}
            </>
          ) : broker.isError ? (
            <Notice tone="error">{errorText(broker.error)}</Notice>
          ) : (
            <div className="h-40 rounded-2xl shimmer" />
          )}
        </div>
      </aside>
      {paying && b ? (
        <PayoutModal
          broker={b}
          onClose={() => setPaying(false)}
          onDone={() => {
            setPaying(false);
            refresh();
            setTab('payouts');
          }}
        />
      ) : null}
    </div>
  );
}

function VenuesList({ rows, loading }: { rows: ReferredVenue[]; loading: boolean }) {
  const columns: Column<ReferredVenue>[] = [
    {
      key: 'name',
      header: 'Venue',
      cell: (r) => (
        <span>
          <span className="font-medium">{r.name}</span>
          <span className="block text-xs text-on-surface-variant">
            {humanize(r.category)}, {r.city} · owner {r.owner_name}
          </span>
        </span>
      ),
    },
    { key: 'status', header: 'Listing', cell: (r) => <StatusBadge status={r.status} /> },
    {
      key: 'price',
      header: 'Price',
      align: 'right',
      cell: (r) => (
        <span>
          {money(r.base_price)}
          <span className="block text-xs text-on-surface-variant">{perUnit(r.unit_type)}</span>
        </span>
      ),
    },
    { key: 'bookings', header: 'Bookings', align: 'right', cell: (r) => `${r.paid_booking_count} paid / ${r.booking_count}` },
    { key: 'received', header: 'Received', align: 'right', cell: (r) => money(r.amount_received) },
    { key: 'commission', header: 'Commission', align: 'right', cell: (r) => money(r.commission_earned) },
    { key: 'since', header: 'Referred', cell: (r) => <span className="whitespace-nowrap">{dateOnly(r.referred_at)}</span> },
  ];
  return (
    <Panel padded={false}>
      <DataTable rows={rows} columns={columns} rowKey={(r) => r.id} loading={loading} empty="No venues listed with this code yet." />
    </Panel>
  );
}

function BookingsList({ rows, loading }: { rows: ReferredBooking[]; loading: boolean }) {
  const columns: Column<ReferredBooking>[] = [
    { key: 'ref', header: 'Booking', cell: (r) => <span className="font-medium tabular">{r.reference}</span> },
    { key: 'venue', header: 'Venue', cell: (r) => r.venue_name },
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
    { key: 'status', header: 'Status', cell: (r) => <StatusBadge status={r.status} /> },
    { key: 'payment', header: 'Payment', cell: (r) => <StatusBadge status={r.payment_state} /> },
    { key: 'amount', header: 'Amount', align: 'right', cell: (r) => money(r.amount) },
    { key: 'commission', header: 'Commission', align: 'right', cell: (r) => (r.commission_amount ? money(r.commission_amount) : '—') },
  ];
  return (
    <Panel padded={false}>
      <DataTable rows={rows} columns={columns} rowKey={(r) => r.id} loading={loading} empty="No bookings at these venues yet." />
    </Panel>
  );
}

function CommissionList({ rows, loading }: { rows: Commission[]; loading: boolean }) {
  const columns: Column<Commission>[] = [
    { key: 'ref', header: 'Booking', cell: (r) => <span className="font-medium tabular">{r.booking_reference}</span> },
    { key: 'venue', header: 'Venue', cell: (r) => r.venue_name },
    { key: 'date', header: 'Event', cell: (r) => <span className="whitespace-nowrap">{dateOnly(r.event_date)}</span> },
    {
      key: 'basis',
      header: 'Base',
      align: 'right',
      cell: (r) => (
        <span>
          {money(r.basis_amount)}
          <span className="block text-xs text-on-surface-variant">{percent(r.rate)} {BASIS_TEXT[r.basis]}</span>
        </span>
      ),
    },
    { key: 'amount', header: 'Earned', align: 'right', cell: (r) => money(r.amount) },
    { key: 'rev', header: 'Reversed', align: 'right', cell: (r) => (Number(r.reversed_amount) ? `−${money(r.reversed_amount)}` : '—') },
    { key: 'paid', header: 'Paid', align: 'right', cell: (r) => money(r.paid_amount) },
    { key: 'due', header: 'Due', align: 'right', cell: (r) => money(r.balance_due) },
    { key: 'status', header: 'Status', cell: (r) => <StatusBadge status={r.status} /> },
  ];
  return <DataTable rows={rows} columns={columns} rowKey={(r) => r.id} loading={loading} empty="No commission recorded yet." />;
}

function PayoutList({ rows, loading }: { rows: BrokerPayout[]; loading: boolean }) {
  const columns: Column<BrokerPayout>[] = [
    { key: 'date', header: 'Paid on', cell: (r) => dateTime(r.paid_at) },
    { key: 'amount', header: 'Amount', align: 'right', cell: (r) => <span className="font-semibold">{money(r.amount)}</span> },
    { key: 'method', header: 'Method', cell: (r) => humanize(r.method) },
    { key: 'ref', header: 'Reference', cell: (r) => r.reference || '—' },
    { key: 'notes', header: 'Notes', cell: (r) => r.notes || '—' },
  ];
  return <DataTable rows={rows} columns={columns} rowKey={(r) => r.id} loading={loading} empty="No payouts recorded yet." />;
}

function PayoutModal({ broker, onClose, onDone }: { broker: Broker; onClose: () => void; onDone: () => void }) {
  const [method, setMethod] = useState(broker.payout_method || 'upi');
  const [reference, setReference] = useState('');
  const [notes, setNotes] = useState('');
  const pay = useMutation({
    mutationFn: () =>
      platformApi.recordBrokerPayout(broker.id, {
        expected_amount: broker.wallet.payable,
        method,
        reference: reference.trim() || undefined,
        notes: notes.trim() || undefined,
      }),
    onSuccess: onDone,
  });
  return (
    <Modal
      title={`Record payout to ${broker.name}`}
      onClose={onClose}
      footer={
        <>
          <Button onClick={onClose}>Cancel</Button>
          <Button variant="primary" loading={pay.isPending} onClick={() => pay.mutate()}>
            Record {money(broker.wallet.payable)} as paid
          </Button>
        </>
      }
    >
      <p className="text-[15px] text-ink">
        This settles the partner's whole payable balance of <strong>{money(broker.wallet.payable)}</strong>: every commission
        for an event that has already taken place. Send the money first, then record it here.
      </p>
      {broker.payout_details ? (
        <div className="mt-3 rounded-lg border border-surface-container-highest bg-surface-container-low p-3 text-sm">
          <span className="text-on-surface-variant">Pay to ({humanize(broker.payout_method)}): </span>
          <span className="font-medium break-all">{broker.payout_details}</span>
        </div>
      ) : (
        <div className="mt-3">
          <Notice>No payout details on file for this partner. Confirm where to send the money before paying.</Notice>
        </div>
      )}
      <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2">
        <Field label="Paid by">
          <select className={inputClass} value={method} onChange={(e) => setMethod(e.target.value)}>
            <option value="upi">UPI</option>
            <option value="bank_transfer">Bank transfer</option>
            <option value="cash">Cash</option>
          </select>
        </Field>
        <Field label="Transaction reference" hint="UTR or UPI reference">
          <input className={inputClass} value={reference} onChange={(e) => setReference(e.target.value)} maxLength={120} />
        </Field>
        <Field label="Note (optional)" className="sm:col-span-2">
          <input className={inputClass} value={notes} onChange={(e) => setNotes(e.target.value)} maxLength={500} />
        </Field>
      </div>
      {pay.isError ? (
        <div className="mt-4">
          <Notice tone="error">{errorText(pay.error)}</Notice>
        </div>
      ) : null}
    </Modal>
  );
}

function DetailsForm({ broker, isSuper, onSaved }: { broker: Broker; isSuper: boolean; onSaved: () => void }) {
  const [form, setForm] = useState({
    name: broker.name,
    company_name: broker.company_name ?? '',
    city: broker.city ?? '',
    payout_method: broker.payout_method ?? '',
    payout_details: broker.payout_details ?? '',
    notes: broker.notes ?? '',
    commission_percent: broker.commission_percent,
    commission_basis: broker.commission_basis,
    status: broker.status,
  });
  const qc = useQueryClient();
  const save = useMutation({
    mutationFn: () =>
      platformApi.updateBroker(broker.id, {
        name: form.name.trim(),
        company_name: form.company_name,
        city: form.city,
        payout_method: form.payout_method,
        payout_details: form.payout_details,
        notes: form.notes,
        ...(isSuper
          ? { commission_percent: form.commission_percent, commission_basis: form.commission_basis, status: form.status }
          : {}),
      }),
    onSuccess: onSaved,
  });
  const regen = useMutation({
    mutationFn: () => platformApi.regenerateBrokerCode(broker.id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['admin-broker', broker.id] });
      onSaved();
    },
  });
  const set = (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) =>
    setForm({ ...form, [k]: e.target.value } as typeof form);

  return (
    <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
      <Panel title="Contact and payout details">
        <div className="space-y-4">
          <Field label="Full name">
            <input className={inputClass} value={form.name} onChange={set('name')} maxLength={120} />
          </Field>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <Field label="Business name">
              <input className={inputClass} value={form.company_name} onChange={set('company_name')} maxLength={160} />
            </Field>
            <Field label="City">
              <input className={inputClass} value={form.city} onChange={set('city')} maxLength={80} />
            </Field>
            <Field label="Payout method">
              <select className={inputClass} value={form.payout_method} onChange={set('payout_method')}>
                <option value="">Not set</option>
                <option value="upi">UPI</option>
                <option value="bank_transfer">Bank transfer</option>
                <option value="cash">Cash</option>
              </select>
            </Field>
            <Field label="Payout details">
              <input className={inputClass} value={form.payout_details} onChange={set('payout_details')} maxLength={300} />
            </Field>
          </div>
          <Field label="Internal notes">
            <textarea className={inputClass} rows={3} value={form.notes} onChange={set('notes')} maxLength={1000} />
          </Field>
        </div>
      </Panel>

      <Panel title="Commission terms" description={isSuper ? 'Changes apply to payments confirmed from now on. Past commission is never recalculated.' : undefined}>
        {isSuper ? (
          <div className="space-y-4">
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <Field label="Rate (%)">
                <input className={inputClass} value={form.commission_percent} onChange={set('commission_percent')} inputMode="decimal" />
              </Field>
              <Field label="Rate applies to">
                <select className={inputClass} value={form.commission_basis} onChange={set('commission_basis')}>
                  <option value="booking_amount">Booking amount received</option>
                  <option value="platform_commission">GroundKart's commission</option>
                </select>
              </Field>
              <Field label="Status" hint="Paused partners earn nothing on new payments and their code stops working.">
                <select className={inputClass} value={form.status} onChange={set('status')}>
                  <option value="active">Active</option>
                  <option value="paused">Paused</option>
                </select>
              </Field>
            </div>
            <div className="rounded-lg border border-surface-container-highest p-3">
              <p className="text-sm text-ink">
                Code <strong className="tabular">{broker.referral_code}</strong>
              </p>
              <p className="mt-1 text-xs text-on-surface-variant">
                A new code stops the old one working for new listings. Venues already attributed stay with this partner.
              </p>
              <Button className="mt-2" variant="danger" loading={regen.isPending} onClick={() => regen.mutate()}>
                Issue a new code
              </Button>
              {regen.isError ? <p className="mt-1 text-sm text-clay">{errorText(regen.error)}</p> : null}
            </div>
          </div>
        ) : (
          <dl className="space-y-2 text-[15px]">
            <div className="flex justify-between">
              <dt className="text-on-surface-variant">Rate</dt>
              <dd className="font-medium">
                {percent(broker.commission_percent)} {BASIS_TEXT[broker.commission_basis]}
              </dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-on-surface-variant">Status</dt>
              <dd>
                <StatusBadge status={broker.status} />
              </dd>
            </div>
            <p className="pt-2 text-sm text-on-surface-variant">Only the super admin can change commission terms.</p>
          </dl>
        )}
      </Panel>

      <div className="lg:col-span-2 flex items-center gap-3">
        <Button variant="primary" loading={save.isPending} onClick={() => save.mutate()}>
          Save changes
        </Button>
        {save.isSuccess ? <span className="text-sm text-primary-container">Saved.</span> : null}
        {save.isError ? <span className="text-sm text-clay">{errorText(save.error)}</span> : null}
      </div>
    </div>
  );
}
