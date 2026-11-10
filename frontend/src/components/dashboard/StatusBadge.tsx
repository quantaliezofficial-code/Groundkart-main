import React from 'react';

export type StatusType = 
  | 'active' 
  | 'approved' 
  | 'pending_review' 
  | 'pending' 
  | 'suspended' 
  | 'rejected' 
  | 'draft'
  | 'confirmed'
  | 'pending_payment'
  | 'cancelled'
  | 'completed';

export interface StatusBadgeProps {
  status: string;
  className?: string;
}

const STATUS_BADGE_STYLE: Record<string, string> = {
  active: 'bg-primary-container/10 text-primary-container border-primary-container/20',
  approved: 'bg-primary-container/10 text-primary-container border-primary-container/20',
  confirmed: 'bg-primary-container/10 text-primary-container border-primary-container/20',
  completed: 'bg-primary-container/10 text-primary-container border-primary-container/20',
  
  pending_review: 'bg-marigold/10 text-pitch border-marigold/30',
  pending: 'bg-marigold/10 text-pitch border-marigold/30',
  pending_payment: 'bg-marigold/10 text-pitch border-marigold/30',
  
  suspended: 'bg-clay/10 text-clay border-clay/20',
  rejected: 'bg-clay/10 text-clay border-clay/20',
  cancelled: 'bg-clay/10 text-clay border-clay/20',
  
  draft: 'bg-surface-container-high text-on-surface-variant border-surface-container-highest',
  archived: 'bg-surface-container-high text-on-surface-variant border-surface-container-highest',

  // Money states (commissions, payouts, payments)
  paid: 'bg-primary-container/10 text-primary-container border-primary-container/20',
  received: 'bg-primary-container/10 text-primary-container border-primary-container/20',
  payable: 'bg-info/10 text-info border-info/25',
  awaiting: 'bg-marigold/10 text-pitch border-marigold/30',
  refunded: 'bg-clay/10 text-clay border-clay/20',
  partly_refunded: 'bg-clay/10 text-clay border-clay/20',
  reversed: 'bg-clay/10 text-clay border-clay/20',
  adjustment: 'bg-clay/10 text-clay border-clay/20',
  paused: 'bg-surface-container-high text-on-surface-variant border-surface-container-highest',
  expired: 'bg-surface-container-high text-on-surface-variant border-surface-container-highest',
};

const STATUS_LABEL: Record<string, string> = {
  pending_review: 'In review',
  pending_payment: 'Awaiting payment',
  awaiting: 'Awaiting payment',
  received_not_eligible: 'Paid before referral',
  not_received: 'Not paid',
  partly_refunded: 'Partly refunded',
  under_admin_review: 'Under review',
};

export function StatusBadge({ status, className = '' }: StatusBadgeProps) {
  const normalizedStatus = status.toLowerCase();
  const style = STATUS_BADGE_STYLE[normalizedStatus] ?? 'bg-surface-container-high text-on-surface-variant border-surface-container-highest';
  
  return (
    <span className={`inline-flex items-center whitespace-nowrap rounded-full border px-2 py-0.5 font-sans text-xs font-medium ${style} ${className}`}>
      {STATUS_LABEL[normalizedStatus] ?? (normalizedStatus.charAt(0).toUpperCase() + normalizedStatus.slice(1)).replace(/_/g, ' ')}
    </span>
  );
}
