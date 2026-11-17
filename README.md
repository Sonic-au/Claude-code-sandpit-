# Claude Code Sandpit

A sandbox repository for building with Claude Code, Anthropic's AI coding assistant. It holds three independent
projects and the instructions the agent follows when working here ([CLAUDE.md](./CLAUDE.md)).

| Project | What it is | Stack | State |
|---|---|---|---|
| [Manual Handling](manual-app/) | Answers technicians' questions from equipment manuals on a phone, with the printed page as proof; plus the test bench that chose how to read manuals | Python bench; app as a claude.ai page and on Cloudflare Workers + D1 + R2; Claude | App live on claude.ai; Cloudflare version built, not deployed |
| [Content aggregator](content-aggregator/) | Collects articles and podcasts from sources you choose and scores each against your topics with Claude | Python, FastAPI, SQLAlchemy, APScheduler | Early, and does not start as written with current libraries (see its README); RSS, website and podcast sources only |
| [Domain finder](domain-finder/) | Suggests startup names in the style of a brand agency and checks whether the .ai, .io and .co domains are free | Python, FastAPI, Claude, RDAP | Built; its pages fail with current FastAPI versions (see its README) |

Start with each project's README. Manual Handling also has an
[architecture](manual-app/docs/ARCHITECTURE.md) and a [technical design](manual-app/docs/TECHNICAL_DESIGN.md).

## Working in this repo

- Tasks are tracked in [GitHub Issues](https://github.com/Sonic-au/Claude-code-sandpit-/issues), summarised in
  [TODO.md](./TODO.md).
- Changes go through pull requests; `main` is never pushed to directly.
- Secrets live in each project's `.env` (git-ignored) or the hosting platform's secret store, never in the repo.
