import { test, expect } from '@playwright/test';
import { firstVenueSlug } from './helpers';

const URGENCY = /only \d+ (left|remaining)|selling fast|hurry|\d+ (people|others) (are )?(viewing|looking)|offer ends in|last chance/i;

test.describe('@compliance check 6.5: dark-pattern scan', () => {
  test('[6.5] no fake urgency, countdowns or pre-selected extras on public pages', async ({ page }) => {
    const slug = await firstVenueSlug(page);
    for (const route of ['/', '/search', `/venues/${slug}`]) {
      await page.goto(route, { waitUntil: 'networkidle' });
      const text = await page.locator('body').innerText();
      expect(text, `urgency wording on ${route}`).not.toMatch(URGENCY);
      // Countdown widgets are allowed only when they show the real hold expiry (data-hold-expiry).
      await expect(page.locator('[data-countdown]:not([data-hold-expiry])')).toHaveCount(0);
      await expect(page.locator('input[type=checkbox]:checked:not([data-setting]), input[type=radio][data-extra]:checked')).toHaveCount(0);
    }
  });

  test('[6.5] a closed announcement stays closed on the next page and the next visit', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    const close = page.getByRole('button', { name: 'Dismiss announcement' });
    test.skip((await close.count()) === 0, 'no announcement strip is published');
    await close.click();
    await page.goto('/search');
    await page.goto('/');
    await page.reload();
    await page.waitForLoadState('networkidle');
    await expect(page.getByRole('button', { name: 'Dismiss announcement' })).toHaveCount(0);
  });

  test('[6.5] nothing opens by itself on first visit', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1500);
    await expect(page.getByRole('dialog')).toHaveCount(0);
  });
});

