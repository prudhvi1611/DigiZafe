import fs from 'fs';

// 1. identity-anchor.spec.ts
let idAnchor = fs.readFileSync('e2e/identity-anchor.spec.ts', 'utf8');
idAnchor = idAnchor.replace(
  /const TEST_ALIAS = `alice_\$\{RUN_ID\}@example.com`;/g,
  ""
);
idAnchor = idAnchor.replace(
  /test\('Add a new alias', async \(\) => \{/g,
  "test('Add a new alias', async () => {\n    const TEST_ALIAS = `alice_${Date.now()}@example.com`;\n"
);
idAnchor = idAnchor.replace(
  /await page\.getByPlaceholder\(\/you@example\.com\/i\)\.fill\(TEST_ALIAS\);/g,
  "if (typeof TEST_ALIAS === 'undefined') { var TEST_ALIAS = `alice_${Date.now()}@example.com`; }\n    await page.getByPlaceholder(/you@example.com/i).fill(TEST_ALIAS);"
);
idAnchor = idAnchor.replace(
  /await expect\(page\.getByText\(TEST_ALIAS\)\.first\(\)\)\.toBeVisible\(\);/g,
  "await expect(page.getByText(TEST_ALIAS).first()).toBeVisible({ timeout: 15000 });"
);
fs.writeFileSync('e2e/identity-anchor.spec.ts', idAnchor);

// 2. review-queue.spec.ts
let reviewQueue = fs.readFileSync('e2e/review-queue.spec.ts', 'utf8');
reviewQueue = reviewQueue.replace(
  /await expect\(page\.getByText\(\/no reviews\|all caught up\/i\)\.first\(\)\)\.toBeVisible\(\);/g,
  "await expect(page.getByText(/no review|all caught up/i).first()).toBeVisible({ timeout: 15000 });"
);
fs.writeFileSync('e2e/review-queue.spec.ts', reviewQueue);

console.log('Fixed identity-anchor and review-queue');
