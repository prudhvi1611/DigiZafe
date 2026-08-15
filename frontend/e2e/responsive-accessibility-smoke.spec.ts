import { test, expect } from '@playwright/test';

test.describe.serial('Responsive and Accessibility Smoke', () => {
  test('Desktop layout renders correctly', async ({ page }) => {
    await page.goto('/login');
    // Ensure viewport is desktop
    await page.setViewportSize({ width: 1280, height: 800 });
    await expect(page.getByRole('heading', { name: /sign in/i })).toBeVisible();
  });

  test('Mobile layout renders correctly', async ({ page }) => {
    await page.goto('/login');
    // Emulate mobile
    await page.setViewportSize({ width: 375, height: 667 });
    await expect(page.getByRole('heading', { name: /sign in/i })).toBeVisible();
    // Assuming there might be a hamburger menu or something on the dashboard, but for login just verifying it doesn't crash
  });

  test('Basic keyboard accessibility on login', async ({ page }) => {
    await page.goto('/login');
    
    // Focus email
    await page.getByLabel(/email/i).focus();
    // Tab to password
    await page.keyboard.press('Tab');
    await expect(page.getByLabel(/password/i)).toBeFocused();
    // Tab to submit
    await page.keyboard.press('Tab');
    await expect(page.getByRole('button', { name: /sign in|log in/i })).toBeFocused();
  });
});

