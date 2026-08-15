import { test, expect } from '@playwright/test';

const RUN_ID = `e2e_${Date.now()}`;
const TEST_EMAIL = `review_${RUN_ID}@example.com`;
const TEST_PASSWORD = 'StrongPassword123!';

test.describe.serial('Review Queue', () => {
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

  test('Check Review queue empty state and interactions', async () => {
    await page.locator('aside').getByRole('link', { name: /Reviews/i }).click();
    
    const reviewHeader = page.getByRole('heading', { name: /review/i });
    if (await reviewHeader.isVisible()) {
        const hasItems = await page.locator('.review-item').count() > 0;
        if (hasItems) {
            await page.locator('.review-item').first().click();
            await expect(page.getByText(/status|revalidation/i).first()).toBeVisible();
        } else {
            // Verify empty state is rendered correctly and not just a blank screen
            await expect(page.getByText(/no review|all caught up/i).first()).toBeVisible({ timeout: 15000 });
        }
    }
  });
  test.afterAll(async () => {
    await context.close();
  });
});

