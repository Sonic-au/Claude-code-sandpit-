# The Manual Handling film

A 2 minute 26 second film rendered from a web page: a three.js scene with bloom (`video.html`), music generated in
the browser (`music.html`), and narration recorded with ElevenLabs (`vo/*.mp3`, text in `script.json`). The finished
web copy is `../web/landing/manual-handling.mp4`, which the landing page and `../web/film/` play.

| File | What it is |
|---|---|
| `video.html` | The film (uses `ux1-3.png`, screenshots of the app, and the Barlow and JetBrains Mono fonts from npm). `window.renderAt(t)` draws the frame at `t` seconds; scenes are timed to the narration clips |
| `music.html` | `window.renderMusic(total, starts)` renders the score offline and returns 16-bit PCM |
| `script.json` | Narration text for scenes `s1`-`s8` (the app-tour line, `vo/ux.mp3`, was recorded separately) |
| `timeline.json` | Scene start times and durations from the last render |
| `vo/` | Narration clips, voice "Stuart" (`eleven_multilingual_v2`) |
| `narrate.py` | Re-record lines from `script.json` (needs `ELEVENLABS_API_KEY`) |
| `render.js` | Render frames in headless Chromium, several workers in parallel |
| `build.sh` | Mix narration over the music (ducking it under the voice), normalise loudness, encode full and web copies |

## Rebuild it

```bash
npm install                                    # three.js 0.128.0 and the fonts video.html uses
python3 -m http.server 8833 --bind 127.0.0.1   # in this folder, in another terminal
for w in 0 1 2 3; do node render.js out $w 4 & done; wait     # 4,390 frames; about an hour on a 4-core machine
./build.sh out                                 # out/manual-handling.mp4, out/web.mp4, out/poster.jpg
cp out/web.mp4 ../web/landing/manual-handling.mp4
```

Needs Node, Playwright with Chromium, Python 3 and ffmpeg. Frames are rendered with software WebGL (SwiftShader),
so no GPU is needed. To change one scene, edit `video.html`, delete that scene's frames from `out/f/` (30 per second
from its start in `timeline.json`) and run `render.js` again: frames that already exist are kept.

The figures shown in the results scene (169 of 179 correct across twelve manuals, 29 of 29 unanswerable questions
answered "not found", 140 of 141 grades agreed) come from `../results/`.
