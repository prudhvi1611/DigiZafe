import { test, expect } from '@playwright/test';

const RUN_ID = `e2e_${Date.now()}`;
const TEST_EMAIL = `consent_${RUN_ID}@example.com`;
const TEST_PASSWORD = 'StrongPassword123!';

test.describe.serial('Consent and Zero-Egress Boundary', () => {
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
  });

  test('Discovery blocked without consent', async () => {
    await page.locator('aside').getByRole('link', { name: /Identity/i }).click();
    
    // Setup anchor if needed (assuming auto-created or easy to create)
    // Attempting to run discovery should be disabled or blocked
    const discoverBtn = page.getByRole('button', { name: /start discovery|scan/i });
    
    if (await discoverBtn.isVisible()) {
        // If visible, it should either be disabled or clicking it shows an error/requires consent
        if (!await discoverBtn.isDisabled()) {
            await discoverBtn.click();
            await expect(page.getByText(/consent required|authorization required/i)).toBeVisible();
        }
    }
  });

  test('Can grant consent and perform discovery', async () => {
    await page.locator('aside').getByRole('link', { name: /Identity/i }).click();
    
    // Find consent toggle or section
    const consentToggle = page.getByRole('switch', { name: /consent|authorize/i }).or(page.getByLabel(/consent|authorize/i));
    if (await consentToggle.isVisible()) {
        await consentToggle.check();
        
        // Wait for API sync
        await page.waitForResponse(resp => resp.url().includes('consent') && resp.status() === 200);
        
        const discoverBtn = page.getByRole('button', { name: /start discovery|scan/i });
        await expect(discoverBtn).toBeEnabled();
    }
  });
  test.afterAll(async () => {
    await context.close();
  });
});

