const fs = require('fs');

// 1. identity-anchor.spec.ts
let idAnchor = fs.readFileSync('e2e/identity-anchor.spec.ts', 'utf8');
idAnchor = idAnchor.replace(
  /page\.getByRole\('button', \{ name: \/add alias\|add identifier\/i \}\)/g,
  "page.getByRole('button', { name: /^add$/i })"
);
fs.writeFileSync('e2e/identity-anchor.spec.ts', idAnchor);

// 2. privacy-export.spec.ts
let privacy = fs.readFileSync('e2e/privacy-export.spec.ts', 'utf8');
privacy = privacy.replace(
  /if \(await exportBtn\.isVisible\(\)\) \{([\s\S]*?)\}/,
  `if (await exportBtn.isVisible()) {
        await exportBtn.click();
        const downloadBtn = page.getByRole('button', { name: /download json/i });
        await expect(downloadBtn).toBeVisible({ timeout: 15000 });
        const downloadPromise = page.waitForEvent('download');
        await downloadBtn.click();
        const download = await downloadPromise;
        expect(download.suggestedFilename()).toMatch(/digizafe.*export.*\\.json/i);
    }`
);
fs.writeFileSync('e2e/privacy-export.spec.ts', privacy);

console.log('Fixed identity-anchor and privacy-export');
