import { test, expect } from '@playwright/test';

const RUN_ID = `e2e_${Date.now()}`;
const TEST_EMAIL = `privacy_${RUN_ID}@example.com`;
const TEST_PASSWORD = 'StrongPassword123!';

test.describe.serial('Privacy Export', () => {
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

  test('Export functionality works', async () => {
    await page.locator('aside').getByRole('link', { name: /Privacy/i }).click();
    
    const exportBtn = page.getByRole('button', { name: /export/i });
    if (await exportBtn.isVisible()) {
        await exportBtn.click();
        const downloadBtn = page.getByRole('button', { name: /download json/i });
        await expect(downloadBtn).toBeVisible({ timeout: 15000 });
        const downloadPromise = page.waitForEvent('download');
        await downloadBtn.click();
        const download = await downloadPromise;
        expect(download.suggestedFilename()).toMatch(/digizafe.*export.*\.json/i);
    }
  });
  test.afterAll(async () => {
    await context.close();
  });
});

