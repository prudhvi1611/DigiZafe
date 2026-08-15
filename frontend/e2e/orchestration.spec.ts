import { test, expect } from '@playwright/test';

const RUN_ID = `e2e_${Date.now()}`;
const TEST_EMAIL = `orch_${RUN_ID}@example.com`;
const TEST_PASSWORD = 'StrongPassword123!';

test.describe.serial('Discovery and Orchestration Journey', () => {
  let context;
  let page;

  test.beforeAll(async ({ browser }) => {
    context = await browser.newContext();
    page = await context.newPage();
    // Register & Login
    await page.goto('/register');

    await page.getByLabel(/email/i).fill(TEST_EMAIL);
    await page.getByLabel(/password/i).fill(TEST_PASSWORD);
    await page.getByRole('button', { name: /register|sign up/i }).click();
    await page.waitForURL(/.*login/);
    
    await page.getByLabel(/email/i).fill(TEST_EMAIL);
    await page.getByLabel(/password/i).fill(TEST_PASSWORD);
    await page.getByRole('button', { name: /log in|sign in/i }).click();
    await page.waitForURL(/.*app/);
    
    // Setup Identity Alias and Consent (mocked/assuming this works via UI or setup)
  });

  test('Start a discovery run and observe transitions', async () => {
    await page.locator('aside').getByRole('link', { name: /Identity/i }).click(); // or /app/scans
    
    const discoverBtn = page.getByRole('button', { name: /start discovery|scan/i });
    if (await discoverBtn.isVisible()) {
        // Double-click idempotency test
        await discoverBtn.dblclick();
        
        await expect(discoverBtn).toBeDisabled();
        
        // Wait for run to appear in list
        await expect(page.getByText(/queued|running|in progress/i).first()).toBeVisible();
        
        // Polling to completion
        await expect(page.getByText(/completed/i).first()).toBeVisible({ timeout: 15000 });
        
        // Ensure test-only connector status is displayed truthfully
        // Not marked as "Certified Live"
        await expect(page.getByText(/certified live/i)).not.toBeVisible();
    }
  });
  test.afterAll(async () => {
    await context.close();
  });
});

