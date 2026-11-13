import React, { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { AlertTriangle, Plus } from 'lucide-react';
import {
  complianceApi,
  type AdminDataRequest,
  type Incident,
  type IncidentCreate,
  type IncidentUpdate,
} from '../../lib/api/compliance';
import { LEGAL_PROFILE_FIELDS } from '../../lib/legal';
import { dateTime, errorText, humanize } from '../../lib/format';
import { Button, DataTable, Field, Modal, Notice, Panel, Stat, Tabs, inputClass } from '../dashboard/kit';
import TwoStepSetup from './TwoStepSetup';

/**
 * Privacy and compliance: one place for the Grievance Officer and the
 * admins. Complaint and data-request clocks, personal-data incidents with
 * their CERT-In and Data Protection Board deadlines, and sign-in security.
 * The procedure behind it is docs/compliance/drafts/breach-response-plan.md.
 */

type View = 'overview' | 'incidents' | 'requests' | 'security';

const OVERDUE_LABEL: Record<string, string> = {
  cert_in: 'CERT-In report (6 h)',
  board_report: 'Board report (72 h)',
  users_notice: 'Notice to affected people',
};

function Badge({ tone, children }: { tone: 'red' | 'amber' | 'green' | 'grey'; children: React.ReactNode }) {
  const cls = {
    red: 'bg-clay/10 text-clay',
    amber: 'bg-marigold/20 text-pitch',
    green: 'bg-primary-container/10 text-primary-container',
    grey: 'bg-surface-container text-on-surface-variant',
  }[tone];
  return <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-semibold ${cls}`}>{children}</span>;
}

export function SlaBadge({ state }: { state: string | null | undefined }) {
  if (!state) return null;
  const label: Record<string, string> = {
    ack_overdue: 'Reply overdue',
    resolve_overdue: 'Resolution overdue',
    on_track: 'On track',
    done: 'Done',
  };
  const tone = state.includes('overdue') ? 'red' : state === 'done' ? 'green' : 'grey';
  return <Badge tone={tone}>{label[state] ?? humanize(state)}</Badge>;
}

/* ------------------------------------------------------------------ */

function Overview({ go }: { go: (v: View) => void }) {
  const summary = useQuery({ queryKey: ['compliance-summary'], queryFn: complianceApi.summary, refetchInterval: 60_000 });
  if (summary.isError) return <Notice tone="error">{errorText(summary.error)}</Notice>;
  if (!summary.data) return <div className="h-64 rounded-2xl shimmer" />;
  const s = summary.data;
  const missingLabels = s.legal_profile_missing.map((k) => LEGAL_PROFILE_FIELDS.find((f) => f.key === k)?.label ?? k);

  return (
    <div className="space-y-6">
      {s.incidents.some((i) => i.overdue.length) ? (
        <Notice tone="error">
          An open incident has a missed reporting deadline.{' '}
          <button type="button" className="font-semibold underline cursor-pointer" onClick={() => go('incidents')}>
            Open incidents
          </button>
        </Notice>
      ) : null}
      {missingLabels.length ? (
        <Notice>
          Legal pages and the footer still show placeholders for: {missingLabels.join(', ')}. The super admin fills these in
          Rules and fees, under Legal and business details.
        </Notice>
      ) : null}

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Stat label="Open tickets" value={s.tickets.open} hint={`${s.tickets.grievances_open} grievance or data`} />
        <Stat label="Not acknowledged in time" value={s.tickets.ack_overdue} tone={s.tickets.ack_overdue ? 'strong' : 'default'} />
        <Stat label="Past resolution date" value={s.tickets.resolve_overdue} tone={s.tickets.resolve_overdue ? 'strong' : 'default'} />
        <Stat label="Open data requests" value={s.data_requests.open} hint={`${s.data_requests.overdue} overdue`} />
      </div>

      <Panel title="Due next" description="Open tickets by resolution date. Reply from Support tickets." padded={false}>
        <DataTable
          rows={s.next_due}
          rowKey={(r) => r.id}
          empty="Nothing open."
          columns={[
            { key: 'n', header: 'Ticket', cell: (r) => <span className="font-mono text-xs">{r.ticket_number ?? '—'}</span> },
            { key: 's', header: 'Subject', cell: (r) => r.subject },
            { key: 'c', header: 'Type', cell: (r) => humanize(r.category) },
            { key: 'd', header: 'Resolve by', cell: (r) => dateTime(r.resolve_due_at) },
            { key: 'st', header: 'Status', cell: (r) => <SlaBadge state={r.sla_state} /> },
          ]}
        />
      </Panel>

      <Panel title="Consent records" description="Counts of recorded agreements and withdrawals. Records are never edited or deleted." padded={false}>
        <DataTable
          rows={s.consents}
          rowKey={(r) => `${r.purpose}-${r.action}`}
          empty="No consent records yet."
          columns={[
            { key: 'p', header: 'Purpose', cell: (r) => humanize(r.purpose) },
            { key: 'a', header: 'Action', cell: (r) => humanize(r.action) },
            { key: 'c', header: 'Count', align: 'right', cell: (r) => r.count },
          ]}
        />
      </Panel>
    </div>
  );
}

/* ------------------------------------------------------------------ */

function toIsoOrUndefined(local: string): string | undefined {
  return local ? new Date(local).toISOString() : undefined;
}

function NewIncident({ onClose }: { onClose: () => void }) {
  const qc = useQueryClient();
  const [form, setForm] = useState({
    title: '',
    description: '',
    detected_at: '',
    occurred_at: '',
    data_categories: '',
    affected_count: '',
    is_cyber_incident: true,
    is_personal_data_breach: true,
  });
  const create = useMutation({
    mutationFn: () => {
      const body: IncidentCreate = {
        title: form.title.trim(),
        description: form.description.trim(),
        detected_at: toIsoOrUndefined(form.detected_at),
        occurred_at: toIsoOrUndefined(form.occurred_at),
        data_categories: form.data_categories.split(',').map((s) => s.trim()).filter(Boolean),
        affected_count: form.affected_count ? Number(form.affected_count) : undefined,
        is_cyber_incident: form.is_cyber_incident,
        is_personal_data_breach: form.is_personal_data_breach,
      };
      return complianceApi.createIncident(body);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['compliance-incidents'] });
      qc.invalidateQueries({ queryKey: ['compliance-summary'] });
      onClose();
    },
  });

  return (
    <Modal
      title="Record an incident"
      onClose={onClose}
      wide
      footer={
        <>
          <Button onClick={onClose}>Cancel</Button>
          <Button variant="primary" loading={create.isPending} disabled={form.title.trim().length < 3 || !form.description.trim()} onClick={() => create.mutate()}>
            Record incident
          </Button>
        </>
      }
    >
      <div className="space-y-4">
        <Notice>
          Recording starts the clocks: CERT-In within 6 hours of noticing a cyber incident, the Data Protection Board within 72
          hours of becoming aware of a personal data breach, and affected people without delay. Follow the breach response plan.
        </Notice>
        <Field label="Short title">
          <input className={inputClass} value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} />
        </Field>
        <Field label="What happened" hint="Facts only: what was seen, when, which systems.">
          <textarea className={`${inputClass} min-h-[110px]`} value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
        </Field>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <Field label="Noticed at" hint="Leave empty for now.">
            <input type="datetime-local" className={inputClass} value={form.detected_at} onChange={(e) => setForm({ ...form, detected_at: e.target.value })} />
          </Field>
          <Field label="Started at (if known)">
            <input type="datetime-local" className={inputClass} value={form.occurred_at} onChange={(e) => setForm({ ...form, occurred_at: e.target.value })} />
          </Field>
          <Field label="Data involved" hint="Comma separated, e.g. names, phone numbers, ID documents">
            <input className={inputClass} value={form.data_categories} onChange={(e) => setForm({ ...form, data_categories: e.target.value })} />
          </Field>
          <Field label="People affected (estimate)">
            <input className={inputClass} inputMode="numeric" value={form.affected_count} onChange={(e) => setForm({ ...form, affected_count: e.target.value.replace(/\D/g, '') })} />
          </Field>
        </div>
        <label className="flex items-center gap-2 text-sm text-ink">
          <input type="checkbox" checked={form.is_cyber_incident} onChange={(e) => setForm({ ...form, is_cyber_incident: e.target.checked })} />
          Cyber security incident (CERT-In reporting applies)
        </label>
        <label className="flex items-center gap-2 text-sm text-ink">
          <input type="checkbox" checked={form.is_personal_data_breach} onChange={(e) => setForm({ ...form, is_personal_data_breach: e.target.checked })} />
          Personal data breach (Board and affected people must be told)
        </label>
        {create.isError ? <Notice tone="error">{errorText(create.error)}</Notice> : null}
      </div>
    </Modal>
  );
}

const MARKS: { key: keyof IncidentUpdate; label: string }[] = [
  { key: 'cert_in_reported_at', label: 'Reported to CERT-In' },
  { key: 'board_initial_reported_at', label: 'First notice to the Board' },
  { key: 'users_notified_at', label: 'Affected people told' },
  { key: 'board_report_submitted_at', label: 'Full report to the Board' },
];

function IncidentDetail({ incident, onClose }: { incident: Incident; onClose: () => void }) {
  const qc = useQueryClient();
  const [notes, setNotes] = useState({ containment_notes: incident.containment_notes ?? '', remediation_notes: incident.remediation_notes ?? '' });
  const update = useMutation({
    mutationFn: (body: IncidentUpdate) => complianceApi.updateIncident(incident.id, body),
    onSuccess: (data) => {
      qc.setQueryData<Incident[]>(['compliance-incidents'], (old) => old?.map((i) => (i.id === data.id ? data : i)));
      qc.invalidateQueries({ queryKey: ['compliance-summary'] });
    },
  });
  const current = (qc.getQueryData<Incident[]>(['compliance-incidents']) ?? []).find((i) => i.id === incident.id) ?? incident;

  return (
    <Modal title={`${current.reference} · ${current.title}`} onClose={onClose} wide>
      <div className="space-y-5">
        <p className="whitespace-pre-wrap text-sm text-ink">{current.description}</p>
        <dl className="grid grid-cols-1 gap-3 text-sm sm:grid-cols-2">
          <div>
            <dt className="text-on-surface-variant">Noticed</dt>
            <dd>{dateTime(current.detected_at)}</dd>
          </div>
          {current.is_cyber_incident ? (
            <div>
              <dt className="text-on-surface-variant">CERT-In due</dt>
              <dd>{dateTime(current.cert_in_due_at)}</dd>
            </div>
          ) : null}
          {current.is_personal_data_breach ? (
            <div>
              <dt className="text-on-surface-variant">Board report due</dt>
              <dd>{dateTime(current.board_report_due_at)}</dd>
            </div>
          ) : null}
          <div>
            <dt className="text-on-surface-variant">Status</dt>
            <dd>{humanize(current.status)}</dd>
          </div>
        </dl>

        <div className="space-y-2">
          <h3 className="text-sm font-semibold text-ink">Steps done</h3>
          {MARKS.filter((m) => (m.key === 'cert_in_reported_at' ? current.is_cyber_incident : current.is_personal_data_breach)).map((m) => {
            const done = current[m.key as keyof Incident] as string | null;
            return (
              <div key={m.key} className="flex flex-wrap items-center justify-between gap-2 rounded-lg bg-surface-container-low px-3 py-2 text-sm">
                <span>{m.label}</span>
                {done ? (
                  <span className="text-on-surface-variant">{dateTime(done)}</span>
                ) : (
                  <Button loading={update.isPending} onClick={() => update.mutate({ [m.key]: new Date().toISOString() } as IncidentUpdate)}>
                    Mark done now
                  </Button>
                )}
              </div>
            );
          })}
        </div>

        <Field label="Containment">
          <textarea className={`${inputClass} min-h-[80px]`} value={notes.containment_notes} onChange={(e) => setNotes({ ...notes, containment_notes: e.target.value })} />
        </Field>
        <Field label="Fix and follow-up">
          <textarea className={`${inputClass} min-h-[80px]`} value={notes.remediation_notes} onChange={(e) => setNotes({ ...notes, remediation_notes: e.target.value })} />
        </Field>
        {update.isError ? <Notice tone="error">{errorText(update.error)}</Notice> : null}
        <div className="flex flex-wrap gap-2">
          <Button variant="primary" loading={update.isPending} onClick={() => update.mutate(notes)}>
            Save notes
          </Button>
          {current.status === 'open' ? <Button onClick={() => update.mutate({ status: 'contained' })}>Mark contained</Button> : null}
          {current.status !== 'closed' ? (
            <Button variant="danger" onClick={() => update.mutate({ ...notes, status: 'closed' })}>
              Close incident
            </Button>
          ) : null}
        </div>
      </div>
    </Modal>
  );
}

function Incidents() {
  const incidents = useQuery({ queryKey: ['compliance-incidents'], queryFn: complianceApi.incidents });
  const [creating, setCreating] = useState(false);
  const [open, setOpen] = useState<Incident | null>(null);

  return (
    <Panel
      title="Incidents"
      description="Security incidents and personal data breaches, with their reporting deadlines."
      padded={false}
      actions={
        <Button variant="primary" onClick={() => setCreating(true)}>
          <Plus size={15} aria-hidden="true" /> Record an incident
        </Button>
      }
    >
      {incidents.isError ? <div className="p-5"><Notice tone="error">{errorText(incidents.error)}</Notice></div> : null}
      <DataTable<Incident>
        rows={incidents.data ?? []}
        loading={incidents.isLoading}
        rowKey={(r) => r.id}
        onRowClick={(r: Incident) => setOpen(r)}
        empty="No incidents recorded."
        columns={[
          { key: 'r', header: 'Reference', cell: (r) => <span className="font-mono text-xs">{r.reference}</span> },
          { key: 't', header: 'Title', cell: (r) => r.title },
          { key: 'd', header: 'Noticed', cell: (r) => dateTime(r.detected_at) },
          { key: 's', header: 'Status', cell: (r) => <Badge tone={r.status === 'closed' ? 'green' : r.status === 'contained' ? 'amber' : 'red'}>{humanize(r.status)}</Badge> },
          {
            key: 'o',
            header: 'Overdue',
            cell: (r) =>
              r.overdue.length ? (
                <span className="inline-flex items-center gap-1 text-xs font-semibold text-clay">
                  <AlertTriangle size={13} aria-hidden="true" />
                  {r.overdue.map((o) => OVERDUE_LABEL[o] ?? o).join(', ')}
                </span>
              ) : (
                '—'
              ),
          },
        ]}
      />
      {creating ? <NewIncident onClose={() => setCreating(false)} /> : null}
      {open ? <IncidentDetail incident={open} onClose={() => setOpen(null)} /> : null}
    </Panel>
  );
}

/* ------------------------------------------------------------------ */

function DataRequests() {
  const qc = useQueryClient();
  const [status, setStatus] = useState<'open' | ''>('open');
  const [closing, setClosing] = useState<{ req: AdminDataRequest; to: 'completed' | 'rejected' } | null>(null);
  const [note, setNote] = useState('');
  const requests = useQuery({ queryKey: ['compliance-requests', status], queryFn: () => complianceApi.dataRequests(status || undefined) });
  const update = useMutation({
    mutationFn: () => complianceApi.updateDataRequest(closing!.req.id, { status: closing!.to, note: note.trim() || undefined }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['compliance-requests'] });
      qc.invalidateQueries({ queryKey: ['compliance-summary'] });
      setClosing(null);
      setNote('');
    },
  });

  return (
    <Panel
      title="Data requests"
      description="Requests to see, correct or erase personal data, or to name a nominee. Downloads and self-service erasures are completed automatically."
      padded={false}
      actions={
        <Tabs<'open' | 'all'>
          value={status || 'all'}
          onChange={(v) => setStatus(v === 'all' ? '' : 'open')}
          items={[
            { id: 'open', label: 'Open' },
            { id: 'all', label: 'All' },
          ]}
        />
      }
    >
      <DataTable
        rows={requests.data ?? []}
        loading={requests.isLoading}
        rowKey={(r) => r.id}
        empty="No requests."
        columns={[
          { key: 'n', header: 'Request', cell: (r) => <span className="font-mono text-xs">{r.request_number}</span> },
          { key: 't', header: 'Type', cell: (r) => humanize(r.type) },
          { key: 'd', header: 'Details', cell: (r) => <span className="line-clamp-2 max-w-[320px]">{r.details || '—'}</span> },
          { key: 'due', header: 'Due', cell: (r) => (r.overdue ? <Badge tone="red">{dateTime(r.due_at)}</Badge> : dateTime(r.due_at)) },
          { key: 's', header: 'Status', cell: (r) => humanize(r.status) },
          {
            key: 'a',
            header: '',
            cell: (r) =>
              r.status === 'open' ? (
                <div className="flex gap-1.5">
                  <Button onClick={() => setClosing({ req: r, to: 'completed' })}>Done</Button>
                  <Button variant="ghost" onClick={() => setClosing({ req: r, to: 'rejected' })}>
                    Decline
                  </Button>
                </div>
              ) : null,
          },
        ]}
      />
      {closing ? (
        <Modal
          title={`${closing.to === 'completed' ? 'Complete' : 'Decline'} ${closing.req.request_number}`}
          onClose={() => setClosing(null)}
          footer={
            <>
              <Button onClick={() => setClosing(null)}>Cancel</Button>
              <Button variant="primary" loading={update.isPending} disabled={closing.to === 'rejected' && !note.trim()} onClick={() => update.mutate()}>
                Save
              </Button>
            </>
          }
        >
          <Field label={closing.to === 'rejected' ? 'Reason (required, shown to the person)' : 'Note (optional)'}>
            <textarea className={`${inputClass} min-h-[100px]`} value={note} onChange={(e) => setNote(e.target.value)} />
          </Field>
          {update.isError ? <div className="mt-3"><Notice tone="error">{errorText(update.error)}</Notice></div> : null}
        </Modal>
      ) : null}
    </Panel>
  );
}

/* ------------------------------------------------------------------ */

export default function ComplianceTab() {
  const [view, setView] = useState<View>('overview');
  return (
    <div className="space-y-6" data-testid="compliance-tab">
      <Tabs<View>
        value={view}
        onChange={setView}
        items={[
          { id: 'overview', label: 'Overview' },
          { id: 'incidents', label: 'Incidents' },
          { id: 'requests', label: 'Data requests' },
          { id: 'security', label: 'Sign-in security' },
        ]}
      />
      {view === 'overview' ? <Overview go={setView} /> : null}
      {view === 'incidents' ? <Incidents /> : null}
      {view === 'requests' ? <DataRequests /> : null}
      {view === 'security' ? <TwoStepSetup /> : null}
    </div>
  );
}
