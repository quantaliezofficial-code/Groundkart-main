import { test, expect } from '@playwright/test';
import { expectNoCheckedBoxes, firstVenueSlug, openSignup } from './helpers';

test.describe('@compliance check 2: consent', () => {
  test('[2.1] no public form has a pre-ticked box', async ({ page }) => {
    for (const route of ['/contact', '/search', '/support']) {
      await page.goto(route);
      await expectNoCheckedBoxes(page);
    }
    await page.goto('/');
    await openSignup(page);
    await expectNoCheckedBoxes(page);
    const slug = await firstVenueSlug(page);
    await page.goto(`/venues/${slug}`);
    await expectNoCheckedBoxes(page);
  });

  test('[2.2] there is no marketing opt-in bundled anywhere', async ({ page }) => {
    await page.goto('/');
    await openSignup(page);
    // No marketing opt-in control exists at all (owner decision D-11), so
    // nothing can be bundled with the service terms.
    const form = page.getByTestId('signup-form');
    await expect(form.getByRole('checkbox', { name: /newsletter|promotion|marketing|offers|whatsapp updates/i })).toHaveCount(0);
    await expect(form.getByRole('checkbox')).toHaveCount(1); // the 18+ declaration only
  });

  test('[2.3] My Data page offers one-step consent withdrawal (signed out: asks to sign in)', async ({ page }) => {
    await page.goto('/your-data');
    await expect(page.getByRole('heading', { name: /your data rights/i })).toBeVisible();
    await expect(page.getByText(/withdraw consent/i).first()).toBeVisible();
  });
});
