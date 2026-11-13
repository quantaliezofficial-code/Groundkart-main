import { test, expect } from '@playwright/test';
import { FIRST_PARTY, PUBLIC_ROUTES, firstVenueSlug, trackHosts, venueWithVideo } from './helpers';

test.describe('@compliance check 4: cookies and third parties', () => {
  test('[4.1] [4.2] first load of public pages contacts no third-party host', async ({ page }) => {
    const hosts = trackHosts(page);
    const slug = await firstVenueSlug(page);
    for (const route of [...PUBLIC_ROUTES, `/venues/${slug}`]) {
      await page.goto(route, { waitUntil: 'networkidle' });
    }
    const third = [...hosts].filter((h) => !FIRST_PARTY.has(h));
    expect(third, `third-party hosts: ${third.join(', ')}`).toEqual([]);
  });

  test('[4.1] no cookie banner is needed because no non-essential cookie is set', async ({ page, context }) => {
    await page.goto('/', { waitUntil: 'networkidle' });
    const cookies = await context.cookies();
    expect(cookies.filter((c) => c.name !== 'refresh_token')).toEqual([]);
  });

  test('[4.2] venue videos load only after the visitor presses play', async ({ page }) => {
    const slug = await venueWithVideo(page);
    test.skip(!slug, 'no seeded venue has a video');
    const hosts = trackHosts(page);
    await page.goto(`/venues/${slug}`, { waitUntil: 'networkidle' });
    expect([...hosts].some((h) => /youtube|vimeo/.test(h))).toBe(false);
    await expect(page.locator('iframe[src*="youtube"], iframe[src*="vimeo"]')).toHaveCount(0);
    await page.getByTestId('video-facade').first().click();
    await expect(page.locator('iframe[src*="youtube-nocookie"], iframe[src*="vimeo"]').first()).toBeVisible();
  });

  test('[4.3] cookie notice names the cookie, storage keys and every third-party service', async ({ page }) => {
    await page.goto('/cookies');
    for (const t of ['refresh_token', 'groundkart_favorites', 'YouTube', 'Vimeo', 'Google Maps', 'WhatsApp']) {
      await expect(page.getByText(t).first()).toBeVisible();
    }
  });

  test('[4.4] footer has a Cookie settings control that opens the choices', async ({ page }) => {
    await page.goto('/');
    await page.getByTestId('cookie-settings-link').click();
    const dialog = page.getByRole('dialog', { name: /cookie settings/i });
    await expect(dialog).toBeVisible();
    await expect(dialog.getByRole('switch')).not.toBeChecked();
  });
});
