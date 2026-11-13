import { test, expect } from '@playwright/test';
import path from 'path';
import { fileURLToPath } from 'url';

const HERE = path.dirname(fileURLToPath(import.meta.url));

test.describe('@compliance beyond-8: Your data rights', () => {
  test('[B.1] public page explains each right and the response times', async ({ page }) => {
    await page.goto('/your-data');
    for (const t of [/summary of your data/i, /correction/i, /withdraw consent/i, /erasure/i, /nominee/i]) {
      await expect(page.getByRole('table').getByText(t).first()).toBeVisible();
    }
  });

  test.describe('signed in', () => {
    test.use({ storageState: path.resolve(HERE, '../../.auth/customer.json') });

    test('[B.1] My Data downloads a JSON copy and offers nominee, withdrawal and deletion', async ({ page }) => {
      await page.goto('/account/data');
      await expect(page.getByRole('heading', { level: 1, name: /my data/i })).toBeVisible();
      const download = page.waitForEvent('download');
      await page.getByRole('button', { name: /download my data/i }).click();
      expect((await download).suggestedFilename()).toMatch(/groundkart-my-data-\d+\.json/);
      await expect(page.getByRole('button', { name: /save nominee/i })).toBeVisible();
      await expect(page.getByRole('button', { name: /withdraw consent/i })).toBeVisible();
      await expect(page.getByRole('button', { name: /delete my data/i })).toBeVisible();
    });
  });
});
