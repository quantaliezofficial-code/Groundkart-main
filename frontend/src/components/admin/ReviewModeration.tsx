import React, { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { BadgeCheck, Eye, EyeOff, Star } from 'lucide-react';
import { siteApi } from '../../lib/api/site';
import { useAuth } from '../../lib/auth';
import { errorText } from '../../lib/format';
import { Button, Field, Modal, Notice, inputClass } from '../dashboard/kit';

export interface ModeratedReview {
  id: string;
  verified_booking?: boolean;
  hidden_at?: string | null;
  hidden_reason?: string | null;
  featured?: boolean;
}

/** Status chips for any admin; hide / show / feature buttons for the super
 * admin. The customer's text and rating are never editable. */
export default function ReviewModeration({ review }: { review: ModeratedReview }) {
  const { user } = useAuth();
  const isSuper = Boolean(user?.is_super_admin);
  const qc = useQueryClient();
  const [hiding, setHiding] = useState(false);
  const [reason, setReason] = useState('');
  const mutate = useMutation({
    mutationFn: (body: { hidden?: boolean; reason?: string; featured?: boolean }) => siteApi.moderateReview(review.id, body),
    onSuccess: () => {
      setHiding(false);
      setReason('');
      qc.invalidateQueries({ queryKey: ['admin-reviews'] });
    },
  });
  const hidden = Boolean(review.hidden_at);

  return (
    <div className="flex flex-col items-end gap-1.5">
      <div className="flex flex-wrap justify-end gap-1">
        {review.verified_booking ? (
          <span className="inline-flex items-center gap-1 whitespace-nowrap rounded-full bg-pitch/[0.06] px-2 py-0.5 text-[11px] font-semibold text-pitch">
            <BadgeCheck size={12} aria-hidden="true" /> Completed booking
          </span>
        ) : (
          <span className="rounded-full bg-surface-container px-2 py-0.5 text-[11px] font-semibold text-on-surface-variant">Not public: no completed booking</span>
        )}
        {hidden ? (
          <span className="rounded-full bg-clay/10 px-2 py-0.5 text-[11px] font-semibold text-clay" title={review.hidden_reason ?? ''}>
            Hidden
          </span>
        ) : null}
        {review.featured ? (
          <span className="inline-flex items-center gap-1 rounded-full bg-marigold/20 px-2 py-0.5 text-[11px] font-semibold text-pitch">
            <Star size={11} aria-hidden="true" /> Featured
          </span>
        ) : null}
      </div>
      {hidden && review.hidden_reason ? <p className="max-w-[220px] text-right text-[11px] text-on-surface-variant">Reason: {review.hidden_reason}</p> : null}
      {isSuper ? (
        <div className="flex flex-nowrap justify-end gap-1 [&>button]:px-2.5 [&>button]:py-1.5 [&>button]:text-xs">
          {hidden ? (
            <Button loading={mutate.isPending} onClick={() => mutate.mutate({ hidden: false })}>
              <Eye size={13} aria-hidden="true" /> Show again
            </Button>
          ) : (
            <Button onClick={() => setHiding(true)}>
              <EyeOff size={13} aria-hidden="true" /> Hide
            </Button>
          )}
          {review.verified_booking && !hidden ? (
            <Button loading={mutate.isPending} onClick={() => mutate.mutate({ featured: !review.featured })}>
              <Star size={13} aria-hidden="true" /> {review.featured ? 'Unfeature' : 'Feature'}
            </Button>
          ) : null}
        </div>
      ) : null}
      {mutate.isError && !hiding ? <p className="text-[11px] text-clay">{errorText(mutate.error)}</p> : null}
      {hiding ? (
        <Modal
          title="Hide this review"
          onClose={() => setHiding(false)}
          footer={
            <>
              <Button onClick={() => setHiding(false)}>Cancel</Button>
              <Button variant="danger" loading={mutate.isPending} disabled={reason.trim().length < 3} onClick={() => mutate.mutate({ hidden: true, reason: reason.trim() })}>
                Hide review
              </Button>
            </>
          }
        >
          <div className="space-y-3 text-left">
            <p className="text-sm text-ink">
              Hidden reviews leave the venue page, the homepage and the rating. Hide only for a real reason: abuse, someone's
              personal details, spam or a review about a different venue. Never hide a review just because it is negative.
            </p>
            <Field label="Reason (kept in the audit log)">
              <textarea className={`${inputClass} min-h-[80px]`} value={reason} maxLength={500} onChange={(e) => setReason(e.target.value)} />
            </Field>
            {mutate.isError ? <Notice tone="error">{errorText(mutate.error)}</Notice> : null}
          </div>
        </Modal>
      ) : null}
    </div>
  );
}
