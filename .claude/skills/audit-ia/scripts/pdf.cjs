// Rend un livrable HTML en PDF A4 avec Chromium (Playwright).
// Usage : node pdf.cjs entree.html sortie.pdf "texte du pied de page"
//
// Sans Playwright : ouvrir le HTML dans un navigateur et « Imprimer → PDF »
// (le CSS d'impression est le même).
const path = require('path');

let chromium;
try {
  ({ chromium } = require('playwright'));
} catch (e) {
  console.error('Module playwright introuvable (npm i -g playwright, ou impression manuelle du HTML).');
  process.exit(2);
}

const echapper = (t) => t.replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

(async () => {
  const [, , entree, sortie, pied = ''] = process.argv;
  if (!entree || !sortie) {
    console.error('Usage : node pdf.cjs entree.html sortie.pdf "pied de page"');
    process.exit(2);
  }
  const navigateur = await chromium.launch();
  try {
    const page = await navigateur.newPage();
    await page.goto('file://' + path.resolve(entree), { waitUntil: 'load' });
    await page.pdf({
      path: sortie,
      format: 'A4',
      printBackground: true,
      margin: { top: '16mm', bottom: '18mm', left: '17mm', right: '17mm' },
      displayHeaderFooter: true,
      headerTemplate: '<span></span>',
      footerTemplate:
        '<div style="font-family:Helvetica,Arial,sans-serif;font-size:7.5px;color:#6c6057;width:100%;' +
        'padding:0 17mm;display:flex;justify-content:space-between">' +
        `<span>${echapper(pied)}</span>` +
        '<span><span class="pageNumber"></span> / <span class="totalPages"></span></span></div>',
    });
  } finally {
    await navigateur.close();
  }
})().catch((e) => {
  console.error(e.message || String(e));
  process.exit(1);
});
