import React, { useEffect, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { platformApi, type PlatformSettings } from '../../lib/api/platform';
import { useAuth } from '../../lib/auth';
import { dateTime, errorText } from '../../lib/format';
import { Button, Field, Notice, Panel, inputClass } from '../dashboard/kit';
import LegalProfilePanel from './LegalProfilePanel';

/**
 * The platform's business rules. Every change is audited with its before
 * and after values. The default partner rate is the super admin's to set.
 */

type Form = Record<keyof Omit<PlatformSettings, 'updated_at'>, string>;

const FIELDS: { key: keyof Form; label: string; hint: string; suffix: string; superOnly?: boolean }[] = [
  { key: 'booking_hold_duration_minutes', label: 'Hold an unpaid request for', hint: 'After this, an unpaid request is released and the slot reopens.', suffix: 'minutes' },
  { key: 'booking_grace_period_hours', label: 'Owner review window after payment', hint: 'Time an owner has to flag a problem with a confirmed booking.', suffix: 'hours' },
  { key: 'cancellation_full_refund_hours', label: 'Full refund if cancelled at least', hint: 'Before the event starts.', suffix: 'hours before' },
  { key: 'cancellation_partial_refund_hours', label: 'Partial refund if cancelled at least', hint: 'Later than this, nothing is refunded.', suffix: 'hours before' },
  { key: 'cancellation_partial_refund_percent', label: 'Partial refund amount', hint: 'Share of the amount paid that is returned.', suffix: '%' },
  { key: 'platform_commission_percent', label: 'GroundKart commission', hint: 'Kept from each confirmed payment before the owner payout.', suffix: '%' },
  { key: 'payout_holdback_days', label: 'Hold owner payouts for', hint: 'Days after the event before money becomes payable to the owner.', suffix: 'days' },
  { key: 'default_broker_commission_percent', label: 'Default partner rate', hint: 'Given to new referral partners. Existing partners keep their own rate.', suffix: '%', superOnly: true },
];

export default function SettingsTab() {
  const { user } = useAuth();
  const isSuper = Boolean(user?.is_super_admin);
  const qc = useQueryClient();
  const settings = useQuery({ queryKey: ['admin-settings'], queryFn: platformApi.getSettings });
  const [form, setForm] = useState<Form | null>(null);

  useEffect(() => {
    if (settings.data) {
      const f = {} as Form;
      for (const { key } of FIELDS) f[key] = String(settings.data[key] ?? '');
      setForm(f);
    }
  }, [settings.data]);

  const save = useMutation({
    mutationFn: () => {
      const body: Record<string, number | string> = {};
      for (const { key, superOnly } of FIELDS) {
        if (!form || (superOnly && !isSuper)) continue;
        if (String(settings.data?.[key]) === form[key]) continue;
        body[key] = key === 'default_broker_commission_percent' ? form[key] : Number(form[key]);
      }
      return platformApi.updateSettings(body);
    },
    onSuccess: (data) => qc.setQueryData(['admin-settings'], data),
  });

  if (settings.isError) return <Notice tone="error">{errorText(settings.error)}</Notice>;
  if (!form) return <div className="h-64 rounded-2xl shimmer" />;

  return (
    <div className="space-y-6">
    <Panel
      title="Booking, refund and payout rules"
      description={settings.data ? `Last changed ${dateTime(settings.data.updated_at)}. Every change is recorded in the audit log.` : undefined}
    >
      <form
        onSubmit={(e) => {
          e.preventDefault();
          save.mutate();
        }}
        className="space-y-6"
      >
        <div className="grid grid-cols-1 gap-5 md:grid-cols-2">
          {FIELDS.map((f) => (
            <Field key={f.key} label={f.label} hint={f.superOnly && !isSuper ? 'Only the super admin can change this.' : f.hint}>
              <div className="flex items-center gap-2">
                <input
                  className={`${inputClass} max-w-[140px]`}
                  inputMode="decimal"
                  value={form[f.key]}
                  disabled={f.superOnly && !isSuper}
                  onChange={(e) => setForm({ ...form, [f.key]: e.target.value })}
                />
                <span className="text-sm text-on-surface-variant">{f.suffix}</span>
              </div>
            </Field>
          ))}
        </div>
        {save.isError ? <Notice tone="error">{errorText(save.error)}</Notice> : null}
        {save.isSuccess ? <Notice tone="success">Saved. New bookings use these rules from now on.</Notice> : null}
        <Button type="submit" variant="primary" loading={save.isPending}>
          Save rules
        </Button>
      </form>
    </Panel>
    <LegalProfilePanel />
    </div>
  );
}
