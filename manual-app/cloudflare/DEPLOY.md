# Manual Handling on Cloudflare

One Worker serves everything:

| Part | Cloudflare service | What it holds |
|---|---|---|
| The app page, page images, figures, the shipped PDFs | Workers static assets (`public/`) | Files that ship with each deploy |
| API (`src/worker.js`) | Worker | `/api/manuals`, `/api/pages`, `/api/search`, `/api/ask`, `/api/feedback` |
| Library database | D1 (`migrations/`, seeded from `seed/data.json`) | Manuals, page text, search passages and counts, feedback, answer log |
| Manuals added later | R2 bucket `manual-handling-files` | Served at the same `/files/...` paths as the shipped files |
| Written answers | Claude API (`claude-opus-5-5`, effort `medium`) | Called by the Worker; needs `ANTHROPIC_API_KEY` |

Search is the browser app's keyword search moved into the database. `scripts/check_search.mjs` compares the two on
all 201 test questions, each searched in its own manual and across the library: 402 of 402 results are identical.

## First deployment (once)

Needs Node 20+ and a Cloudflare account. From this folder:

```bash
npm install
npx wrangler login                               # opens the browser to sign in to Cloudflare
npx wrangler d1 create manual-handling           # copy the database_id it prints into wrangler.jsonc
npx wrangler r2 bucket create manual-handling-files
npm run db:remote                                # creates the tables and loads the 19 manuals
npx wrangler secret put ANTHROPIC_API_KEY        # paste the key when asked; it is never stored in a file
npm run deploy                                   # prints the app's address, e.g. https://manual-handling.<you>.workers.dev
```

After that, `npm run deploy` publishes changes. To deploy on every merge instead, connect the repository in the
Cloudflare dashboard (Workers & Pages, the Worker, Settings, Build): root directory `manual-app/cloudflare`,
deploy command `npx wrangler deploy`.

## Settings (`wrangler.jsonc`, `vars`)

| Setting | Default | Meaning |
|---|---|---|
| `MH_MODEL` | `claude-opus-5-5` | Model for written answers |
| `MH_EFFORT` | `medium` | How hard the model thinks; `low` is faster and cheaper |
| `MH_ASKS_PER_CLIENT_PER_HOUR` | `30` | Written answers one device can get per hour |
| `MH_ASKS_PER_DAY` | `500` | Written answers for everyone per day; past it the app still shows the matching passages |

The app has no sign-in, so these limits are what keeps the Claude bill bounded. Set a monthly spend limit on the
API key in the Claude Console as well.

## Run it locally

```bash
npm install
npm run db:local                 # local D1 with the same data
printf 'MH_FAKE_LLM=1\n' > .dev.vars   # stand-in answers; or put ANTHROPIC_API_KEY=... in .dev.vars for real ones
npm run dev                      # http://localhost:8787
npm run test:search              # in another terminal: search parity check against the browser app
```

## Not built yet

- Finding and loading new manuals from the web (the claude.ai version does this). The plan: the Library search
  starts a job that searches makers' sites and lists candidates in D1; chosen manuals are parsed and added to D1
  and R2. Parsing PDFs needs Python, so that step runs outside the Worker (a Cloudflare Container, or the existing
  Claude Code agent calling an admin endpoint).
- Meaning-based search (Vectorize) alongside the keyword search.
