const { chromium } = require('playwright');
(async () => { const b = await chromium.launch(); const errs = [];
  const p = await b.newPage({ viewport: { width: 390, height: 800 } }); p.on('pageerror', e => errs.push(e.message)); p.on('response', r => { if (r.status() >= 400) errs.push(r.status() + ' ' + r.url()); });
  await p.goto('http://127.0.0.1:8787/#req-grundfos-cr-cri-crn-10-20-service'); await p.waitForTimeout(1200);
  await p.fill('#q', 'How do I fit the transport bracket?'); await p.click('#go'); await p.waitForSelector('.card .cite', { timeout: 15000 });
  for (let i = 0; i < 20; i++) { await p.waitForTimeout(500); if (await p.locator('.card .fig canvas').count() === await p.locator('.card .fig').count()) break; }
  console.log('figs', await p.locator('.card .fig canvas').count(), '/', await p.locator('.card .fig').count(), (await p.locator('.card .figs').textContent()).slice(0, 80));
  await p.locator('.card .figs').scrollIntoViewIfNeeded(); await p.screenshot({ path: process.argv[2] + '/cf-figs.png' });
  console.log(JSON.stringify(errs)); await b.close(); })();
