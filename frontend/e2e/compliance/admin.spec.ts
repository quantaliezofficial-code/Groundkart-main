import { test, expect } from '@playwright/test';

const API = process.env.E2E_API_URL || 'http://localhost:8000';

test.describe('@compliance admin console', () => {
  // A fresh sign-in per test: refresh tokens rotate, so a shared saved
  // session is spent by the first test that uses it.
  test.beforeEach(async ({ page }) => {
    const res = await page.request.post(`${API}/api/v1/auth/login`, {
      data: { login_id: 'admin@groundkart.demo', password: process.env.ADMIN_PASSWORD || 'Admin@2026!' },
    });
    expect(res.ok()).toBeTruthy();
  });

  test('[3.3] [8.5] incidents can be recorded with their reporting deadlines', async ({ page }) => {
    await page.goto('/admin?tab=Compliance');
    await expect(page.getByTestId('compliance-tab')).toBeVisible();
    await page.getByRole('tab', { name: 'Incidents' }).click();
    await page.getByRole('button', { name: /record an incident/i }).click();
    const dialog = page.getByRole('dialog', { name: /record an incident/i });
    await expect(dialog).toContainText(/6 hours/);
    await expect(dialog).toContainText(/72/);
    await dialog.getByLabel('Short title').fill('E2E drill: test incident');
    await dialog.getByLabel('What happened').fill('Recorded by the compliance end-to-end test.');
    await dialog.getByRole('button', { name: 'Record incident' }).click();
    await expect(page.getByText('E2E drill: test incident').first()).toBeVisible();
    await expect(page.getByText(/GK-INC-/).first()).toBeVisible();
  });

  test('[3.2] data requests and complaint clocks are visible to the Grievance Officer', async ({ page }) => {
    await page.goto('/admin?tab=Compliance');
    await expect(page.getByText('Not acknowledged in time')).toBeVisible();
    await page.getByRole('tab', { name: 'Data requests' }).click();
    await expect(page.getByRole('heading', { name: 'Data requests' })).toBeVisible();
  });

  test('[6.2] legal and business details are edited in one place', async ({ page }) => {
    await page.goto('/admin?tab=Settings');
    const form = page.getByTestId('legal-profile-form');
    await expect(form).toBeVisible();
    for (const label of ['Legal company name', 'Registered office address', 'Grievance Officer name', 'Jurisdiction city (courts)']) {
      await expect(form.getByText(label, { exact: true })).toBeVisible();
    }
  });

  test('[8.2] admins can enrol an authenticator app', async ({ page }) => {
    await page.goto('/admin?tab=Compliance');
    await page.getByRole('tab', { name: 'Sign-in security' }).click();
    await expect(page.getByRole('heading', { name: /two-step sign-in/i })).toBeVisible();
  });
});
