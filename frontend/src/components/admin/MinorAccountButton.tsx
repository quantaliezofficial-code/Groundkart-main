import React, { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../../lib/api/client';
import { errorText } from '../../lib/format';
import { Button, Field, Modal, Notice, inputClass } from '../dashboard/kit';

/** Adults-only rule (D-12): close an account found to belong to someone
 * under 18 and erase its personal data, keeping only records the law
 * requires. Calls POST /api/v1/admin/users/{id}/minor-account. */
export default function MinorAccountButton({ userId, name }: { userId: string; name: string }) {
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [note, setNote] = useState('');
  const [typed, setTyped] = useState('');
  const run = useMutation({
    mutationFn: () => api.post(`/api/v1/admin/users/${userId}/minor-account`, { note: note.trim() || undefined }),
    onSuccess: () => {
      setOpen(false);
      qc.invalidateQueries({ queryKey: ['admin-users'] });
    },
  });
  return (
    <>
      <button type="button" onClick={() => setOpen(true)} className="ml-1 text-xs px-2 py-1 border border-ink/20 rounded-lg text-on-surface-variant hover:bg-mist cursor-pointer">
        Under 18
      </button>
      {open ? (
        <Modal
          title="Close an account that belongs to a minor"
          onClose={() => setOpen(false)}
          footer={
            <>
              <Button onClick={() => setOpen(false)}>Cancel</Button>
              <Button variant="danger" loading={run.isPending} disabled={typed.trim() !== 'ERASE'} onClick={() => run.mutate()}>
                Close and erase
              </Button>
            </>
          }
        >
          <div className="space-y-3 text-sm text-ink">
            <p>
              GroundKart is for people aged 18 and over. This suspends <strong>{name}</strong>, erases their personal data and keeps
              only records the law requires (for example payment entries). It cannot be undone.
            </p>
            <Field label="Note (how you found out; kept in the audit log)">
              <textarea className={`${inputClass} min-h-[70px]`} maxLength={1000} value={note} onChange={(e) => setNote(e.target.value)} />
            </Field>
            <Field label='Type ERASE to confirm'>
              <input className={inputClass} value={typed} onChange={(e) => setTyped(e.target.value)} />
            </Field>
            {run.isError ? <Notice tone="error">{errorText(run.error)}</Notice> : null}
          </div>
        </Modal>
      ) : null}
    </>
  );
}
