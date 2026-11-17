# Browser checks

Playwright scripts used while building the app, landing page, workbench and film. Each opens a page in headless
Chromium at phone (390 px) and sometimes desktop width, walks through it, prints what it found (counts, sideways
scroll width, page errors, failed requests) and saves screenshots to the folder given as the first argument.

```bash
node cf.js /tmp/shots        # needs: npm run dev in ../../cloudflare (Wrangler on port 8787, MH_FAKE_LLM=1)
```

| Script | Checks | Expects at |
|---|---|---|
| `cf.js` | Cloudflare build: ask, streamed answer, page chips, figures, feedback, reader and text view, no-match, library, PDF reader, graph | `127.0.0.1:8787/` (Wrangler) |
| `cf3.js` | Cloudflare build: figures cut from a PDF manual's cited page | `127.0.0.1:8787/` |
| `app3.js` | claude.ai app: Ask, Library and Graph views, search, deep links | `127.0.0.1:8833/app/_local.html` |
| `app4.js` | claude.ai app: reader drawing pages from a PDF manual | `127.0.0.1:8833/addtest/_local.html` |
| `app5.js`, `app5b.js` | claude.ai app: web search list, duplicates removed, load selected / all (stand-in database) | `127.0.0.1:8833/app/_local.html` |
| `app6.js` | claude.ai app: library thumbnails, graph grouped by equipment type and maker | `127.0.0.1:8833/addtest/_local.html` |
| `app7.js` | claude.ai app: search and loading progress cards, watch-progress list | `127.0.0.1:8833/app/_local.html` |
| `live.js` | claude.ai app with the live library data pulled from the published app | `127.0.0.1:8833/live/_local.html` |
| `lp2.js`, `site.js` | Landing site: pages, tap-target sizes, sideways scroll, images | `127.0.0.1:8833/landing/_local.html` |
| `wb.js`, `wb2.js` | Workbench: manual reader, extracts, phone and desktop layout | `127.0.0.1:8811/_local.html` |
| `vtest.js` | Film page renders, and time per frame | `127.0.0.1:8833/video/video.html` |

Only the `cf*.js` scripts run as they are against the Cloudflare build. The others were run against a local copy of
the claude.ai pages: a static server (`python3 -m http.server`) over a folder holding the page, its data files and a
`_local.html` wrapper (the page inside `<!doctype html>`, a viewport meta tag and `[hidden]{display:none!important}`,
which claude.ai adds when it publishes). The ports and folder names in the table are those used during development;
change the URL at the top of a script to point it elsewhere.
