import { test, expect } from '@playwright/test';
import path from 'path';
import { fileURLToPath } from 'url';

const HERE = path.dirname(fileURLToPath(import.meta.url));

test.describe('@compliance check 8: security in the browser', () => {
  test.use({ storageState: path.resolve(HERE, '../../.auth/customer.json') });

  test('[8.2] [8.3] no access or refresh token is kept in browser storage', async ({ page }) => {
    await page.goto('/my-bookings');
    await page.waitForLoadState('networkidle');
    const dump = await page.evaluate(() => JSON.stringify({ ...localStorage }) + JSON.stringify({ ...sessionStorage }));
    expect(dump).not.toMatch(/eyJ[A-Za-z0-9_-]{10,}\./); // JWT shape
    expect(dump.toLowerCase()).not.toContain('refresh_token');
  });

  test('[8.1] API responses carry HSTS and frame protection', async ({ page }) => {
    const res = await page.request.get(`${process.env.E2E_API_URL || 'http://localhost:8000'}/api/v1/health`);
    expect(res.headers()['strict-transport-security']).toContain('max-age=');
    expect(res.headers()['x-frame-options']).toBe('DENY');
  });
});
