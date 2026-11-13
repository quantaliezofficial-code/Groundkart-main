import { test, expect } from '@playwright/test';
import { openSignup } from './helpers';

test.describe('@compliance check 5: terms', () => {
  test('[5.1] terms show the live cancellation tiers', async ({ page }) => {
    await page.goto('/terms');
    const legal = await (await page.request.get(`${process.env.E2E_API_URL || 'http://localhost:8000'}/api/v1/legal/profile`)).json();
    const bt = legal.booking_terms;
    await expect(page.getByText(`${bt.full_refund_hours} hours or more before the start time`).first()).toBeVisible();
    await expect(page.getByText(`${bt.partial_refund_percent}% refund`).first()).toBeVisible();
    await expect(page.getByText('{{')).toHaveCount(0);
  });

  test('[5.2] [5.3] terms include governing law, disputes and content rules', async ({ page }) => {
    await page.goto('/terms');
    for (const h of [/governing law and jurisdiction/i, /complaints and disputes/i, /reviews and other content/i, /our responsibility/i]) {
      await expect(page.getByRole('heading', { name: h })).toBeVisible();
    }
  });

  test('[5.2] @owner-facts jurisdiction city is filled in', async ({ page }) => {
    await page.goto('/terms');
    const section = page.locator('section', { has: page.getByRole('heading', { name: /governing law/i }) });
    await expect(section).not.toContainText('OWNER TO FILL');
  });

  test('[5.4] sign-up shows the agreement line linking terms and notice', async ({ page }) => {
    await page.goto('/');
    await openSignup(page);
    const form = page.getByTestId('signup-form');
    await expect(form.getByRole('link', { name: /terms/i }).first()).toHaveAttribute('href', '/terms');
    await expect(form.getByRole('link', { name: /privacy notice/i }).first()).toHaveAttribute('href', '/privacy');
  });
});
