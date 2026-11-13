import { expect, Page } from '@playwright/test';

export const API = process.env.E2E_API_URL || 'http://localhost:8000';
export const PUBLIC_ROUTES = ['/', '/search', '/about', '/contact', '/support', '/privacy', '/terms', '/refunds', '/cookies', '/grievance', '/your-data'];
export const FIRST_PARTY = new Set(['localhost', '127.0.0.1']);

/** Records every request host the page makes. */
export function trackHosts(page: Page): Set<string> {
  const hosts = new Set<string>();
  page.on('request', (req) => {
    try {
      const u = new URL(req.url());
      if (u.protocol.startsWith('http')) hosts.add(u.hostname);
    } catch {
      /* data: and blob: URLs */
    }
  });
  return hosts;
}

export async function firstVenueSlug(page: Page): Promise<string> {
  const res = await page.request.get(`${API}/api/v1/venues?limit=1`);
  const body = await res.json();
  return body.data[0].slug;
}

export async function venueWithVideo(page: Page): Promise<string | null> {
  const res = await page.request.get(`${API}/api/v1/venues?limit=50`);
  const body = await res.json();
  for (const v of body.data) {
    const media = [...(v.images || []), ...(v.media || [])];
    if (media.some((m: any) => /youtu|vimeo/.test(m.url || ''))) return v.slug;
  }
  return null;
}

export async function expectNoCheckedBoxes(page: Page) {
  const checked = await page.locator('input[type=checkbox]:checked:not([data-setting])').count();
  expect(checked, 'a checkbox is ticked by default').toBe(0);
}

export async function openSignup(page: Page) {
  await page.goto('/');
  await page.getByRole('button', { name: /^log in$/i }).first().click();
  await page.getByRole('button', { name: /create one free|create an account|sign up/i }).first().click();
  await expect(page.getByTestId('signup-form')).toBeVisible();
}
