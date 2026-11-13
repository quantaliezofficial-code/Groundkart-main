import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi, beforeEach } from 'vitest';
import NoticeUpdateBanner from './NoticeUpdateBanner';
import { useAuth } from '../../lib/auth';
import { api } from '../../lib/api/client';

vi.mock('../../lib/auth', () => ({ useAuth: vi.fn() }));
vi.mock('../../lib/api/client', async (orig) => {
  const mod = await orig<typeof import('../../lib/api/client')>();
  return { ...mod, api: { ...mod.api, post: vi.fn().mockResolvedValue({}) } };
});

const refreshUser = vi.fn().mockResolvedValue(null);

function asUser(user: Record<string, unknown> | null) {
  (useAuth as unknown as ReturnType<typeof vi.fn>).mockReturnValue({ user, refreshUser });
}

describe('NoticeUpdateBanner [2.4] [7.1]', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  it('stays hidden for signed-out visitors and accounts on the current version', () => {
    asUser(null);
    const { container, rerender } = render(<NoticeUpdateBanner onNavigate={() => {}} />);
    expect(container).toBeEmptyDOMElement();
    asUser({ role: 'customer', accepted_terms_version: '1.0', age_confirmed: true });
    rerender(<NoticeUpdateBanner onNavigate={() => {}} />);
    expect(container).toBeEmptyDOMElement();
  });

  it('asks a legacy account to accept, with an unticked 18+ box that gates the button', async () => {
    asUser({ role: 'customer', accepted_terms_version: null, age_confirmed: false });
    render(<NoticeUpdateBanner onNavigate={() => {}} />);
    expect(screen.getByTestId('notice-update-banner')).toBeInTheDocument();
    const box = screen.getByLabelText('I confirm I am 18 years or older.');
    expect(box).not.toBeChecked();
    const accept = screen.getByRole('button', { name: 'I accept' });
    expect(accept).toBeDisabled();

    await userEvent.click(box);
    await userEvent.click(accept);
    await waitFor(() => expect(api.post).toHaveBeenCalledWith('/api/v1/me/consents/accept', { accept: true, age_confirmed: true }));
    expect(refreshUser).toHaveBeenCalled();
  });

  it('can be closed, and stays closed on later visits for the same notice version', async () => {
    asUser({ role: 'customer', accepted_terms_version: null, age_confirmed: true });
    const { unmount } = render(<NoticeUpdateBanner onNavigate={() => {}} />);
    await userEvent.click(screen.getByRole('button', { name: 'Not now' }));
    expect(screen.queryByTestId('notice-update-banner')).not.toBeInTheDocument();
    expect(api.post).not.toHaveBeenCalled();
    unmount();
    render(<NoticeUpdateBanner onNavigate={() => {}} />);
    expect(screen.queryByTestId('notice-update-banner')).not.toBeInTheDocument();
  });

  it('is never shown to admins', () => {
    asUser({ role: 'admin', accepted_terms_version: null, age_confirmed: false });
    const { container } = render(<NoticeUpdateBanner onNavigate={() => {}} />);
    expect(container).toBeEmptyDOMElement();
  });
});
