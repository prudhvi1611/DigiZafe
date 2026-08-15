import fs from 'fs';

const files = fs.readdirSync('./e2e').filter(f => f.endsWith('.spec.ts'));

for (const file of files) {
  let content = fs.readFileSync('./e2e/' + file, 'utf8');
  
  // Fix the locator issue: replace `.getByRole(...).first().click()` with `.locator('aside').getByRole(...).click()`
  content = content.replace(/await ([a-zA-Z0-9_]+)\.getByRole\('link', \{ name: \/([^\/]+)\/i \}\)\.first\(\)\.click\(\);/g, "await $1.locator('aside').getByRole('link', { name: /$2/i }).click();");

  // If file uses test.beforeEach and defines TEST_EMAIL, convert to beforeAll
  if (content.includes('test.beforeEach') && content.includes('const TEST_EMAIL')) {
    // Add let context; let page;
    content = content.replace(/test\.describe\.serial\('([^']+)', \(\) => \{/, "test.describe.serial('$1', () => {\n  let context;\n  let page;\n");
    
    content = content.replace(/test\.beforeEach\(async \(\{ page \}\) => \{/, "test.beforeAll(async ({ browser }) => {\n    context = await browser.newContext();\n    page = await context.newPage();");
    
    // Replace async ({ page }) with async () inside test blocks, just in case (though we did this already)
    content = content.replace(/test\('([^']+)', async \(\{ page \}\) => \{/g, "test('$1', async () => {");
    
    // Add afterAll at the end of the describe block. We'll just insert it before the last `});`
    content = content.replace(/\n\}\);\s*$/, "\n  test.afterAll(async () => {\n    await context.close();\n  });\n});\n");
  }

  fs.writeFileSync('./e2e/' + file, content);
}
console.log('Fixed all issues');
