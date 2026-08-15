import { test, expect } from '@playwright/test';

const RUN_ID = `e2e_${Date.now()}`;
const TEST_EMAIL = `assessment_${RUN_ID}@example.com`;
const TEST_PASSWORD = 'StrongPassword123!';

test.describe.serial('Deterministic Match Assessment', () => {
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

  test('Verify Assessment scores update deterministically', async () => {
    await page.locator('aside').getByRole('link', { name: /PDSS Score/i }).click();
    
    const recalculateBtn = page.getByRole('button', { name: /recalculate|refresh/i });
    if (await recalculateBtn.isVisible()) {
        await recalculateBtn.click();
        // Assume an API call is made to /api/v1/assessments/recalculate
        const response = await page.waitForResponse(resp => resp.url().includes('assessments') && resp.status() === 200);
        
        await expect(page.getByText(/deterministic/i).first()).toBeVisible();
        await expect(page.getByText(/llm/i).first()).not.toBeVisible();
    }
  });
  test.afterAll(async () => {
    await context.close();
  });
});

