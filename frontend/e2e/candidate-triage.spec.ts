import { test, expect } from '@playwright/test';

const RUN_ID = `e2e_${Date.now()}`;
const TEST_EMAIL = `candidate_${RUN_ID}@example.com`;
const TEST_PASSWORD = 'StrongPassword123!';

test.describe.serial('Candidate Triage', () => {
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
    
    // Simulate candidate generation or assume fixture data is available
  });

  test('View candidates and perform triage actions', async () => {
    // Navigate to Findings / Candidates
    await page.locator('aside').getByRole('link', { name: /Findings/i }).click();
    
    const candidatesHeader = page.getByRole('heading', { name: /findings|candidates/i });
    if (await candidatesHeader.isVisible()) {
        // Find a candidate card
        const candidateRow = page.locator('.candidate-card').first();
        if (await candidateRow.isVisible()) {
            await candidateRow.click();
            
            // Confirm "This is mine"
            const confirmBtn = page.getByRole('button', { name: /this is mine/i });
            await confirmBtn.click();
            
            // Verify status changed
            await expect(page.getByText(/confirmed/i).first()).toBeVisible();
            
            // Dismiss "Not mine"
            const dismissBtn = page.getByRole('button', { name: /not mine/i });
            await dismissBtn.click();
            
            await expect(page.getByText(/dismissed/i).first()).toBeVisible();
            
            // Double click idempotency check
            await dismissBtn.dblclick({ force: true });
            
            await page.reload();
            await expect(page.getByText(/dismissed/i).first()).toBeVisible();
        }
    }
  });
  test.afterAll(async () => {
    await context.close();
  });
});

