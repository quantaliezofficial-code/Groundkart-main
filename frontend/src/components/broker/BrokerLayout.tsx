import React, { useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  AlertCircle,
  Building2,
  CalendarCheck,
  IndianRupee,
  LayoutDashboard,
  Landmark,
  UserRound,
} from 'lucide-react';
import { useAuth } from '../../lib/auth';
import { platformApi, type ReferredBooking, type ReferredVenue, type Commission, type BrokerPayout } from '../../lib/api/platform';
import { dateOnly, dateTime, errorText, humanize, money, percent, perUnit, slotLabel } from '../../lib/format';
import { DashboardShell, StatusBadge } from '../dashboard';
import {
  Button,
  CopyButton,
  DataTable,
  ExportButton,
  Field,
  Notice,
  Panel,
  Stat,
  inputClass,
  type Column,
} from '../dashboard/kit';

/**
 * The referral partner's dashboard.
 *
 * Everything shown here is fetched from /api/v1/broker/*, which the server
 * scopes to the signed-in partner. Customer names and contact details are
 * never part of it: a partner works with venue owners, and needs booking
 * amounts and payment status to follow their earnings, not who booked.
 */

type Tab = 'overview' | 'venues' | 'bookings' | 'earnings' | 'payouts' | 'profile';

const BASIS_LABEL: Record<string, string> = {
  booking_amount: 'of the booking amount received',
  platform_commission: "of GroundKart's commission on each booking",
};

export default function BrokerLayout({ onReturnToSite }: { onReturnToSite?: () => void }) {
  const { user, logout } = useAuth();
  if (!user) {
    return <Gate text="Please log in with your partner account to continue." />;
  }
  if (user.role !== 'broker') {
    return <Gate text="This dashboard is only for GroundKart referral partners." />;
  }
  return <BrokerDashboard name={user.name} onLogout={logout} onReturnToSite={onReturnToSite} />;
}

function Gate({ text }: { text: string }) {
  return (
    <div className="mx-auto max-w-xl space-y-3 py-24 text-center">
      <AlertCircle size={32} className="mx-auto text-ink/40" aria-hidden="true" />
      <p className="text-on-surface-variant">{text}</p>
    </div>
  );
}

function BrokerDashboard({
  name,
  onLogout,
  onReturnToSite,
}: {
  name: string;
  onLogout: () => Promise<void>;
  onReturnToSite?: () => void;
}) {
  const [tab, setTab] = useState<Tab>('overview');
  const me = useQuery({ queryKey: ['broker-me'], queryFn: platformApi.brokerMe });
  const venues = useQuery({ queryKey: ['broker-venues'], queryFn: platformApi.myReferredVenues });
  const bookings = useQuery({ queryKey: ['broker-bookings'], queryFn: () => platformApi.myReferredBookings() });
  const commissions = useQuery({ queryKey: ['broker-commissions'], queryFn: platformApi.myCommissions });
  const payouts = useQuery({ queryKey: ['broker-payouts'], queryFn: platformApi.myPayouts });

  const navItems = [
    { id: 'overview', label: 'Overview', icon: LayoutDashboard, onClick: () => setTab('overview') },
    { id: 'venues', label: 'My venues', icon: Building2, onClick: () => setTab('venues') },
    { id: 'bookings', label: 'Bookings', icon: CalendarCheck, onClick: () => setTab('bookings') },
    { id: 'earnings', label: 'Earnings', icon: IndianRupee, onClick: () => setTab('earnings') },
    { id: 'payouts', label: 'Payouts', icon: Landmark, onClick: () => setTab('payouts') },
    { id: 'profile', label: 'Profile', icon: UserRound, onClick: () => setTab('profile') },
  ];

  const titles: Record<Tab, [string, string]> = {
    overview: ['Partner dashboard', 'Your referral code, venues and earnings'],
    venues: ['My venues', 'Venues listed with your referral code'],
    bookings: ['Bookings', 'Bookings at your venues and whether they have been paid'],
    earnings: ['Earnings', 'Commission on each paid booking'],
    payouts: ['Payouts', 'Money GroundKart has paid you'],
    profile: ['Profile', 'Your details and where to send payouts'],
  };

  return (
    <DashboardShell
      title={titles[tab][0]}
      description={titles[tab][1]}
      navItems={navItems}
      activeNavId={tab}
      userName={name}
      userRole="Referral partner"
      onLogout={() => void onLogout()}
      onReturnToSite={onReturnToSite}
    >
      {me.isError ? (
        <Notice tone="error">{errorText(me.error, 'Could not load your partner account.')}</Notice>
      ) : null}
      {me.data?.status === 'paused' ? (
        <div className="mb-6">
          <Notice>
            Your partner account is paused. Venues you already referred stay linked to you, but new bookings don't earn
            commission until it is reactivated. Contact the GroundKart team if you think this is a mistake.
          </Notice>
        </div>
      ) : null}

      {tab === 'overview' && (
        <Overview
          me={me.data}
          loading={me.isLoading}
          venues={venues.data ?? []}
          bookings={bookings.data ?? []}
          onGo={setTab}
        />
      )}
      {tab === 'venues' && <VenuesTab rows={venues.data ?? []} loading={venues.isLoading} />}
      {tab === 'bookings' && <BookingsTab rows={bookings.data ?? []} loading={bookings.isLoading} venues={venues.data ?? []} />}
      {tab === 'earnings' && <EarningsTab rows={commissions.data ?? []} loading={commissions.isLoading} me={me.data} />}
      {tab === 'payouts' && <PayoutsTab rows={payouts.data ?? []} loading={payouts.isLoading} me={me.data} />}
      {tab === 'profile' && <ProfileTab me={me.data} />}
    </DashboardShell>
  );
}

type Me = Awaited<ReturnType<typeof platformApi.brokerMe>>;

function Overview({
  me,
  loading,
  venues,
  bookings,
  onGo,
}: {
  me?: Me;
  loading: boolean;
  venues: ReferredVenue[];
  bookings: ReferredBooking[];
  onGo: (t: Tab) => void;
}) {
  const w = me?.wallet;
  const shareText = me
    ? `List your venue on GroundKart. Use my referral code ${me.referral_code} on the first step: ${me.referral_link}`
    : '';
  const recent = bookings.slice(0, 6);
  const inReview = venues.filter((v) => v.status === 'pending_review').length;
  const live = venues.filter((v) => v.status === 'active').length;

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-12">
        <section className="rounded-2xl bg-pitch p-6 text-chalk lg:col-span-5">
          <p className="text-sm text-chalk/75">Your referral code</p>
          {loading || !me ? (
            <div className="mt-2 h-10 w-48 rounded bg-white/10" />
          ) : (
            <>
              <p className="mt-1 font-display text-4xl font-semibold tracking-wide text-marigold tabular">{me.referral_code}</p>
              <p className="mt-3 text-sm text-chalk/80">
                You earn {percent(me.commission_percent)} {BASIS_LABEL[me.commission_basis] ?? ''} at every venue listed with
                this code.
              </p>
              <div className="mt-5 flex flex-wrap gap-2">
                <CopyButton text={me.referral_code} label="Copy code" />
                <CopyButton text={me.referral_link} label="Copy listing link" />
                <a
                  href={`https://wa.me/?text=${encodeURIComponent(shareText)}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center rounded-lg bg-marigold px-3.5 py-2 text-sm font-semibold text-pitch hover:brightness-105"
                >
                  Share on WhatsApp
                </a>
              </div>
            </>
          )}
        </section>

        <div className="grid grid-cols-2 gap-4 lg:col-span-7">
          <Stat label="Ready to be paid" value={w ? money(w.payable) : '—'} hint="Events that have taken place" tone="strong" />
          <Stat label="Coming up" value={w ? money(w.pending) : '—'} hint="Paid bookings, event not yet held" />
          <Stat label="Paid to you so far" value={w ? money(w.paid) : '—'} />
          <Stat
            label="Venues referred"
            value={me ? me.venue_count : '—'}
            hint={me ? `${live} live${inReview ? `, ${inReview} in review` : ''}` : undefined}
          />
        </div>
      </div>

      <Panel
        title="Latest bookings at your venues"
        actions={
          <Button variant="ghost" onClick={() => onGo('bookings')}>
            See all bookings
          </Button>
        }
        padded={false}
      >
        <DataTable rows={recent} columns={bookingColumns} rowKey={(r) => r.id} empty="No bookings at your venues yet." />
      </Panel>

      <Panel title="How your earnings work">
        <ol className="list-decimal space-y-2 pl-5 text-[15px] text-ink">
          <li>A venue owner enters your code when they list. The venue appears under My venues straight away.</li>
          <li>Our team reviews the listing. Once approved, it is live and can take bookings.</li>
          <li>
            When a booking's payment is received and recorded, your commission is added under Coming up. The rate is
            fixed at that moment, so later changes to your terms don't affect it.
          </li>
          <li>After the event date it moves to Ready to be paid, and is settled in the next payout.</li>
          <li>If a booking is refunded, the same share of your commission is taken back.</li>
        </ol>
      </Panel>
    </div>
  );
}

const bookingColumns: Column<ReferredBooking>[] = [
  { key: 'ref', header: 'Booking', cell: (r) => <span className="font-medium tabular">{r.reference}</span> },
  { key: 'venue', header: 'Venue', cell: (r) => r.venue_name },
  {
    key: 'when',
    header: 'Event',
    cell: (r) => (
      <span className="whitespace-nowrap">
        {dateOnly(r.event_date)}
        <span className="block text-xs text-on-surface-variant">{slotLabel(r.start_time, r.end_time)}</span>
      </span>
    ),
  },
  { key: 'status', header: 'Booking status', cell: (r) => <StatusBadge status={r.status} /> },
  { key: 'payment', header: 'Payment', cell: (r) => <StatusBadge status={r.payment_state} /> },
  { key: 'amount', header: 'Amount', align: 'right', cell: (r) => money(r.amount) },
  {
    key: 'commission',
    header: 'Your commission',
    align: 'right',
    cell: (r) =>
      r.commission_amount !== null ? (
        <span>
          {money(r.commission_amount)}
          <span className="block text-xs text-on-surface-variant">{r.commission_status ? humanize(r.commission_status) : ''}</span>
        </span>
      ) : (
        <span className="text-on-surface-variant">—</span>
      ),
  },
];

function VenuesTab({ rows, loading }: { rows: ReferredVenue[]; loading: boolean }) {
  const columns: Column<ReferredVenue>[] = [
    {
      key: 'name',
      header: 'Venue',
      cell: (r) => (
        <span>
          <span className="font-medium">{r.name}</span>
          <span className="block text-xs text-on-surface-variant">
            {humanize(r.category)}, {r.city}
          </span>
        </span>
      ),
    },
    {
      key: 'owner',
      header: 'Owner',
      cell: (r) => (
        <span>
          {r.owner_name}
          {r.owner_phone ? (
            <a href={`tel:${r.owner_phone}`} className="block text-xs text-pitch hover:underline">
              {r.owner_phone}
            </a>
          ) : null}
        </span>
      ),
    },
    {
      key: 'status',
      header: 'Listing',
      cell: (r) => (
        <span>
          <StatusBadge status={r.status} />
          {r.review_note ? <span className="mt-1 block max-w-[220px] text-xs text-clay">{r.review_note}</span> : null}
        </span>
      ),
    },
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
    {
      key: 'bookings',
      header: 'Bookings',
      align: 'right',
      cell: (r) => (
        <span>
          {r.booking_count}
          <span className="block text-xs text-on-surface-variant">
            {r.paid_booking_count} paid{r.awaiting_payment_count ? `, ${r.awaiting_payment_count} awaiting` : ''}
          </span>
        </span>
      ),
    },
    { key: 'received', header: 'Money received', align: 'right', cell: (r) => money(r.amount_received) },
    { key: 'earned', header: 'Your commission', align: 'right', cell: (r) => money(r.commission_earned) },
    { key: 'since', header: 'Referred', cell: (r) => <span className="whitespace-nowrap">{dateOnly(r.referred_at || r.created_at)}</span> },
  ];
  return (
    <Panel
      title={`${rows.length} venue${rows.length === 1 ? '' : 's'}`}
      description="In review means our team is checking the listing. Draft means the owner has not finished it, or was asked to change something."
      actions={<ExportButton onExport={() => platformApi.downloadMyExport('venues')} />}
      padded={false}
    >
      <DataTable
        rows={rows}
        columns={columns}
        rowKey={(r) => r.id}
        loading={loading}
        empty="No venues yet. Share your referral code with venue owners to get started."
      />
    </Panel>
  );
}

function BookingsTab({ rows, loading, venues }: { rows: ReferredBooking[]; loading: boolean; venues: ReferredVenue[] }) {
  const [venueId, setVenueId] = useState('');
  const [payment, setPayment] = useState('');
  const filtered = useMemo(
    () =>
      rows.filter(
        (r) => (!venueId || r.venue_id === venueId) && (!payment || r.payment_state === payment),
      ),
    [rows, venueId, payment],
  );
  return (
    <Panel
      title="Bookings"
      actions={
        <>
          <select aria-label="Venue" className={`${inputClass} w-auto`} value={venueId} onChange={(e) => setVenueId(e.target.value)}>
            <option value="">All venues</option>
            {venues.map((v) => (
              <option key={v.id} value={v.id}>
                {v.name}
              </option>
            ))}
          </select>
          <select aria-label="Payment" className={`${inputClass} w-auto`} value={payment} onChange={(e) => setPayment(e.target.value)}>
            <option value="">Any payment status</option>
            <option value="received">Paid</option>
            <option value="awaiting">Awaiting payment</option>
            <option value="refunded">Refunded</option>
            <option value="partly_refunded">Partly refunded</option>
          </select>
          <ExportButton onExport={() => platformApi.downloadMyExport('bookings')} />
        </>
      }
      padded={false}
    >
      <DataTable rows={filtered} columns={bookingColumns} rowKey={(r) => r.id} loading={loading} empty="No bookings match." />
    </Panel>
  );
}

function EarningsTab({ rows, loading, me }: { rows: Commission[]; loading: boolean; me?: Me }) {
  const columns: Column<Commission>[] = [
    { key: 'ref', header: 'Booking', cell: (r) => <span className="font-medium tabular">{r.booking_reference}</span> },
    { key: 'venue', header: 'Venue', cell: (r) => r.venue_name },
    { key: 'date', header: 'Event date', cell: (r) => <span className="whitespace-nowrap">{dateOnly(r.event_date)}</span> },
    {
      key: 'basis',
      header: 'Calculated on',
      align: 'right',
      cell: (r) => (
        <span>
          {money(r.basis_amount)}
          <span className="block text-xs text-on-surface-variant">at {percent(r.rate)}</span>
        </span>
      ),
    },
    { key: 'amount', header: 'Earned', align: 'right', cell: (r) => money(r.amount) },
    {
      key: 'reversed',
      header: 'Refunded back',
      align: 'right',
      cell: (r) => (Number(r.reversed_amount) > 0 ? <span className="text-clay">−{money(r.reversed_amount)}</span> : '—'),
    },
    { key: 'paid', header: 'Paid', align: 'right', cell: (r) => money(r.paid_amount) },
    { key: 'status', header: 'Status', cell: (r) => <StatusBadge status={r.status} /> },
  ];
  return (
    <div className="space-y-6">
      {me ? (
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
          <Stat label="Total earned" value={money(me.wallet.earned)} hint="After refunds" />
          <Stat label="Coming up" value={money(me.wallet.pending)} />
          <Stat label="Ready to be paid" value={money(me.wallet.payable)} tone="strong" />
          <Stat label="Paid" value={money(me.wallet.paid)} />
        </div>
      ) : null}
      <Panel
        title="Commission by booking"
        description="One line for every paid booking at your venues."
        actions={<ExportButton onExport={() => platformApi.downloadMyExport('commissions')} />}
        padded={false}
      >
        <DataTable rows={rows} columns={columns} rowKey={(r) => r.id} loading={loading} empty="No commission yet." />
      </Panel>
    </div>
  );
}

function PayoutsTab({ rows, loading, me }: { rows: BrokerPayout[]; loading: boolean; me?: Me }) {
  const columns: Column<BrokerPayout>[] = [
    { key: 'date', header: 'Paid on', cell: (r) => <span className="whitespace-nowrap">{dateTime(r.paid_at)}</span> },
    { key: 'amount', header: 'Amount', align: 'right', cell: (r) => <span className="font-semibold">{money(r.amount)}</span> },
    { key: 'method', header: 'Method', cell: (r) => humanize(r.method) },
    { key: 'ref', header: 'Reference', cell: (r) => r.reference || '—' },
    { key: 'notes', header: 'Note', cell: (r) => r.notes || '—' },
  ];
  return (
    <div className="space-y-6">
      {me ? (
        <Notice>
          {Number(me.wallet.payable) > 0
            ? `${money(me.wallet.payable)} is ready to be paid and will be included in your next payout.`
            : 'Nothing is waiting to be paid right now.'}{' '}
          Payouts go to the details in your profile{me.payout_method ? ` (${humanize(me.payout_method)})` : ''}.
        </Notice>
      ) : null}
      <Panel title="Payout history" actions={<ExportButton onExport={() => platformApi.downloadMyExport('payouts')} />} padded={false}>
        <DataTable rows={rows} columns={columns} rowKey={(r) => r.id} loading={loading} empty="No payouts yet." />
      </Panel>
    </div>
  );
}

function ProfileTab({ me }: { me?: Me }) {
  const qc = useQueryClient();
  const [form, setForm] = useState({ company_name: '', city: '', payout_method: '', payout_details: '' });
  const [loadedFor, setLoadedFor] = useState<string | null>(null);
  if (me && loadedFor !== me.id) {
    setLoadedFor(me.id);
    setForm({
      company_name: me.company_name ?? '',
      city: me.city ?? '',
      payout_method: me.payout_method ?? '',
      payout_details: me.payout_details ?? '',
    });
  }
  const save = useMutation({
    mutationFn: () => platformApi.updateBrokerMe(form),
    onSuccess: (data) => qc.setQueryData(['broker-me'], data),
  });

  if (!me) return <div className="h-48 rounded-2xl shimmer" />;

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
      <Panel title="Your details" className="lg:col-span-7">
        <form
          className="space-y-4"
          onSubmit={(e) => {
            e.preventDefault();
            save.mutate();
          }}
        >
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <Field label="Business name" hint="Shown to owners who check your code">
              <input className={inputClass} value={form.company_name} onChange={(e) => setForm({ ...form, company_name: e.target.value })} maxLength={160} />
            </Field>
            <Field label="City">
              <input className={inputClass} value={form.city} onChange={(e) => setForm({ ...form, city: e.target.value })} maxLength={80} />
            </Field>
            <Field label="Payout method">
              <select className={inputClass} value={form.payout_method} onChange={(e) => setForm({ ...form, payout_method: e.target.value })}>
                <option value="">Choose…</option>
                <option value="upi">UPI</option>
                <option value="bank_transfer">Bank transfer</option>
                <option value="cash">Cash</option>
              </select>
            </Field>
            <Field label="Payout details" hint="UPI ID, or account name, number and IFSC">
              <input className={inputClass} value={form.payout_details} onChange={(e) => setForm({ ...form, payout_details: e.target.value })} maxLength={300} />
            </Field>
          </div>
          {save.isError ? <Notice tone="error">{errorText(save.error)}</Notice> : null}
          {save.isSuccess ? <Notice tone="success">Saved.</Notice> : null}
          <Button type="submit" variant="primary" loading={save.isPending}>
            Save details
          </Button>
        </form>
      </Panel>
      <Panel title="Your terms" className="lg:col-span-5">
        <dl className="space-y-3 text-[15px]">
          <div className="flex justify-between gap-4">
            <dt className="text-on-surface-variant">Name</dt>
            <dd className="text-right font-medium">{me.name}</dd>
          </div>
          <div className="flex justify-between gap-4">
            <dt className="text-on-surface-variant">Phone</dt>
            <dd className="text-right font-medium">{me.phone}</dd>
          </div>
          <div className="flex justify-between gap-4">
            <dt className="text-on-surface-variant">Referral code</dt>
            <dd className="text-right font-medium tabular">{me.referral_code}</dd>
          </div>
          <div className="flex justify-between gap-4">
            <dt className="text-on-surface-variant">Commission</dt>
            <dd className="text-right font-medium">
              {percent(me.commission_percent)} <span className="block text-xs font-normal text-on-surface-variant">{BASIS_LABEL[me.commission_basis]}</span>
            </dd>
          </div>
          <div className="flex justify-between gap-4">
            <dt className="text-on-surface-variant">Status</dt>
            <dd>
              <StatusBadge status={me.status} />
            </dd>
          </div>
        </dl>
        <p className="mt-4 text-sm text-on-surface-variant">
          Your rate and code are set by GroundKart. To change your name or phone number, contact the team.
        </p>
      </Panel>
    </div>
  );
}

