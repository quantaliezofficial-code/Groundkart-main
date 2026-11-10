import React, { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Plus } from 'lucide-react';
import { platformApi, type TeamMember } from '../../lib/api/platform';
import { adminApi } from '../../lib/api/admin';
import { dateOnly, dateTime, errorText } from '../../lib/format';
import { StatusBadge } from '../dashboard';
import { Button, DataTable, Field, Modal, Notice, Panel, SetupLinkModal, inputClass, type Column } from '../dashboard/kit';

/**
 * Super admin only. Who else can run the console, and what they have done.
 *
 * Admins are never self-registered: the super admin adds them here and
 * hands over a one-time link to set a password. Suspending an admin ends
 * their sessions; their audited history stays.
 */
export default function TeamTab() {
  const qc = useQueryClient();
  const team = useQuery({ queryKey: ['admin-team'], queryFn: platformApi.listTeam });
  const [adding, setAdding] = useState(false);
  const [setup, setSetup] = useState<{ name: string; url: string; hours: number } | null>(null);
  const [suspending, setSuspending] = useState<TeamMember | null>(null);

  const reactivate = useMutation({
    mutationFn: (id: string) => adminApi.reactivateUser(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin-team'] }),
  });

  const columns: Column<TeamMember>[] = [
    {
      key: 'name',
      header: 'Name',
      cell: (m) => (
        <span>
          <span className="font-medium">{m.name}</span>
          <span className="block text-xs text-on-surface-variant">{[m.phone, m.email].filter(Boolean).join(', ')}</span>
        </span>
      ),
    },
    { key: 'role', header: 'Role', cell: (m) => (m.is_super_admin ? 'Super admin' : 'Admin') },
    {
      key: 'status',
      header: 'Status',
      cell: (m) => (
        <span>
          <StatusBadge status={m.suspended_at ? 'suspended' : 'active'} />
          {m.suspension_reason ? <span className="mt-1 block text-xs text-on-surface-variant">{m.suspension_reason}</span> : null}
        </span>
      ),
    },
    { key: 'actions', header: 'Recorded actions', align: 'right', cell: (m) => m.action_count },
    { key: 'last', header: 'Last action', cell: (m) => <span className="whitespace-nowrap">{dateTime(m.last_action_at)}</span> },
    { key: 'since', header: 'Added', cell: (m) => <span className="whitespace-nowrap">{dateOnly(m.created_at)}</span> },
    {
      key: 'manage',
      header: '',
      cell: (m) =>
        m.is_super_admin ? null : m.suspended_at ? (
          <Button onClick={() => reactivate.mutate(m.id)} loading={reactivate.isPending && reactivate.variables === m.id}>
            Reactivate
          </Button>
        ) : (
          <Button variant="danger" onClick={() => setSuspending(m)}>
            Suspend
          </Button>
        ),
    },
  ];

  return (
    <div className="space-y-6">
      <Panel
        title="Admin team"
        description="Admins can approve listings, confirm payments, manage partners, banners and records. Only you can add or remove admins, change commission terms, or change partner rates."
        actions={
          <Button variant="primary" onClick={() => setAdding(true)}>
            <Plus size={15} aria-hidden="true" /> Add admin
          </Button>
        }
        padded={false}
      >
        {team.isError ? (
          <div className="p-5">
            <Notice tone="error">{errorText(team.error)}</Notice>
          </div>
        ) : (
          <DataTable rows={team.data ?? []} columns={columns} rowKey={(m) => m.id} loading={team.isLoading} />
        )}
        {reactivate.isError ? (
          <div className="p-5 pt-0">
            <Notice tone="error">{errorText(reactivate.error)}</Notice>
          </div>
        ) : null}
      </Panel>

      {adding && (
        <AddAdminModal
          onClose={() => setAdding(false)}
          onCreated={(name, url, hours) => {
            setAdding(false);
            setSetup({ name, url, hours });
            qc.invalidateQueries({ queryKey: ['admin-team'] });
          }}
        />
      )}
      {setup && <SetupLinkModal name={setup.name} url={setup.url} hours={setup.hours} onClose={() => setSetup(null)} />}
      {suspending && (
        <SuspendModal
          member={suspending}
          onClose={() => setSuspending(null)}
          onDone={() => {
            setSuspending(null);
            qc.invalidateQueries({ queryKey: ['admin-team'] });
          }}
        />
      )}
    </div>
  );
}

function AddAdminModal({ onClose, onCreated }: { onClose: () => void; onCreated: (name: string, url: string, hours: number) => void }) {
  const [name, setName] = useState('');
  const [phone, setPhone] = useState('');
  const [email, setEmail] = useState('');
  const create = useMutation({
    mutationFn: () => platformApi.createAdmin({ name: name.trim(), phone: phone.trim(), email: email.trim() || null }),
    onSuccess: (r) => onCreated(r.name, r.setup_url, r.setup_url_expires_in_hours),
  });
  return (
    <Modal
      title="Add an admin"
      onClose={onClose}
      footer={
        <>
          <Button onClick={onClose}>Cancel</Button>
          <Button
            variant="primary"
            loading={create.isPending}
            disabled={name.trim().length < 2 || phone.trim().length < 10}
            onClick={() => create.mutate()}
          >
            Add admin
          </Button>
        </>
      }
    >
      <div className="space-y-4">
        <Field label="Full name">
          <input className={inputClass} value={name} onChange={(e) => setName(e.target.value)} autoFocus maxLength={120} />
        </Field>
        <Field label="Mobile number" hint="They sign in with this">
          <input className={inputClass} value={phone} onChange={(e) => setPhone(e.target.value)} inputMode="tel" />
        </Field>
        <Field label="Email (optional)">
          <input className={inputClass} value={email} onChange={(e) => setEmail(e.target.value)} type="email" />
        </Field>
        <Notice>You'll get a one-time link to send them. They choose their own password; nobody else sees it.</Notice>
        {create.isError ? <Notice tone="error">{errorText(create.error)}</Notice> : null}
      </div>
    </Modal>
  );
}

function SuspendModal({ member, onClose, onDone }: { member: TeamMember; onClose: () => void; onDone: () => void }) {
  const [reason, setReason] = useState('');
  const suspend = useMutation({ mutationFn: () => adminApi.suspendUser(member.id, reason.trim()), onSuccess: onDone });
  return (
    <Modal
      title={`Suspend ${member.name}`}
      onClose={onClose}
      footer={
        <>
          <Button onClick={onClose}>Cancel</Button>
          <Button variant="danger" loading={suspend.isPending} disabled={reason.trim().length < 3} onClick={() => suspend.mutate()}>
            Suspend admin
          </Button>
        </>
      }
    >
      <p className="text-[15px] text-ink">They are signed out everywhere and can't sign in until reactivated. Everything they did stays in the audit log.</p>
      <Field label="Reason" className="mt-4">
        <input className={inputClass} value={reason} onChange={(e) => setReason(e.target.value)} maxLength={300} autoFocus />
      </Field>
      {suspend.isError ? (
        <div className="mt-3">
          <Notice tone="error">{errorText(suspend.error)}</Notice>
        </div>
      ) : null}
    </Modal>
  );
}
