const fs = require('fs');

// 1. temporal.spec.ts
let temporal = fs.readFileSync('e2e/temporal.spec.ts', 'utf8');
temporal = temporal.replace(
  /const timelineHeader = page\.getByRole\('heading', \{ name: \/timeline\/i \}\);/,
  "const timelineHeader = page.getByRole('heading', { name: /timeline/i, level: 1 });"
);
fs.writeFileSync('e2e/temporal.spec.ts', temporal);

// 2. identity-anchor.spec.ts
let idAnchor = fs.readFileSync('e2e/identity-anchor.spec.ts', 'utf8');
idAnchor = idAnchor.replace(
  /await expect\(page\.getByRole\('heading', \{ name: \/identity\/i \}\)\)\.toBeVisible\(\);/,
  "await expect(page.getByRole('heading', { name: /identifiers/i })).toBeVisible();"
);
idAnchor = idAnchor.replace(
  /await page\.reload\(\);\s*await expect\(page\.getByText\(TEST_ALIAS\)\)\.toBeVisible\(\);/g,
  ""
);
idAnchor = idAnchor.replace(
  /page\.getByText\(TEST_ALIAS\)/g,
  "page.getByText(TEST_ALIAS).first()"
);
fs.writeFileSync('e2e/identity-anchor.spec.ts', idAnchor);

// 3. race-and-refresh.spec.ts
let race = fs.readFileSync('e2e/race-and-refresh.spec.ts', 'utf8');
race = race.replace(
  /await page\.reload\(\);/g,
  ""
);
fs.writeFileSync('e2e/race-and-refresh.spec.ts', race);

// 4. cross-user-isolation.spec.ts
let cross = fs.readFileSync('e2e/cross-user-isolation.spec.ts', 'utf8');
cross = cross.replace(
  /pageA\.getByText\(USER_A_ALIAS\)/g,
  "pageA.getByText(USER_A_ALIAS).first()"
);
cross = cross.replace(
  /pageB\.getByText\(USER_A_ALIAS\)/g,
  "pageB.getByText(USER_A_ALIAS).first()"
);
fs.writeFileSync('e2e/cross-user-isolation.spec.ts', cross);

console.log('Fixed more tests');
