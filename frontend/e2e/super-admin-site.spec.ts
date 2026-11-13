import { test, expect } from '@playwright/test';

const API = process.env.E2E_API_URL || 'http://localhost:8000';

test.describe('Super admin website control @regression', () => {
  test.beforeEach(async ({ page }) => {
    const res = await page.request.post(`${API}/api/v1/auth/login`, {
      data: { login_id: 'admin@groundkart.demo', password: process.env.ADMIN_PASSWORD || 'Admin@2026!' },
    });
    expect(res.ok()).toBeTruthy();
  });

  // Signed-in admins land on the console, so the public page is checked as a visitor.
  async function visitorHome(browser) {
    const ctx = await browser.newContext();
    const visitor = await ctx.newPage();
    await visitor.goto('/');
    await visitor.waitForLoadState('networkidle');
    return { visitor, close: () => ctx.close() };
  }

  test('editing the homepage headline publishes it, and History can restore the previous version', async ({ page, browser }) => {
    const headline = `Grounds for every plan ${Date.now() % 100000}`;
    await page.goto('/admin?tab=Website');
    const editor = page.getByTestId('homepage-editor');
    await expect(editor).toBeVisible();
    const field = editor.getByLabel(/^Headline(?!,)/);
    const original = await field.inputValue();
    await field.fill(headline);
    await editor.getByPlaceholder('Note for this version (optional)').fill('e2e headline test');
    await editor.getByRole('button', { name: 'Publish' }).click();
    await expect(editor.getByText(/Published\. Visitors see it/)).toBeVisible();

    let v = await visitorHome(browser);
    await expect(v.visitor.getByRole('heading', { level: 1 })).toContainText(headline);
    await v.close();

    // Put the previous text back through History (restore = new version).
    await page.goto('/admin?tab=Website');
    await page.getByRole('tab', { name: 'History' }).click();
    const restore = page.getByRole('button', { name: 'Restore' }).first();
    await restore.click();
    await expect(page.getByText('live').first()).toBeVisible();
    v = await visitorHome(browser);
    await expect(v.visitor.getByRole('heading', { level: 1 })).toContainText(original);
    await v.close();
  });

  test('turning a section off hides it from the homepage', async ({ page, browser }) => {
    await page.goto('/admin?tab=Website');
    const editor = page.getByTestId('homepage-editor');
    await editor.getByLabel('Founder and team').uncheck();
    await editor.getByRole('button', { name: 'Publish' }).click();
    await expect(editor.getByText(/Published\. Visitors see it/)).toBeVisible();
    const v = await visitorHome(browser);
    await expect(v.visitor.getByTestId('founder-story')).toHaveCount(0);
    await v.close();

    await page.goto('/admin?tab=Website');
    await page.getByTestId('homepage-editor').getByLabel('Founder and team').check();
    await page.getByTestId('homepage-editor').getByRole('button', { name: 'Publish' }).click();
    await expect(page.getByTestId('homepage-editor').getByText(/Published\. Visitors see it/)).toBeVisible();
  });

  test('the asset library and review moderation are available to the super admin', async ({ page }) => {
    await page.goto('/admin?tab=Website');
    await page.getByRole('tab', { name: 'Images' }).click();
    await expect(page.getByTestId('asset-library')).toContainText('Upload an image');
    await page.goto('/admin?tab=Reviews');
    await expect(page.getByRole('button', { name: /^Hide$/ }).first()).toBeVisible();
  });
});
