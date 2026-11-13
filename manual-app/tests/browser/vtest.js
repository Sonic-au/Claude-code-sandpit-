const { chromium } = require('playwright');
(async () => { const b = await chromium.launch({ args: ['--use-gl=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] }); const p = await b.newPage({ viewport: { width: 1280, height: 720 } }); const errs = [];
  p.on('pageerror', e => errs.push(e.message)); p.on('console', m => { if (m.type() === 'error') errs.push(m.text()); });
  await p.goto('http://127.0.0.1:8833/video/video.html'); await p.evaluate(() => window.ready); const tl = await p.evaluate(() => window.TIMELINE); console.log(JSON.stringify(tl));
  const times = process.argv.slice(3).map(Number); const t0 = Date.now();
  for (const t of times) { await p.evaluate((t) => window.renderAt(t), t); await p.screenshot({ path: `${process.argv[2]}/vt-${t}.jpg`, type: 'jpeg', quality: 80, clip: { x: 0, y: 0, width: 1280, height: 720 } }); }
  console.log('ms/frame', (Date.now() - t0) / times.length, 'errors', JSON.stringify(errs.slice(0, 5))); await b.close(); })();
