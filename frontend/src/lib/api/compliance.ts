import { api } from './client';
import type { LegalProfile } from '../legal';

/** Admin compliance endpoints (backend/app/routers/compliance.py). */

export interface Incident {
  id: string;
  reference: string;
  title: string;
  description: string;
  status: 'open' | 'contained' | 'closed';
  detected_at: string | null;
  occurred_at: string | null;
  data_categories: string[];
  affected_count: number | null;
  is_cyber_incident: boolean;
  is_personal_data_breach: boolean;
  cert_in_due_at: string | null;
  board_report_due_at: string | null;
  cert_in_reported_at: string | null;
  board_initial_reported_at: string | null;
  board_report_submitted_at: string | null;
  users_notified_at: string | null;
  containment_notes: string | null;
  remediation_notes: string | null;
  overdue: ('cert_in' | 'board_report' | 'users_notice')[];
  created_at: string | null;
  closed_at: string | null;
}

export interface IncidentCreate {
  title: string;
  description: string;
  detected_at?: string;
  occurred_at?: string;
  data_categories?: string[];
  affected_count?: number;
  is_cyber_incident: boolean;
  is_personal_data_breach: boolean;
}

export type IncidentUpdate = Partial<
  Pick<
    Incident,
    | 'status'
    | 'cert_in_reported_at'
    | 'board_initial_reported_at'
    | 'board_report_submitted_at'
    | 'users_notified_at'
    | 'containment_notes'
    | 'remediation_notes'
    | 'affected_count'
  >
>;

export interface AdminDataRequest {
  id: string;
  user_id: string | null;
  request_number: string;
  type: string;
  status: 'open' | 'completed' | 'rejected';
  details: string | null;
  due_at: string | null;
  completed_at: string | null;
  created_at: string | null;
  result: Record<string, unknown> | null;
  overdue: boolean;
}

export interface ComplianceSummary {
  tickets: { open: number; ack_overdue: number; resolve_overdue: number; grievances_open: number };
  data_requests: { open: number; overdue: number };
  consents: { purpose: string; action: string; count: number }[];
  incidents: Incident[];
  next_due: {
    id: string;
    ticket_number: string | null;
    subject: string;
    category: string;
    resolve_due_at: string;
    sla_state: string;
  }[];
  legal_profile_missing: string[];
  admin_2fa_required: boolean;
}

export const complianceApi = {
  summary: () => api.get<ComplianceSummary>('/api/v1/admin/compliance/summary'),
  incidents: () => api.get<Incident[]>('/api/v1/admin/compliance/incidents'),
  createIncident: (body: IncidentCreate) => api.post<Incident>('/api/v1/admin/compliance/incidents', body),
  updateIncident: (id: string, body: IncidentUpdate) => api.patch<Incident>(`/api/v1/admin/compliance/incidents/${id}`, body),
  dataRequests: (status?: string) =>
    api.get<AdminDataRequest[]>('/api/v1/admin/compliance/data-requests', { query: status ? { status } : {} }),
  updateDataRequest: (id: string, body: { status: string; note?: string }) =>
    api.patch<AdminDataRequest>(`/api/v1/admin/compliance/data-requests/${id}`, body),
  updateLegalProfile: (body: Partial<Record<keyof LegalProfile, string | null>>) =>
    api.put<LegalProfile>('/api/v1/admin/legal/profile', body),
  revealVerificationNumbers: (verificationId: string) =>
    api.get<Record<string, string | null>>(`/api/v1/admin/owner-verifications/${verificationId}/numbers`),
};

export const twoFactorApi = {
  setup: () => api.post<{ secret: string; otpauth_uri: string }>('/api/v1/auth/2fa/setup', {}),
  enable: (code: string) => api.post<{ enabled: boolean; recovery_codes: string[] }>('/api/v1/auth/2fa/enable', { code }),
};
