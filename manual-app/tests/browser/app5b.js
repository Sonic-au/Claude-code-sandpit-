const { chromium } = require('playwright');
(async () => { const b = await chromium.launch(); const out = process.argv[2]; const errs = [];
  const p = await b.newPage({ viewport: { width: 390, height: 800 }, colorScheme: 'light' }); p.on('pageerror', e => errs.push(e.message));
  await p.addInitScript(() => { const cols = { searches: [], requests: [] }, subs = { searches: [], requests: [] }; window.__cols = cols; window.__fired = 0;
    const emit = (n) => subs[n].forEach((f) => f({ docs: cols[n].map((d) => ({ id: d.id, data: () => d.data })) }));
    const db = { collection: (n) => ({ add: async (data) => { cols[n].push({ id: n + cols[n].length, data }); emit(n); return {}; }, onSnapshot: (f) => { subs[n].push(f); setTimeout(() => emit(n), 0); return () => {}; } }) };
    window.__ready = (i, cands) => { cols.searches[i].data = { ...cols.searches[i].data, status: 'ready', candidates: cands }; emit('searches'); };
    window.claude = { use: async (n) => n === 'db' ? db : n === 'mcp' ? { callTool: async () => { window.__fired++; return {}; } } : n === 'user' ? { id: async () => 'u_test' } : null }; });
  await p.goto('http://127.0.0.1:8833/app/_local.html#library'); await p.waitForTimeout(1000);
  await p.fill('#lib-q', 'Daikin FTXM'); await p.press('#lib-q', 'Enter'); await p.waitForTimeout(400);
  console.log('after search:', await p.textContent('#found'), '| fired', await p.evaluate(() => window.__fired));
  await p.fill('#req-in', 'daikin  FTXM'); await p.click('#req-go'); await p.waitForTimeout(300); console.log('repeat blocked:', await p.evaluate(() => window.__cols.searches.length), await p.textContent('#req-note'));
  await p.evaluate(() => window.__ready(0, [
    { title: 'Daikin FTXM20-50A Installation manual 3PEN697375-8B', url: 'https://www.daikin.eu/a/FTXM-A_install.pdf', host: 'www.daikin.eu', trust: 'vendor', models: ['FTXM20A', 'FTXM35A'] },
    { title: 'Daikin FTXM20-50A Installation manual 3PEN697375-8B', url: 'https://manualslib.example/ftxm.pdf', host: 'manualslib.example', trust: 'third-party' },
    { title: 'Daikin FTXM-A Operation manual', url: 'https://www.daikin.eu/a/FTXM-A_install.pdf?x=1', host: 'www.daikin.eu', trust: 'vendor' },
    { title: 'Daikin FTXM-R Operation manual 3P600', url: 'https://www.daikin.eu/a/FTXM-R_op.pdf', host: 'www.daikin.eu', trust: 'vendor', models: 'FTXM20R-71R' },
    { title: 'Daikin RXM outdoor service manual', url: 'https://thirdparty.example/rxm.pdf', host: 'thirdparty.example', trust: 'third-party' },
    { title: 'Bad scheme', url: 'javascript:alert(1)', host: 'x' } ]));
  await p.waitForTimeout(300); console.log('candidates shown', await p.locator('.cand').count(), '|', (await p.textContent('#found')).slice(0, 200));
  await p.locator('#found').scrollIntoViewIfNeeded(); await p.screenshot({ path: out + '/a5-found.png' });
  const m = await p.evaluate(() => ({ sw: document.documentElement.scrollWidth })); console.log(JSON.stringify(m));
  await p.locator('.cand input').nth(1).check(); await p.getByRole('button', { name: 'Add selected' }).click(); await p.waitForTimeout(400);
  console.log('requests', JSON.stringify(await p.evaluate(() => window.__cols.requests.map((r) => [r.data.wanted, r.data.url, r.data.trust]))), '| fired', await p.evaluate(() => window.__fired), '| note:', await p.textContent('#req-note'));
  console.log('disabled after add', await p.locator('.cand input:disabled').count()); await p.getByRole('button', { name: /Add all/ }).click(); await p.waitForTimeout(400);
  console.log('requests total', await p.evaluate(() => window.__cols.requests.length), 'fired', await p.evaluate(() => window.__fired));
  console.log('errors', JSON.stringify(errs)); await b.close(); })();
