import { test, expect } from '@playwright/test';

test.describe('@compliance check 3: grievance', () => {
  test('[3.1] footer and grievance page show the Grievance Officer block', async ({ page }) => {
    await page.goto('/grievance');
    const block = page.getByTestId('footer-legal');
    await expect(block).toContainText(/grievance officer/i);
    await expect(page.getByRole('heading', { name: /how long we take/i })).toBeVisible();
  });

  test('[3.1] @owner-facts Grievance Officer name, designation, email and phone are filled in', async ({ page }) => {
    await page.goto('/grievance');
    await expect(page.getByTestId('footer-legal')).not.toContainText('OWNER TO FILL');
  });

  test('[3.2] contact form returns a ticket number', async ({ page }) => {
    await page.goto('/contact');
    const form = page.getByTestId('contact-form');
    await form.getByLabel(/name/i).first().fill('Compliance Test');
    await form.getByLabel(/email/i).fill(`ct-${Date.now()}@example.com`);
    await form.getByLabel(/subject/i).fill('Refund question');
    await form.getByLabel(/message/i).fill('Checking that complaints get a ticket number.');
    await form.getByRole('button', { name: /send/i }).click();
    await expect(page.getByTestId('ticket-number')).toHaveText(/GK-T-\d{4}-\d{4,}/);
  });

  test('[3.3] grievance page publishes the response times', async ({ page }) => {
    await page.goto('/grievance');
    const table = page.getByRole('table');
    await expect(table).toContainText('24 hours');
    await expect(table).toContainText('48 hours');
    await expect(table).toContainText('1 month');
    await expect(table).toContainText('90 days');
  });
});
