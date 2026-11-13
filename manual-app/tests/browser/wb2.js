const { chromium } = require('playwright');
(async () => { const b = await chromium.launch(); const p = await b.newPage({ viewport: { width: 400, height: 860 } });
  await p.goto('http://127.0.0.1:8811/_local.html#tmqa_makita_drill', { waitUntil: 'networkidle' }); await p.waitForTimeout(500);
  console.log(await p.evaluate(() => [...document.querySelectorAll('body *')].filter(e => e.getBoundingClientRect().right > 401).slice(0, 8).map(e => e.tagName + '.' + e.className + ' ' + Math.round(e.getBoundingClientRect().width)).join('\n')));
  await b.close(); })();
