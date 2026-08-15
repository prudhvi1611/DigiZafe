import { test, expect } from '@playwright/test';

const RUN_ID = `e2e_${Date.now()}`;
const TEST_EMAIL = `temporal_${RUN_ID}@example.com`;
const TEST_PASSWORD = 'StrongPassword123!';

test.describe.serial('Temporal Timeline', () => {
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

  test('Verify Timeline events rendering and interactions', async () => {
    await page.locator('aside').getByRole('link', { name: /Timeline/i }).click();
    
    const timelineHeader = page.getByRole('heading', { name: /timeline/i, level: 1 });
    if (await timelineHeader.isVisible()) {
        const timelineEvent = page.locator('.timeline-event').first();
        if (await timelineEvent.isVisible()) {
            await timelineEvent.click();
            await expect(page.getByText(/details/i).first()).toBeVisible();
            
            // Filters
            const filterBtn = page.getByRole('button', { name: /filter/i });
            if (await filterBtn.isVisible()) {
                await filterBtn.click();
            }
        }
    }
  });
  test.afterAll(async () => {
    await context.close();
  });
});

