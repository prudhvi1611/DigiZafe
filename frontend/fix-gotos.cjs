const fs = require('fs');
const files = fs.readdirSync('./e2e').filter(f => f.endsWith('.spec.ts') && f !== 'auth.spec.ts' && f !== 'responsive-accessibility-smoke.spec.ts');
for (const file of files) {
  let content = fs.readFileSync('./e2e/' + file, 'utf8');
  
  content = content.replace(/await ([a-zA-Z0-9_]+)\.goto\('\/app\/([^']+)'\);/g, (match, p1, p2) => {
    let name = p2;
    if (p2 === 'scores') name = 'PDSS Score';
    else if (p2 === 'identity') name = 'Identity';
    else if (p2 === 'privacy') name = 'Privacy';
    else if (p2 === 'findings') name = 'Findings';
    else if (p2 === 'reviews') name = 'Reviews';
    else if (p2 === 'timeline') name = 'Timeline';
    
    return `await ${p1}.getByRole('link', { name: /${name}/i }).first().click();`;
  });
  
  fs.writeFileSync('./e2e/' + file, content);
}
console.log('Fixed gotos');
