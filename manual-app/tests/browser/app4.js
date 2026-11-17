const { chromium } = require('playwright');
(async () => { const b = await chromium.launch(); const out = process.argv[2]; const errs = []; const U = 'http://127.0.0.1:8833/addtest/_local.html';
  const p = await b.newPage({ viewport: { width: 390, height: 800 }, colorScheme: 'light' }); p.on('pageerror', e => errs.push(e.message)); p.on('console', m => { if (m.type() === 'error') errs.push('console ' + m.text().slice(0, 160)); });
  await p.goto(U + '#library'); await p.waitForTimeout(1000); await p.fill('#lib-q', 'TEST rheem'); await p.waitForTimeout(200); console.log('row:', await p.textContent('#lib-list')); await p.screenshot({ path: out + '/a4-lib.png' });
  await p.locator('#lib-list .row button', { hasText: 'Read' }).click(); await p.waitForSelector('#v-body canvas', { timeout: 20000 }); await p.waitForTimeout(300);
  console.log('canvas', await p.evaluate(() => { const c = document.querySelector('#v-body canvas'); return [c.width, c.height, Math.round(c.getBoundingClientRect().width)]; }), await p.evaluate(() => location.hash)); await p.screenshot({ path: out + '/a4-read.png' });
  await p.click('#v-next'); await p.waitForTimeout(1500); await p.selectOption('#v-jump', '12'); await p.waitForTimeout(1500); console.log('p12 canvas', await p.locator('#v-body canvas').count(), await p.evaluate(() => location.hash)); await p.click('#v-zoom'); await p.waitForTimeout(1500); console.log('zoom w', await p.evaluate(() => Math.round(document.querySelector('#v-body canvas').getBoundingClientRect().width)));
  await p.click('#v-close');
  // figure crop check: draw the first stored figure through the page's own helper path by asking a question is not possible without Claude, so check the data and a crop render directly
  const fig = await p.evaluate(async () => { const d = await (await fetch('data.json')).json(); const m = d.manuals.find(x => x.id === 'req_test_rheem'); const pg = Object.keys(m.figs)[0]; return { pg, clip: m.figs[pg][0], n: Object.keys(m.figs).length }; });
  console.log('fig', JSON.stringify(fig));
  await p.goto('about:blank'); await p.goto(U + '#req-test-rheem-p' + fig.pg); await p.waitForSelector('#v-body canvas', { timeout: 20000 }); console.log('deep link ok'); await p.screenshot({ path: out + '/a4-figpage.png' });
  console.log('errors', JSON.stringify(errs)); await b.close(); })();
