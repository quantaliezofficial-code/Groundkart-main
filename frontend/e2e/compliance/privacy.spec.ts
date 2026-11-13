import { test, expect } from '@playwright/test';
import { PUBLIC_ROUTES, openSignup } from './helpers';

test.describe('@compliance check 1: privacy notice', () => {
  for (const route of PUBLIC_ROUTES) {
    test(`[1.1] footer on ${route} links the privacy notice`, async ({ page }) => {
      await page.goto(route);
      const footer = page.getByTestId('site-footer');
      await expect(footer.getByRole('link', { name: /privacy notice/i })).toHaveAttribute('href', '/privacy');
    });
  }

  test('[1.1] privacy note sits next to the sign-up, contact, ticket and checkout forms', async ({ page }) => {
    await page.goto('/contact');
    await expect(page.getByTestId('contact-form').getByTestId('privacy-note').getByRole('link', { name: /privacy notice/i })).toBeVisible();
    await page.goto('/');
    await openSignup(page);
    await expect(page.getByTestId('signup-form').getByTestId('privacy-note')).toBeVisible();
  });

  test('[1.2] [1.3] [1.4] [1.5] [1.6] notice renders every required section', async ({ page }) => {
    await page.goto('/privacy');
    for (const h of [/data we collect/i, /how we use your data/i, /who we share it with/i, /how long we keep it/i, /your rights/i, /how we protect your data/i, /grievance officer/i]) {
      await expect(page.getByRole('heading', { name: h })).toBeVisible();
    }
    await expect(page.getByText(/Data Protection Board of India/).first()).toBeVisible();
    await expect(page.getByText(/Last updated \d+ \w+ 20\d\d/)).toBeVisible();
    await expect(page.getByRole('table').first()).toBeVisible();
    await expect(page.getByTestId('draft-banner')).toBeVisible();
  });

  test('[1.1] language switch shows the Hindi notice', async ({ page }) => {
    await page.goto('/privacy');
    await page.getByTestId('lang-hi').click();
    await expect(page.getByRole('heading', { level: 1 })).toContainText('गोपनीयता सूचना');
    await expect(page).toHaveURL(/lang=hi/);
  });
});
