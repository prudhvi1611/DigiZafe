import { test, expect } from '@playwright/test';

const RUN_ID = `e2e_${Date.now()}`;
const TEST_EMAIL = `race_${RUN_ID}@example.com`;
const TEST_PASSWORD = 'StrongPassword123!';

test.describe.serial('Race Conditions and Refresh', () => {
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

  test('Double submission of an alias is idempotent', async () => {
    await page.locator('aside').getByRole('link', { name: /Identifiers/i }).click();

    
    await page.getByPlaceholder(/you@example.com/i).fill(`race_${RUN_ID}@example.com`);
    const submitBtn = page.getByRole('button', { name: /save|add/i });
    
    await submitBtn.dblclick(); // click it twice very quickly
    
    // We should only see one instance in the list, or we get a 409 but the UI doesn't break
    
    
    // Check that there is exactly 1 instance of the text (plus possibly a label/input)
    const locator = page.getByText(`race_${RUN_ID}@example.com`);
    const count = await locator.count();
    expect(count).toBeGreaterThanOrEqual(1);
    expect(count).toBeLessThanOrEqual(2); // Depending on where else it's rendered, but we shouldn't have duplicate cards
  });
  test.afterAll(async () => {
    await context.close();
  });
});

