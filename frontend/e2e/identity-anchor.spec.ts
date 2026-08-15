import { test, expect } from '@playwright/test';

const RUN_ID = `e2e_${Date.now()}`;
const TEST_EMAIL = `identity_${RUN_ID}@example.com`;
const TEST_PASSWORD = 'StrongPassword123!';

test.describe.serial('Identity Anchor and Aliases', () => {
  let context;
  let page;

  test.beforeAll(async ({ browser }) => {
    context = await browser.newContext();
    page = await context.newPage();
    
    // Register & Login (fixture setup)
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

  test.afterAll(async () => {
    await context.close();
  });

  test('Navigate to Identity page and check empty state', async () => {
    await page.locator('aside').getByRole('link', { name: /Identifiers/i }).click();
    
    // Verify it loads correctly
    await expect(page.getByRole('heading', { name: /identifiers/i })).toBeVisible();
    
    // Check that we can add an alias
    const addAliasBtn = page.getByRole('button', { name: /^add$/i });
    await expect(addAliasBtn).toBeVisible();
  });

  test('Add a new alias', async () => {
    const TEST_ALIAS = `alice_${Date.now()}@example.com`;
    await page.locator('aside').getByRole('link', { name: /Identifiers/i }).click();

    // Fill alias dialog
    await page.getByPlaceholder(/you@example.com/i).fill(TEST_ALIAS);
    
    const submitPromise = page.waitForResponse(response => 
      response.url().includes('/api/v1/identifiers') && response.status() === 201
    );
    await page.getByRole('button', { name: /save|add/i }).click();
    await submitPromise;
    
    // Verify it appears
    await expect(page.getByText(TEST_ALIAS).first()).toBeVisible({ timeout: 15000 });
  });

  test('Prevent duplicate alias', async () => {
    const TEST_ALIAS = `bob_${Date.now()}@example.com`;
    await page.locator('aside').getByRole('link', { name: /Identifiers/i }).click();
    
    // Add once successfully
    await page.getByPlaceholder(/you@example.com/i).fill(TEST_ALIAS);
    const submitPromise1 = page.waitForResponse(response => 
      response.url().includes('/api/v1/identifiers') && response.status() === 201
    );
    await page.getByRole('button', { name: /save|add/i }).click();
    await submitPromise1;
    await expect(page.getByText(TEST_ALIAS).first()).toBeVisible({ timeout: 15000 });

    // Try to add again
    await page.getByPlaceholder(/you@example.com/i).fill(TEST_ALIAS);
    const submitPromise2 = page.waitForResponse(response => 
      response.url().includes('/api/v1/identifiers') && response.status() === 409
    );
    await page.getByRole('button', { name: /save|add/i }).click();
    await submitPromise2;
    
    // Check for error message
    await expect(page.getByText(/already exists|duplicate|conflict/i)).toBeVisible({ timeout: 15000 });
  });
});
