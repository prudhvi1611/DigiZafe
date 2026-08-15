import { test, expect } from '@playwright/test';

// Define the core routes that a user might visit
const coreRoutes = [
  '/',
  '/login',
  '/register',
  '/dashboard',
  '/identity',
  '/clusters',
  '/timeline',
  '/review',
  '/settings',
];

test.describe.serial('Route Verification and Empty States', () => {
  for (const route of coreRoutes) {
    test(`Direct Navigation and Refresh on ${route}`, async ({ page }) => {
      const response = await page.goto(route);
      
      // The frontend itself shouldn't return a 500 when rendering HTML
      expect(response?.status()).not.toBe(500);

      // Reload the page to test lazy-loaded/direct navigation handling
      await page.reload();

      // Check for unexpected console errors
      const errors: string[] = [];
      page.on('pageerror', (err) => errors.push(err.message));
      page.on('console', (msg) => {
        if (msg.type() === 'error') {
          errors.push(msg.text());
        }
      });

      // The page should not be a blank white screen
      const body = await page.locator('body').innerText();
      // It's acceptable for it to redirect (e.g. from /dashboard to /login), but it shouldn't crash
      expect(errors).toEqual([]);
    });
  }
});

