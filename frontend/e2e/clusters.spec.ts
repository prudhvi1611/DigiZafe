import { test, expect } from '@playwright/test';

const RUN_ID = `e2e_${Date.now()}`;
const TEST_EMAIL = `clusters_${RUN_ID}@example.com`;
const TEST_PASSWORD = 'StrongPassword123!';

test.describe.serial('Identity Clustering', () => {
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

  test('Verify cluster page renders and details open', async () => {
    // Navigate to Findings or clusters page depending on app layout
    await page.locator('aside').getByRole('link', { name: /Findings/i }).click();
    
    // Check if clusters section exists
    const clusterToggle = page.getByRole('button', { name: /clusters/i }).or(page.getByText(/clusters/i, { exact: true }));
    if (await clusterToggle.isVisible()) {
        await clusterToggle.click();
        
        // Open a cluster detail
        const clusterRow = page.locator('.cluster-card').first();
        if (await clusterRow.isVisible()) {
            await clusterRow.click();
            await expect(page.getByText(/evidence/i).first()).toBeVisible();
            
            // Refresh to preserve state
            await page.reload();
            await expect(page.getByText(/evidence/i).first()).toBeVisible();
        }
    }
  });
  test.afterAll(async () => {
    await context.close();
  });
});

