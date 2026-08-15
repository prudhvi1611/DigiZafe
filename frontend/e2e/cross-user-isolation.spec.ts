import { test, expect } from '@playwright/test';

const RUN_ID = `e2e_${Date.now()}`;
const USER_A_EMAIL = `isolation_a_${RUN_ID}@example.com`;
const USER_B_EMAIL = `isolation_b_${RUN_ID}@example.com`;
const PASSWORD = 'StrongPassword123!';
const USER_A_ALIAS = `alice_${RUN_ID}@example.com`;

test.describe.serial('Cross-User Isolation', () => {
  test('User B cannot see User A data', async ({ browser }) => {
    // Setup User A
    const contextA = await browser.newContext();
    const pageA = await contextA.newPage();
    await pageA.goto('/register');

    await pageA.getByLabel(/email/i).fill(USER_A_EMAIL);
    await pageA.getByLabel(/password/i).fill(PASSWORD);
    await pageA.getByRole('button', { name: /register|sign up/i }).click();
    await pageA.waitForURL(/.*login/);
    
    await pageA.getByLabel(/email/i).fill(USER_A_EMAIL);
    await pageA.getByLabel(/password/i).fill(PASSWORD);
    await pageA.getByRole('button', { name: /log in|sign in/i }).click();
    await pageA.waitForURL(/.*app/);
    
    // Add alias for User A
    await pageA.locator('aside').getByRole('link', { name: /Identifiers/i }).click();

    await pageA.getByPlaceholder(/you@example.com/i).fill(USER_A_ALIAS);
    const submitPromiseA = pageA.waitForResponse(response => 
      response.url().includes('/api/v1/identifiers') && response.status() === 201
    );
    await pageA.getByRole('button', { name: /save|add/i }).click();
    await submitPromiseA;
    await expect(pageA.getByText(USER_A_ALIAS).first()).toBeVisible();

    // Setup User B
    const contextB = await browser.newContext();
    const pageB = await contextB.newPage();
    await pageB.goto('/register');

    await pageB.getByLabel(/email/i).fill(USER_B_EMAIL);
    await pageB.getByLabel(/password/i).fill(PASSWORD);
    await pageB.getByRole('button', { name: /register|sign up/i }).click();
    await pageB.waitForURL(/.*login/);
    
    await pageB.getByLabel(/email/i).fill(USER_B_EMAIL);
    await pageB.getByLabel(/password/i).fill(PASSWORD);
    await pageB.getByRole('button', { name: /log in|sign in/i }).click();
    await pageB.waitForURL(/.*app/);
    
    // Check User B's identity page - should NOT see User A's alias
    await pageB.locator('aside').getByRole('link', { name: /Identifiers/i }).click();
    await expect(pageB.getByText(USER_A_ALIAS).first()).not.toBeVisible();
    
    await contextA.close();
    await contextB.close();
  });
});

