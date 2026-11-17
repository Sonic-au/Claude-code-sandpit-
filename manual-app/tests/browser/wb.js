const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch(); const errs = [];
  for (const [name, vp] of [['desk', { width: 1280, height: 900 }], ['phone', { width: 400, height: 860 }]]) {
    const p = await b.newPage({ viewport: vp }); p.on('pageerror', e => errs.push(name + ' pageerror: ' + e.message)); p.on('console', m => { if (m.type() === 'error' && !/fonts\.g/.test(m.text())) errs.push(name + ' console: ' + m.text()); });
    await p.goto('http://127.0.0.1:8811/_local.html#tmqa_makita_drill', { waitUntil: 'networkidle' });
    await p.waitForTimeout(800);
    await p.screenshot({ path: `${process.argv[2]}/shot-${name}-pages.png` });
    if (name === 'desk') {
      await p.click('#tab-questions'); await p.waitForTimeout(300);
      await p.screenshot({ path: `${process.argv[2]}/shot-desk-questions.png` });
      await p.click('#tab-ask'); await p.fill('#ask-q', 'How long does the lamp stay on after releasing the trigger?'); await p.click('text=Search the manual'); await p.waitForTimeout(300);
      const n = await p.$$eval('.extract', x => x.length); const pages = await p.$$eval('.extract .pg', x => x.map(e => e.textContent));
      console.log('extracts', n, pages.join(','));
      await p.screenshot({ path: `${process.argv[2]}/shot-desk-ask.png`, fullPage: false });
      const sw = await p.evaluate(() => document.documentElement.scrollWidth); console.log('desk scrollWidth', sw);
    } else { console.log('phone scrollWidth', await p.evaluate(() => document.documentElement.scrollWidth)); }
  }
  console.log('errors:', JSON.stringify(errs)); await b.close();
})();
