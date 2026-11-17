const { chromium } = require('playwright');
(async () => { const b = await chromium.launch(); const out = process.argv[2]; const errs = [];
  for (const [n, vp, cs] of [['phone', { width: 390, height: 780 }, 'dark'], ['small', { width: 320, height: 640 }, 'light'], ['desk', { width: 1366, height: 800 }, 'light']]) {
    const p = await b.newPage({ viewport: vp, colorScheme: cs }); p.on('pageerror', e => errs.push(n + ' ' + e.message));
    for (const v of ['home', 'how', 'app', 'proof', 'manuals']) {
      await p.goto('about:blank'); await p.goto('http://127.0.0.1:8833/landing/_local.html#' + v, { waitUntil: 'load' }); await p.waitForTimeout(900);
      const m = await p.evaluate(() => ({ sw: document.documentElement.scrollWidth, h: document.documentElement.scrollHeight,
        vis: [...document.querySelectorAll('.view')].filter(e => !e.hidden).map(e => e.id).join(),
        small: [...document.querySelectorAll('a,button')].filter(e => { const r = e.getBoundingClientRect(); return r.width > 0 && r.height < 44; }).map(e => e.textContent.trim().slice(0, 18) + ':' + Math.round(e.getBoundingClientRect().height)),
        imgs: [...document.images].filter(i => i.offsetParent && (!i.complete || !i.naturalWidth)).map(i => i.src.split('/').pop()) }));
      console.log(n, v, JSON.stringify(m));
      if (n !== 'small') { await p.screenshot({ path: `${out}/site-${n}-${v}.png` }); if (n === 'phone') await p.screenshot({ path: `${out}/site-${n}-${v}-full.jpg`, fullPage: true, type: 'jpeg', quality: 55 }); }
    }
    await p.close(); }
  console.log('errors', JSON.stringify(errs)); await b.close(); })();
