const { chromium } = require('playwright');
(async () => { const b = await chromium.launch(); const out = process.argv[2]; const errs = [];
  for (const [n, vp, cs] of [['desk', { width: 1366, height: 800 }, 'light'], ['phone', { width: 390, height: 800 }, 'dark']]) { const p = await b.newPage({ viewport: vp, colorScheme: cs }); p.on('pageerror', e => errs.push(n + ' ' + e.message));
    await p.goto('http://127.0.0.1:8833/landing/_local.html', { waitUntil: 'load' }); await p.waitForTimeout(1500);
    const m = await p.evaluate(() => ({ sw: document.documentElement.scrollWidth, h: document.documentElement.scrollHeight, demoTop: Math.round(document.querySelector('.demo').getBoundingClientRect().top), demoBottom: Math.round(document.querySelector('.demo').getBoundingClientRect().bottom),
      smallTaps: [...document.querySelectorAll('a,button')].filter(e => { const r = e.getBoundingClientRect(); return r.width > 0 && r.height < 44; }).map(e => e.textContent.trim().slice(0, 16) + ':' + Math.round(e.getBoundingClientRect().height)),
      imgs: [...document.images].filter(i => !i.complete || !i.naturalWidth).map(i => i.src.split('/').pop()) }));
    console.log(n, JSON.stringify(m)); await p.screenshot({ path: `${out}/lp2-${n}-top.png` }); await p.screenshot({ path: `${out}/lp2-${n}-full.jpg`, fullPage: true, type: 'jpeg', quality: 55 }); await p.close(); }
  console.log('errors', JSON.stringify(errs)); await b.close(); })();
