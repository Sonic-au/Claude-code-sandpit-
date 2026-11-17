// Render the film's frames in headless Chromium.
//   python3 -m http.server 8833 --bind 127.0.0.1      (in this folder, in another terminal)
//   node render.js out 0 4 & node render.js out 1 4 & node render.js out 2 4 & node render.js out 3 4 & wait
// Each worker renders every frame whose index % workers === worker into out/f/NNNNN.jpg (existing frames are kept,
// so deleting a range re-renders just that range). Worker 0 also writes out/timeline.json and the music (out/music.pcm).
const { chromium } = require('playwright'); const fs = require('fs');
const BASE = process.env.FILM_BASE || 'http://127.0.0.1:8833';
(async () => { const [out, w, n] = [process.argv[2], +process.argv[3], +process.argv[4]]; const FPS = 30;
  fs.mkdirSync(out + '/f', { recursive: true });
  const b = await chromium.launch({ args: ['--use-gl=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] }); const p = await b.newPage({ viewport: { width: 1280, height: 720 } });
  await p.goto(BASE + '/video.html'); await p.evaluate(() => window.ready); const tl = await p.evaluate(() => window.TIMELINE); const frames = Math.ceil(tl.TOTAL * FPS);
  if (w === 0 && !fs.existsSync(out + '/music.pcm')) { fs.writeFileSync(out + '/timeline.json', JSON.stringify({ ...tl, frames, fps: FPS }));
    const m = await b.newPage(); await m.goto(BASE + '/music.html'); const b64 = await m.evaluate(([T, S]) => window.renderMusic(T, S), [tl.TOTAL, tl.START]); fs.writeFileSync(out + '/music.pcm', Buffer.from(b64, 'base64')); await m.close(); }
  for (let f = w; f < frames; f += n) { const file = `${out}/f/${String(f).padStart(5, '0')}.jpg`; if (fs.existsSync(file)) continue;
    await p.evaluate((t) => window.renderAt(t), f / FPS); await p.screenshot({ path: file, type: 'jpeg', quality: 92, clip: { x: 0, y: 0, width: 1280, height: 720 } }); }
  await b.close(); console.log('worker', w, 'done'); })();
