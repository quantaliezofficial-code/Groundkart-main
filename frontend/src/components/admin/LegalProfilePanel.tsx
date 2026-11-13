import React, { useEffect, useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { complianceApi } from '../../lib/api/compliance';
import { LEGAL_PROFILE_FIELDS, useLegalProfile, type LegalProfile } from '../../lib/legal';
import { useAuth } from '../../lib/auth';
import { errorText } from '../../lib/format';
import { Button, Field, Notice, Panel, inputClass } from '../dashboard/kit';

/**
 * The business facts the legal pages, footer and checkout need (company
 * name, CIN, registered office, Grievance Officer, jurisdiction...). Until
 * a field is filled, the site shows a visible "[[OWNER TO FILL: ...]]"
 * placeholder rather than an invented value. Only the super admin edits.
 */

type FieldKey = (typeof LEGAL_PROFILE_FIELDS)[number]['key'];

export default function LegalProfilePanel() {
  const { user } = useAuth();
  const isSuper = Boolean(user?.is_super_admin);
  const qc = useQueryClient();
  const profile = useLegalProfile();
  const [form, setForm] = useState<Record<FieldKey, string> | null>(null);

  useEffect(() => {
    if (!profile.data) return;
    const f = {} as Record<FieldKey, string>;
    for (const { key } of LEGAL_PROFILE_FIELDS) {
      const v = profile.data[key];
      f[key] = typeof v === 'string' ? v : '';
    }
    setForm(f);
  }, [profile.data]);

  const save = useMutation({
    mutationFn: () => {
      const body: Partial<Record<keyof LegalProfile, string | null>> = {};
      for (const { key } of LEGAL_PROFILE_FIELDS) {
        const before = (profile.data?.[key] as string | null) ?? '';
        const now = form?.[key]?.trim() ?? '';
        if (now !== before) body[key] = now || null;
      }
      return complianceApi.updateLegalProfile(body);
    },
    onSuccess: (data) => qc.setQueryData(['legal-profile'], data),
  });

  if (profile.isError) return <Notice tone="error">{errorText(profile.error)}</Notice>;
  if (!form) return <div className="h-48 rounded-2xl shimmer" />;
  const missing = profile.data?.missing.length ?? 0;

  return (
    <Panel
      title="Legal and business details"
      description={
        missing
          ? `${missing} detail${missing === 1 ? '' : 's'} still show as placeholders on the legal pages and footer.`
          : 'All details are filled in. They appear on the legal pages, the footer and at checkout.'
      }
    >
      <form
        data-testid="legal-profile-form"
        onSubmit={(e) => {
          e.preventDefault();
          save.mutate();
        }}
        className="space-y-5"
      >
        {!isSuper ? <Notice>Only the super admin can change these.</Notice> : null}
        <div className="grid grid-cols-1 gap-5 md:grid-cols-2">
          {LEGAL_PROFILE_FIELDS.map((f) => (
            <Field key={f.key} label={f.label} hint={f.hint} className={f.multiline ? 'md:col-span-2' : ''}>
              {f.multiline ? (
                <textarea
                  className={`${inputClass} min-h-[72px]`}
                  value={form[f.key]}
                  disabled={!isSuper}
                  onChange={(e) => setForm({ ...form, [f.key]: e.target.value })}
                />
              ) : (
                <input
                  className={inputClass}
                  value={form[f.key]}
                  disabled={!isSuper}
                  onChange={(e) => setForm({ ...form, [f.key]: e.target.value })}
                />
              )}
            </Field>
          ))}
        </div>
        <Notice>
          These are statements your business makes to customers and regulators. Have your lawyer confirm them before going
          live; the policy texts themselves are drafts for lawyer review.
        </Notice>
        {save.isError ? <Notice tone="error">{errorText(save.error)}</Notice> : null}
        {save.isSuccess ? <Notice tone="success">Saved. The legal pages and footer now show these details.</Notice> : null}
        {isSuper ? (
          <Button type="submit" variant="primary" loading={save.isPending}>
            Save details
          </Button>
        ) : null}
      </form>
    </Panel>
  );
}
