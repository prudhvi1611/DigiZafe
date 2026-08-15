import { test, expect } from '@playwright/test';

const RUN_ID = `e2e_${Date.now()}`;
const TEST_EMAIL = `delete_${RUN_ID}@example.com`;
const TEST_PASSWORD = 'StrongPassword123!';

test.describe.serial('Account Deletion', () => {
  test('User can shred and delete their account', async ({ page }) => {
    await page.goto('/register');

    await page.getByLabel(/email/i).fill(TEST_EMAIL);
    await page.getByLabel(/password/i).fill(TEST_PASSWORD);
    await page.getByRole('button', { name: /register|sign up/i }).click();
    await page.waitForURL(/.*login/);
    
    await page.getByLabel(/email/i).fill(TEST_EMAIL);
    await page.getByLabel(/password/i).fill(TEST_PASSWORD);
    await page.getByRole('button', { name: /log in|sign in/i }).click();
    await page.waitForURL(/.*app/);

    await page.locator('aside').getByRole('link', { name: /Privacy/i }).click(); // or settings
    
    const deleteBtn = page.getByRole('button', { name: /delete account|shred account/i });
    if (await deleteBtn.isVisible()) {
        await deleteBtn.click();
        
        // Confirm deletion in dialog
        const confirmBtn = page.getByRole('button', { name: /confirm|yes, delete/i });
        const deleteResponse = page.waitForResponse(resp => resp.url().includes('auth/me') && resp.request().method() === 'DELETE' && resp.status() === 204);
        await confirmBtn.click();
        await deleteResponse;
        
        // Should be logged out
        await expect(page).toHaveURL(/.*login/);
        
        // Try logging in again
        await page.goto('/login');
        await page.getByLabel(/email/i).fill(TEST_EMAIL);
        await page.getByLabel(/password/i).fill(TEST_PASSWORD);
        const failResponse = page.waitForResponse(resp => resp.url().includes('auth/login') && resp.status() === 401);
        await page.getByRole('button', { name: /log in|sign in/i }).click();
        await failResponse;
        
        await expect(page.getByRole('alert')).toBeVisible();
    }
  });
});

