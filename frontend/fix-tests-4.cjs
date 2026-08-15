const fs = require('fs');

let idAnchor = fs.readFileSync('e2e/identity-anchor.spec.ts', 'utf8');
idAnchor = idAnchor.replace(
  /await expect\(page\.getByRole\('alert'\)\)\.toBeVisible\(\);/g,
  "await expect(page.getByText(/already exists|duplicate|conflict/i)).toBeVisible();"
);
fs.writeFileSync('e2e/identity-anchor.spec.ts', idAnchor);

console.log('Fixed identity-anchor');
