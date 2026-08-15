import { test, expect } from '@playwright/test';

const RUN_ID = `e2e_${Date.now()}`;
const TEST_EMAIL = `alice_${RUN_ID}@example.com`;
const TEST_PASSWORD = 'StrongPassword123!';
const TEST_NAME = 'DigiZafe E2E Alice';

test.describe.serial('Authentication and Session Journey', () => {
  let context;
  let page;

  test.beforeAll(async ({ browser }) => {
    context = await browser.newContext();
    page = await context.newPage();
  });

  test.afterAll(async () => {
    await context.close();
  });

  test('User can register successfully', async () => {
    await page.goto('/register');
    
    // Fill out the registration form
    // Note: Assuming specific form field names exist based on typical UI.
    // If not, we will need to update selectors.

    await page.getByLabel(/email/i).fill(TEST_EMAIL);
    await page.getByLabel(/password/i).fill(TEST_PASSWORD);
    
    const submitPromise = page.waitForResponse(response => 
      response.url().includes('/api/v1/auth/register') && response.status() === 201
    );
    await page.getByRole('button', { name: /register|sign up/i }).click();
    await submitPromise;
    
    // Should be redirected to login or dashboard
    await expect(page).toHaveURL(/.*(dashboard|login)/);
  });

  test('User can log in', async () => {
    await page.goto('/login');
    
    await page.getByLabel(/email/i).fill(TEST_EMAIL);
    await page.getByLabel(/password/i).fill(TEST_PASSWORD);
    
    const loginPromise = page.waitForResponse(response => 
      response.url().includes('/api/v1/auth/login') && response.status() === 200
    );
    await page.getByRole('button', { name: /log in|sign in/i }).click();
    await loginPromise;
    
    await expect(page).toHaveURL(/.*\/app/);
  });

  test('User can log out', async () => {
    // We are currently logged in from the previous test and already on /app
    await expect(page.getByRole('heading', { name: /dashboard/i })).toBeVisible();
    await page.getByRole('button', { name: /log out|sign out|profile/i }).first().click();
    
    // Wait for API logout request or redirection to /login
    await expect(page).toHaveURL(/.*login/);
  });

  test('Session is cleared on refresh (in-memory architecture)', async () => {
    // Log in again first
    await page.goto('/login');
    await page.getByLabel(/email/i).fill(TEST_EMAIL);
    await page.getByLabel(/password/i).fill(TEST_PASSWORD);
    
    const loginPromise = page.waitForResponse(response => 
      response.url().includes('/api/v1/auth/login') && response.status() === 200
    );
    await page.getByRole('button', { name: /log in|sign in/i }).click();
    await loginPromise;

    // We are automatically navigated to /app
    await expect(page).toHaveURL(/.*\/app/);
    await expect(page.getByRole('heading', { name: /dashboard/i })).toBeVisible();
    
    // Now refresh, this should clear the in-memory state
    await page.reload();
    await expect(page).toHaveURL(/.*login/);
  });

  test('Protected routes redirect unauthenticated users', async () => {
    // We are unauthenticated now due to the reload
    await page.goto('/app');
    await expect(page).toHaveURL(/.*login/);
  });
});

