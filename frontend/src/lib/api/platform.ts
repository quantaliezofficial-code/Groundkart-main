/**
 * API client for the areas added on top of the original admin console:
 * team (super admin), referral partners, the partner's own dashboard,
 * referral codes, banners, and records & exports.
 *
 * Money arrives as decimal strings ("1250.00") exactly as the server
 * computed it. It is only converted to a number at the point of display
 * (see lib/format.ts), never summed or re-derived in the browser.
 */
import { api } from './client';

// ---- Team ------------------------------------------------------------------

export interface TeamMember {
  id: string;
  name: string;
  email: string | null;
  phone: string;
  is_super_admin: boolean;
  suspended_at: string | null;
  suspension_reason: string | null;
  created_at: string;
  created_by: string | null;
  action_count: number;
  last_action_at: string | null;
}

export interface AccountCreated {
  id: string;
  name: string;
  /** One-time link the new account holder uses to choose a password. Shown once. */
  setup_url: string;
  setup_url_expires_in_hours: number;
}

// ---- Referral partners -----------------------------------------------------

export type CommissionBasis = 'booking_amount' | 'platform_commission';

export interface Wallet {
  earned: string;
  pending: string;
  payable: string;
  paid: string;
  reversed: string;
  commission_count: number;
}

export interface Broker {
  id: string;
  name: string;
  email: string | null;
  phone: string;
  suspended_at: string | null;
  referral_code: string;
  commission_percent: string;
  commission_basis: CommissionBasis;
  status: 'active' | 'paused';
  company_name: string | null;
  city: string | null;
  payout_method: string | null;
  payout_details: string | null;
  notes: string | null;
  created_at: string;
  venue_count: number;
  active_venue_count: number;
  wallet: Wallet;
}

export interface BrokerSelf extends Omit<Broker, 'suspended_at' | 'notes' | 'created_at'> {
  referral_link: string;
}

export interface BrokerCreateBody {
  name: string;
  phone: string;
  email?: string | null;
  commission_percent?: string | null;
  commission_basis?: CommissionBasis | null;
  company_name?: string | null;
  city?: string | null;
  payout_method?: string | null;
  payout_details?: string | null;
  notes?: string | null;
}

export type BrokerUpdateBody = Partial<Omit<BrokerCreateBody, 'phone' | 'email'>> & { status?: 'active' | 'paused' };

export interface ReferredVenue {
  id: string;
  name: string;
  slug: string;
  category: string;
  city: string;
  status: string;
  review_note: string | null;
  base_price: string;
  unit_type: string;
  owner_name: string;
  owner_phone: string | null;
  referral_code: string | null;
  referred_at: string | null;
  created_at: string;
  booking_count: number;
  awaiting_payment_count: number;
  paid_booking_count: number;
  amount_received: string;
  commission_earned: string;
}

export type PaymentState =
  | 'received'
  | 'refunded'
  | 'partly_refunded'
  | 'awaiting'
  | 'received_not_eligible'
  | 'not_received';

export type CommissionStatus = 'pending' | 'payable' | 'paid' | 'reversed' | 'adjustment';

export interface ReferredBooking {
  id: string;
  reference: string;
  venue_id: string;
  venue_name: string;
  event_date: string;
  start_time: string | null;
  end_time: string | null;
  status: string;
  amount: string;
  payment_state: PaymentState;
  created_at: string;
  confirmed_at: string | null;
  commission_rate: string | null;
  commission_amount: string | null;
  commission_status: CommissionStatus | null;
}

export interface Commission {
  id: string;
  broker_id: string;
  broker_name: string;
  venue_id: string;
  venue_name: string;
  booking_id: string;
  booking_reference: string;
  event_date: string;
  basis: CommissionBasis;
  basis_amount: string;
  rate: string;
  amount: string;
  reversed_amount: string;
  paid_amount: string;
  net_amount: string;
  balance_due: string;
  status: CommissionStatus;
  created_at: string;
}

export interface BrokerPayout {
  id: string;
  broker_id: string;
  broker_name: string;
  amount: string;
  method: string | null;
  reference: string | null;
  notes: string | null;
  paid_at: string;
}

export interface VenueReferral {
  venue_id: string;
  referral_code: string | null;
  partner_name: string | null;
  referred_at: string | null;
  locked: boolean;
}

// ---- Banners ---------------------------------------------------------------

export type BannerPlacement = 'home_hero' | 'home_strip' | 'search_top';

export interface PublicBanner {
  id: string;
  placement: BannerPlacement;
  title: string;
  subtitle: string | null;
  image_url: string | null;
  cta_label: string | null;
  cta_url: string | null;
}

export interface Banner extends PublicBanner {
  enabled: boolean;
  priority: number;
  start_at: string | null;
  end_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface BannerBody {
  placement?: BannerPlacement;
  title?: string;
  subtitle?: string | null;
  cta_label?: string | null;
  cta_url?: string | null;
  enabled?: boolean;
  priority?: number;
  start_at?: string | null;
  end_at?: string | null;
}

// ---- Records ---------------------------------------------------------------

export interface VenueRegisterRow {
  id: string;
  name: string;
  slug: string;
  category: string;
  city: string;
  state: string | null;
  address: string;
  capacity: number | null;
  unit_type: string;
  base_price: string;
  status: string;
  status_note: string | null;
  owner_id: string;
  owner_name: string;
  owner_phone: string | null;
  owner_email: string | null;
  broker_id: string | null;
  broker_name: string | null;
  referral_code: string | null;
  referred_at: string | null;
  listed_at: string;
  approved_at: string | null;
  updated_at: string;
  media_count: number;
  booking_count: number;
  confirmed_booking_count: number;
  amount_received: string;
  platform_commission: string;
  avg_rating: string;
}

export interface BookingRegisterRow {
  id: string;
  reference: string;
  status: string;
  booked_at: string;
  confirmed_at: string | null;
  cancelled_at: string | null;
  cancellation_reason: string | null;
  venue_id: string;
  venue_name: string;
  venue_category: string;
  venue_city: string;
  owner_id: string;
  owner_name: string;
  event_date: string;
  start_time: string | null;
  end_time: string | null;
  rental_mode: string | null;
  guest_count: number | null;
  customer_type: 'account' | 'guest';
  customer_name: string | null;
  customer_phone: string | null;
  customer_email: string | null;
  amount: string;
  currency: string;
  payment_received: boolean;
  payment_method: string | null;
  payment_gateway: string | null;
  payment_reference: string | null;
  payment_recorded_at: string | null;
  refund_amount: string;
  amount_received: string;
  platform_commission: string;
  owner_share: string;
  broker_id: string | null;
  broker_name: string | null;
  broker_commission_rate: string | null;
  broker_commission: string | null;
  broker_commission_status: CommissionStatus | null;
}

export interface HistoryEvent {
  at: string;
  action: string;
  label: string;
  actor_name: string | null;
  actor_role: string | null;
  details: Record<string, unknown>;
}

export interface VenueHistory {
  venue_id: string;
  venue_name: string;
  status: string;
  timeline: HistoryEvent[];
  booking_count: number;
  first_booking_at: string | null;
  last_booking_at: string | null;
}

export interface ExportInfo {
  kind: string;
  title: string;
  row_count: number;
  columns: string[];
}

export interface RegisterFilters {
  status?: string;
  city?: string;
  venue_id?: string;
  broker_id?: string;
  referred?: boolean;
  payment?: 'received' | 'awaiting';
  search?: string;
  date_from?: string;
  date_to?: string;
  date_basis?: 'booked' | 'event';
  limit?: number;
  offset?: number;
}

type Query = Record<string, string | number | boolean | undefined>;
const q = (filters: object): Query =>
  Object.fromEntries(Object.entries(filters).filter(([, v]) => v !== undefined && v !== '' && v !== null)) as Query;

export const platformApi = {
  // Team (super admin)
  listTeam: () => api.get<TeamMember[]>('/api/v1/admin/team'),
  createAdmin: (body: { name: string; phone: string; email?: string | null }) =>
    api.post<AccountCreated>('/api/v1/admin/team', body),

  // Referral partners (admin console)
  listBrokers: (params: { search?: string; status?: string } = {}) =>
    api.get<Broker[]>('/api/v1/admin/brokers', { query: q(params) }),
  getBroker: (id: string) => api.get<Broker>(`/api/v1/admin/brokers/${id}`),
  createBroker: (body: BrokerCreateBody) =>
    api.post<{ broker: Broker; setup_url: string; setup_url_expires_in_hours: number }>('/api/v1/admin/brokers', body),
  updateBroker: (id: string, body: BrokerUpdateBody) => api.patch<Broker>(`/api/v1/admin/brokers/${id}`, body),
  regenerateBrokerCode: (id: string) => api.post<Broker>(`/api/v1/admin/brokers/${id}/regenerate-code`, {}),
  reissueBrokerSetupLink: (id: string) => api.post<AccountCreated>(`/api/v1/admin/brokers/${id}/setup-link`, {}),
  brokerVenues: (id: string) => api.get<ReferredVenue[]>(`/api/v1/admin/brokers/${id}/venues`),
  brokerBookings: (id: string) => api.get<ReferredBooking[]>(`/api/v1/admin/brokers/${id}/bookings`),
  brokerCommissions: (id: string) => api.get<Commission[]>(`/api/v1/admin/brokers/${id}/commissions`),
  brokerPayouts: (id: string) => api.get<BrokerPayout[]>(`/api/v1/admin/brokers/${id}/payouts`),
  recordBrokerPayout: (
    id: string,
    body: { expected_amount: string; method?: string; reference?: string; notes?: string },
  ) => api.post<BrokerPayout>(`/api/v1/admin/brokers/${id}/payouts`, body),
  setVenueBroker: (venueId: string, brokerId: string | null) =>
    api.put<VenueReferral>(`/api/v1/admin/venues/${venueId}/broker`, { broker_id: brokerId }),

  // The partner's own dashboard
  brokerMe: () => api.get<BrokerSelf>('/api/v1/broker/me'),
  updateBrokerMe: (body: { company_name?: string; city?: string; payout_method?: string; payout_details?: string }) =>
    api.patch<BrokerSelf>('/api/v1/broker/me', body),
  myReferredVenues: () => api.get<ReferredVenue[]>('/api/v1/broker/venues'),
  myReferredBookings: (venueId?: string) =>
    api.get<ReferredBooking[]>('/api/v1/broker/bookings', { query: q({ venue_id: venueId }) }),
  myCommissions: () => api.get<Commission[]>('/api/v1/broker/commissions'),
  myPayouts: () => api.get<BrokerPayout[]>('/api/v1/broker/payouts'),
  downloadMyExport: (kind: 'venues' | 'bookings' | 'commissions' | 'payouts') =>
    api.download(`/api/v1/broker/export/${kind}.csv`),

  // Referral codes (owner side)
  checkReferralCode: (code: string) =>
    api.post<{ valid: boolean; partner_name: string | null }>('/api/v1/referral-codes/check', { code }),
  getVenueReferral: (venueId: string) => api.get<VenueReferral>(`/api/v1/owner/venues/${venueId}/referral`),
  applyVenueReferral: (venueId: string, code: string) =>
    api.put<VenueReferral>(`/api/v1/owner/venues/${venueId}/referral`, { code }),

  // Banners
  publicBanners: (placement?: BannerPlacement) =>
    api.get<PublicBanner[]>('/api/v1/banners', { query: q({ placement }), skipAuth: true }),
  listBanners: () => api.get<Banner[]>('/api/v1/admin/banners'),
  createBanner: (body: BannerBody & { title: string }) => api.post<Banner>('/api/v1/admin/banners', body),
  updateBanner: (id: string, body: BannerBody) => api.patch<Banner>(`/api/v1/admin/banners/${id}`, body),
  deleteBanner: (id: string) => api.delete<void>(`/api/v1/admin/banners/${id}`),
  uploadBannerImage: (id: string, file: Blob, filename = 'banner.webp') => {
    const form = new FormData();
    form.append('image', file, filename);
    return api.postForm<Banner>(`/api/v1/admin/banners/${id}/image`, form);
  },

  // Records & exports
  listExports: () => api.get<ExportInfo[]>('/api/v1/admin/records/exports'),
  venueRegister: (filters: RegisterFilters = {}) =>
    api.get<VenueRegisterRow[]>('/api/v1/admin/records/venues', { query: q(filters) }),
  bookingRegister: (filters: RegisterFilters = {}) =>
    api.get<BookingRegisterRow[]>('/api/v1/admin/records/bookings', { query: q(filters) }),
  downloadExport: (kind: string, filters: RegisterFilters = {}) => {
    const { limit: _l, offset: _o, referred: _r, payment: _p, ...rest } = filters;
    return api.download(`/api/v1/admin/records/export/${kind}.csv`, q(rest));
  },
  venueHistory: (venueId: string) => api.get<VenueHistory>(`/api/v1/admin/venues/${venueId}/history`),
};
