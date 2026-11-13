import { test, expect } from '@playwright/test';
import { firstVenueSlug } from './helpers';
import { DetailViewPO } from '../page-objects/DetailView';

async function openCheckout(page) {
  const slug = await firstVenueSlug(page);
  await page.goto(`/venues/${slug}`);
  const detail = new DetailViewPO(page);
  await detail.selectFirstAvailableSlot();
  await detail.clickBookNow();
  await expect(page.getByTestId('price-breakup')).toBeVisible();
}

test.describe('@compliance check 6: selling online', () => {
  test('[6.1] refund and cancellation policy page covers every case', async ({ page }) => {
    await page.goto('/refunds');
    await expect(page.getByRole('heading', { name: /refund and cancellation policy/i })).toBeVisible();
    await expect(page.getByText(/no shipping or delivery/i)).toBeVisible();
    await expect(page.getByRole('table')).toContainText('100%');
  });

  test('[6.2] footer shows legal name, address, customer care and grievance details', async ({ page }) => {
    await page.goto('/');
    const block = page.getByTestId('footer-legal');
    for (const t of [/registered office/i, /customer care/i, /grievance officer/i]) await expect(block).toContainText(t);
  });

  test('[6.2] @owner-facts legal name and registered address are filled in', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByTestId('footer-legal')).not.toContainText('OWNER TO FILL');
  });

  test('[6.2] [6.4] venue page shows the seller and the service details', async ({ page }) => {
    const slug = await firstVenueSlug(page);
    await page.goto(`/venues/${slug}`);
    await expect(page.getByTestId('seller-info')).toContainText(/listed by/i);
    await expect(page.getByTestId('venue-address')).toBeVisible();
  });

  test('[6.3] checkout shows the price break-up, payment modes and refund policy before submitting', async ({ page }) => {
    await openCheckout(page);
    const breakup = page.getByTestId('price-breakup');
    for (const t of [/venue charge/i, /platform fee/i, /taxes/i, /total/i]) await expect(breakup).toContainText(t);
    await expect(page.getByTestId('payment-modes')).toBeVisible();
    await expect(page.getByRole('link', { name: /refund and cancellation policy/i })).toHaveAttribute('href', '/refunds');
  });

  test('[6.5] reviews shown publicly carry the verified-booking label', async ({ page }) => {
    const slug = await firstVenueSlug(page);
    await page.goto(`/venues/${slug}`);
    const reviews = page.getByTestId('review-item');
    const n = await reviews.count();
    for (let i = 0; i < n; i++) await expect(reviews.nth(i)).toContainText(/verified booking/i);
  });

  test('[6.5] homepage shows only verified-booking reviews and the booking protections', async ({ page }) => {
    await page.goto('/');
    const protections = page.getByTestId('booking-protections');
    await expect(protections).toContainText(/held/i);
    await expect(protections).toContainText(/100%/);
    const reviews = page.getByTestId('verified-reviews');
    if (await reviews.count()) {
      const cards = reviews.getByRole('listitem');
      const n = await cards.count();
      for (let i = 0; i < n; i++) await expect(cards.nth(i)).toContainText('Verified booking');
    }
  });

  test('[6.5] demo data is visibly flagged', async ({ page }) => {
    const demo = await (await page.request.get(`${process.env.E2E_API_URL || 'http://localhost:8000'}/api/v1/meta/demo`)).json();
    await page.goto('/');
    if (demo.demo_data_present) await expect(page.getByTestId('demo-banner')).toContainText('DEMO DATA');
    else await expect(page.getByTestId('demo-banner')).toHaveCount(0);
  });
});
