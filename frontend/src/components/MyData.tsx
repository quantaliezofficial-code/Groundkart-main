import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Download, FileText, Loader2, PencilLine, ShieldCheck, Trash2, UserPlus, XCircle } from 'lucide-react';
import SEOHead from './SEOHead';
import { SITE_NAME, absUrl } from '../lib/site';
import { api, ApiError } from '../lib/api/client';
import { useAuth } from '../lib/auth';

interface DataRequest {
  request_number: string;
  type: string;
  status: string;
  due_at: string | null;
  completed_at: string | null;
  created_at: string | null;
}

interface Consent {
  id: string;
  purpose: string;
  action: string;
  terms_version: string | null;
  notice_version: string | null;
  created_at: string | null;
}

interface Nominee {
  name: string;
  relationship: string | null;
  email: string | null;
  phone: string | null;
}

const PURPOSE_LABEL: Record<string, string> = {
  terms: 'Terms of Service',
  privacy_notice: 'Privacy Notice',
  age_18_plus: 'Confirmed 18 or older',
};

const fmt = (iso: string | null) =>
  iso ? new Date(iso).toLocaleString('en-IN', { day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' }) : '—';

function Card({ icon, title, children }: { icon: React.ReactNode; title: string; children: React.ReactNode }) {
  return (
    <section className="rounded-2xl bg-chalk p-6 ring-1 ring-ink/5">
      <div className="flex items-center gap-3">
        <span className="grid h-9 w-9 place-items-center rounded-xl bg-pitch/10 text-pitch">{icon}</span>
        <h2 className="text-base font-bold text-ink">{title}</h2>
      </div>
      <div className="mt-4 text-sm leading-6 text-on-surface-variant">{children}</div>
    </section>
  );
}

const input =
  'w-full rounded-xl border border-ink/15 bg-white px-3 py-2.5 text-sm text-ink placeholder:text-ink/40 focus:border-pitch focus:outline-none focus:ring-2 focus:ring-pitch/20';
const primary = 'inline-flex items-center gap-2 rounded-full bg-pitch px-5 py-2.5 text-sm font-semibold text-chalk hover:bg-pitch/90 disabled:opacity-60';
const secondary = 'inline-flex items-center gap-2 rounded-full px-5 py-2.5 text-sm font-semibold text-pitch ring-1 ring-pitch/30 hover:bg-pitch/5 disabled:opacity-60';
const danger = 'inline-flex items-center gap-2 rounded-full bg-clay px-5 py-2.5 text-sm font-semibold text-chalk hover:bg-clay/90 disabled:opacity-60';

export default function MyData({ onRequestAuth }: { onRequestAuth: () => void }) {
  const { user, isLoading, logout, refreshUser } = useAuth();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const consents = useQuery({ queryKey: ['me-consents'], queryFn: () => api.get<Consent[]>('/api/v1/me/consents'), enabled: !!user });
  const requests = useQuery({ queryKey: ['me-requests'], queryFn: () => api.get<DataRequest[]>('/api/v1/me/data-requests'), enabled: !!user });
  const nomineeQ = useQuery({ queryKey: ['me-nominee'], queryFn: () => api.get<Nominee | null>('/api/v1/me/nominee'), enabled: !!user });

  const [profile, setProfile] = useState({ name: '', email: '', phone: '' });
  const [nominee, setNominee] = useState<Nominee>({ name: '', relationship: '', email: '', phone: '' });
  const [correction, setCorrection] = useState('');
  const [confirmDelete, setConfirmDelete] = useState('');
  const [confirmWithdraw, setConfirmWithdraw] = useState(false);

  useEffect(() => {
    if (user) setProfile({ name: user.name || '', email: user.email || '', phone: user.phone || '' });
  }, [user]);
  useEffect(() => {
    if (nomineeQ.data) setNominee({ ...nomineeQ.data, relationship: nomineeQ.data.relationship || '', email: nomineeQ.data.email || '', phone: nomineeQ.data.phone || '' });
  }, [nomineeQ.data]);

  const run = (fn: () => Promise<unknown>, ok: string) => async () => {
    setError(null);
    setNotice(null);
    try {
      await fn();
      setNotice(ok);
    } catch (e) {
      setError(e instanceof ApiError ? e.detail : 'Something went wrong. Please try again.');
    }
  };

  const saveProfile = useMutation({
    mutationFn: () => api.patch('/api/v1/users/me', { name: profile.name, email: profile.email || undefined, phone: profile.phone }),
    onSuccess: () => refreshUser(),
  });
  const saveNominee = useMutation({
    mutationFn: () =>
      api.put('/api/v1/me/nominee', {
        name: nominee.name,
        relationship: nominee.relationship || null,
        email: nominee.email || null,
        phone: nominee.phone || null,
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['me-nominee'] }),
  });
  const askCorrection = useMutation({
    mutationFn: () => api.post<DataRequest>('/api/v1/me/data-requests', { type: 'correction', details: correction }),
    onSuccess: () => {
      setCorrection('');
      qc.invalidateQueries({ queryKey: ['me-requests'] });
    },
  });

  const finish = async (path: string, body: unknown) => {
    const res = await api.post<{ request_number: string }>(path, body);
    await logout();
    navigate(`/your-data?closed=${encodeURIComponent(res.request_number)}`);
  };

  if (isLoading) return <div className="min-h-[60vh]" />;

  return (
    <div className="min-h-screen bg-[#FDFBF7] pb-16 pt-10 sm:pt-14">
      <SEOHead title={`My data | ${SITE_NAME}`} description="Download, correct or delete your personal data." canonicalUrl={absUrl('/account/data')} noindex />
      <div className="mx-auto max-w-4xl px-5 sm:px-6">
        <h1 className="font-display text-3xl font-bold text-pitch sm:text-4xl">My data</h1>
        <p className="mt-2 max-w-2xl text-on-surface-variant">
          Everything you can do with the personal data GroundKart holds about you. The rules behind each option are on{' '}
          <a href="/your-data" onClick={(e) => { e.preventDefault(); navigate('/your-data'); }} className="font-medium text-pitch underline underline-offset-2">
            Your Data Rights
          </a>
          .
        </p>

        {!user ? (
          <div className="mt-8 rounded-2xl bg-chalk p-6 ring-1 ring-ink/5">
            <p className="text-ink">Sign in to download, correct or delete your data, withdraw consent or name a nominee.</p>
            <p className="mt-1 text-sm text-on-surface-variant">Booked as a guest? Use the private link from your booking, or contact the Grievance Officer.</p>
            <button type="button" className={`${primary} mt-4`} onClick={onRequestAuth}>Sign in</button>
          </div>
        ) : (
          <div className="mt-8 space-y-5">
            {(notice || error) && (
              <p role="status" className={`rounded-xl px-4 py-3 text-sm ${error ? 'bg-clay/10 text-clay' : 'bg-pitch/10 text-pitch'}`}>{error || notice}</p>
            )}

            <Card icon={<Download size={18} />} title="Download my data">
              <p>A JSON file with your profile, bookings, payments, tickets, reviews, consents and who received your data.</p>
              <button type="button" className={`${primary} mt-4`} onClick={run(() => api.download('/api/v1/me/data/export'), 'Your data file has been downloaded.')}>
                <Download size={16} /> Download my data
              </button>
            </Card>

            <Card icon={<PencilLine size={18} />} title="Correct my details">
              <form
                className="grid gap-3 sm:grid-cols-3"
                onSubmit={(e) => {
                  e.preventDefault();
                  run(() => saveProfile.mutateAsync(), 'Your details have been updated.')();
                }}
              >
                <label className="text-xs font-semibold text-ink">Name<input className={`${input} mt-1`} value={profile.name} onChange={(e) => setProfile({ ...profile, name: e.target.value })} /></label>
                <label className="text-xs font-semibold text-ink">Email<input type="email" className={`${input} mt-1`} value={profile.email} onChange={(e) => setProfile({ ...profile, email: e.target.value })} /></label>
                <label className="text-xs font-semibold text-ink">Phone<input className={`${input} mt-1`} value={profile.phone} onChange={(e) => setProfile({ ...profile, phone: e.target.value })} /></label>
                <div className="sm:col-span-3"><button type="submit" className={secondary} disabled={saveProfile.isPending}>Save details</button></div>
              </form>
              <form
                className="mt-5 border-t border-ink/10 pt-4"
                onSubmit={(e) => {
                  e.preventDefault();
                  if (correction.trim()) run(() => askCorrection.mutateAsync(), 'Request received. You can follow it below.')();
                }}
              >
                <label className="text-xs font-semibold text-ink" htmlFor="correction">Something else wrong (a booking, a payment record)?</label>
                <textarea id="correction" rows={2} className={`${input} mt-1`} value={correction} onChange={(e) => setCorrection(e.target.value)} placeholder="Tell us what to correct" />
                <button type="submit" className={`${secondary} mt-2`} disabled={!correction.trim() || askCorrection.isPending}>Ask for a correction</button>
              </form>
            </Card>

            <Card icon={<UserPlus size={18} />} title="Nominee">
              <p>Someone who can use these rights for you if you die or cannot act yourself.</p>
              <form
                className="mt-3 grid gap-3 sm:grid-cols-2"
                onSubmit={(e) => {
                  e.preventDefault();
                  run(() => saveNominee.mutateAsync(), 'Nominee saved.')();
                }}
              >
                <label className="text-xs font-semibold text-ink">Full name<input required className={`${input} mt-1`} value={nominee.name} onChange={(e) => setNominee({ ...nominee, name: e.target.value })} /></label>
                <label className="text-xs font-semibold text-ink">Relationship<input className={`${input} mt-1`} value={nominee.relationship || ''} onChange={(e) => setNominee({ ...nominee, relationship: e.target.value })} /></label>
                <label className="text-xs font-semibold text-ink">Email<input type="email" className={`${input} mt-1`} value={nominee.email || ''} onChange={(e) => setNominee({ ...nominee, email: e.target.value })} /></label>
                <label className="text-xs font-semibold text-ink">Phone<input className={`${input} mt-1`} value={nominee.phone || ''} onChange={(e) => setNominee({ ...nominee, phone: e.target.value })} /></label>
                <div className="sm:col-span-2"><button type="submit" className={secondary} disabled={saveNominee.isPending}>Save nominee</button></div>
              </form>
            </Card>

            <Card icon={<ShieldCheck size={18} />} title="What you agreed to">
              {consents.data?.length ? (
                <ul className="divide-y divide-ink/5">
                  {consents.data.map((c) => (
                    <li key={c.id} className="flex flex-wrap justify-between gap-2 py-2">
                      <span className="text-ink">
                        {PURPOSE_LABEL[c.purpose] || c.purpose}
                        {c.purpose !== 'age_18_plus' && c.terms_version ? ` (version ${c.purpose === 'terms' ? c.terms_version : c.notice_version})` : ''}
                        {c.action === 'withdrawn' ? ' · withdrawn' : ''}
                      </span>
                      <span className="text-xs">{fmt(c.created_at)}</span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p>No records yet. Accounts created before 10 November 2026 are asked to accept the current Privacy Notice and Terms the next time they use the site.</p>
              )}
              <div className="mt-5 rounded-xl bg-mist p-4">
                <p className="font-semibold text-ink">Withdraw consent</p>
                <p className="mt-1">This closes your account and erases your personal data, except payment records the law makes us keep. It cannot be undone.</p>
                <label className="mt-3 flex items-center gap-2 text-ink">
                  <input type="checkbox" checked={confirmWithdraw} onChange={(e) => setConfirmWithdraw(e.target.checked)} className="h-4 w-4 accent-clay" />
                  I understand my account will be closed.
                </label>
                <button
                  type="button"
                  className={`${danger} mt-3`}
                  disabled={!confirmWithdraw}
                  onClick={run(() => finish('/api/v1/me/consents/withdraw', { confirm: true }), 'Consent withdrawn.')}
                >
                  <XCircle size={16} /> Withdraw consent
                </button>
              </div>
            </Card>

            <Card icon={<Trash2 size={18} />} title="Delete my data">
              <p>Erases your account, contact details, booking notes, tickets, review names, notifications and uploaded documents. Booking dates and amounts stay, without your name, for tax and accounting law. You get a reference number.</p>
              <label htmlFor="confirm-delete" className="mt-3 block text-xs font-semibold text-ink">Type DELETE to confirm</label>
              <div className="mt-1 flex flex-wrap gap-2">
                <input id="confirm-delete" className={`${input} max-w-[12rem]`} value={confirmDelete} onChange={(e) => setConfirmDelete(e.target.value)} autoComplete="off" />
                <button
                  type="button"
                  className={danger}
                  disabled={confirmDelete.trim().toUpperCase() !== 'DELETE'}
                  onClick={run(() => finish('/api/v1/me/erase', { confirm: 'DELETE' }), 'Your data has been erased.')}
                >
                  <Trash2 size={16} /> Delete my data
                </button>
              </div>
            </Card>

            <Card icon={<FileText size={18} />} title="My requests">
              {requests.isLoading ? (
                <Loader2 className="animate-spin" size={18} />
              ) : requests.data?.length ? (
                <ul className="divide-y divide-ink/5">
                  {requests.data.map((r) => (
                    <li key={r.request_number} className="flex flex-wrap justify-between gap-2 py-2">
                      <span className="font-mono text-xs text-ink">{r.request_number}</span>
                      <span className="capitalize text-ink">{r.type.replace(/_/g, ' ')} · {r.status}</span>
                      <span className="text-xs">{r.status === 'open' ? `Due ${fmt(r.due_at)}` : `Done ${fmt(r.completed_at)}`}</span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p>No requests yet.</p>
              )}
            </Card>
          </div>
        )}
      </div>
    </div>
  );
}
