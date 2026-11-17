# To-Do

> Source of truth: [GitHub Issues](https://github.com/Sonic-au/Claude-code-sandpit-/issues)
> This file is a synced summary. Update it alongside any issue changes.

## In Progress
- [ ] #5 — Build content aggregator app (v1). Does not start as written: APScheduler version, missing `greenlet`, template call order (see `content-aggregator/README.md`)
- [ ] Manual Handling on Cloudflare: built and tested locally, not deployed (PR #17, open) _(no issue yet)_

## Open
- [ ] Manual Handling: port "find and load manuals from the web" to the Cloudflare version _(no issue yet)_
- [ ] Manual Handling: meaning-based search (Vectorize) alongside keyword search _(no issue yet)_
- [ ] Manual Handling: person to spot-check the answer grades (`scripts/spot_check.py`) _(no issue yet)_
- [ ] Domain finder: fix the template call so pages render with current FastAPI (see `domain-finder/README.md`) _(no issue yet)_
- [ ] AWS deployment: ECS/Fargate + RDS + Secrets Manager _(GitHub issue not yet created; the #6 placeholder number is now used by Manual Handling, formerly TenderBench)_
- [ ] #2 — Set up project structure
- [ ] #3 — Define agent workflows
- [ ] #4 — Add tool integration guides

## Done
- [x] #6 — Manual Handling (formerly TenderBench): evaluation harness for tender and technical document extraction (PR #10)
- [x] #7 — Retarget the bench to technical manuals for technician Q&A (PR #10)
- [x] #8 — Vendor-website validation and external evals for technical manuals (PR #10)
- [x] Manual Handling: rename, Jev answer grader, workbench scripts, HVAC knowledge graph, tagline (PRs #11–#13)
- [x] Manual Handling: technician app on claude.ai (PR #14)
- [x] Manual Handling: app accuracy measured (94.4% with a manual picked), reader, page links, figures in answers, film-first landing site (PR #15)
- [x] Manual Handling: search-first app, Library and Graph views, find and load manuals from the web with safety scan, progress cards (PR #16)
- [x] Manual Handling: architecture, technical design and READMEs for all three projects (PR #17)
