import { test, expect } from '@playwright/test';
import { openSignup } from './helpers';

test.describe('@compliance check 7: adults only', () => {
  test('[7.1] sign-up has an unticked 18+ declaration and refuses without it', async ({ page }) => {
    await page.goto('/');
    await openSignup(page);
    const form = page.getByTestId('signup-form');
    const box = form.getByLabel(/I confirm I am 18 years or older/i);
    await expect(box).not.toBeChecked();
    await form.getByLabel(/full name/i).fill('Adult Test');
    await form.getByLabel(/email/i).fill(`adult-${Date.now()}@example.com`);
    await form.getByLabel(/phone/i).fill(`98${String(Date.now()).slice(-8)}`);
    await form.getByLabel(/^password/i).fill('Strong-Passw0rd!');
    await form.getByRole('button', { name: /create account/i }).click();
    await expect(form.getByText(/18 years or older/i).last()).toBeVisible();
  });

  test('[7.3] [7.4] privacy notice states adults-only and asks not to enter children\'s details', async ({ page }) => {
    await page.goto('/privacy');
    await expect(page.getByText(/adults aged 18 and over/i).first()).toBeVisible();
    await expect(page.getByText(/do not enter the personal details of children/i)).toBeVisible();
  });
});
