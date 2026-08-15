const fs = require('fs');

const files = ['e2e/identity-anchor.spec.ts', 'e2e/race-and-refresh.spec.ts', 'e2e/cross-user-isolation.spec.ts'];

for (const file of files) {
  let content = fs.readFileSync(file, 'utf8');

  // Change "Identity" to "Identifiers" when clicking the aside link
  content = content.replace(/getByRole\('link', \{ name: \/Identity\/i \}\)/g, "getByRole('link', { name: /Identifiers/i })");

  // Change "e.g. jdoe123" to "you@example.com"
  content = content.replace(/getByPlaceholder\(\/e\.g\.\s*jdoe123\/i\)/g, "getByPlaceholder(/you@example.com/i)");

  // Change TEST_ALIAS or USER_A_ALIAS to an email format so the backend accepts it
  content = content.replace(/alice_\$\{RUN_ID\}/g, "alice_${RUN_ID}@example.com");
  content = content.replace(/race_alias_\$\{RUN_ID\}/g, "race_${RUN_ID}@example.com");

  fs.writeFileSync(file, content);
}
console.log('Fixed identity specs');
