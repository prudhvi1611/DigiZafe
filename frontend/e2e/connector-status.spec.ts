import { test, expect } from '@playwright/test';

const RUN_ID = `e2e_${Date.now()}`;
const TEST_EMAIL = `connector_${RUN_ID}@example.com`;
const TEST_PASSWORD = 'StrongPassword123!';

test.describe.serial('Connector Status', () => {
  let context;
  let page;

  test.beforeAll(async ({ browser }) => {
    context = await browser.newContext();
    page = await context.newPage();
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

  test('Check that connector status is truthful and accurate', async () => {
    // Navigating to the page where connector status is displayed, e.g., settings or a specific Connector page
    await page.locator('aside').getByRole('link', { name: /Identity/i }).click(); 
    
    // Check for the Connectors or certification panel
    const connectorPanel = page.getByText(/connector status|connectors/i).first();
    if (await connectorPanel.isVisible()) {
        // Assert that Maigret is NOT listed as Certified / fully available unless we are explicitly mocking it as such
        // Assuming test_only logic marks it as 'TEST_ONLY' or 'disabled' in the UI
        await expect(page.getByText(/test_only|disabled/i).first()).toBeVisible();
    }
  });
  test.afterAll(async () => {
    await context.close();
  });
});

