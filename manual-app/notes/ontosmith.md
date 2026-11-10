# OntoSmith: assessment and corpus profile (8 Nov 2026)

[OntoSmith](https://pypi.org/project/ontosmith/) 0.1.9 (MIT, Dongbum Lee) builds an evidence-carrying
knowledge graph in Neo4j under a human-approved, flat schema: an LLM proposes candidate facts and a judge
model ("Jev") decides what is written, each fact keeping its source sentence. Assessed from its PyPI README
(read in full) and its installed code; the GitHub whitepaper was not reachable from this environment.

## Profile of the Manual Handling tenders

Command (deterministic, no LLM, no network; verified in the code: the only HTTP call sits behind the
drafting seat and needs an API key that was not set):

```bash
ontosmith profile corpus --family tenders
```

Input: MinerU's Markdown for `newcastle_rft`, `narembeen_rft`, `centralina_rfp` (3 files, 110,721 characters).
Output: [`ontosmith-profile/`](ontosmith-profile/) — status COMPLETE, 7 claims, **0 decision points**.

| Profile claim | Value | Reality in the tenders |
|---|---|---|
| Defined terms | 0 | About 30: glossary entries (`Shire: The Shire of Narembeen (SoN)`), "X means ...", and 3 parenthetical definitions with curly quotes |
| Recurring clause/section headings | 1 | Expected; the three tenders use different templates |
| Redaction markers, amendment titles | 0 | Correct |

**Why 0 defined terms:** the scanner matches only the US-contract form `(the "Term")` with straight quotes
(`_DEFINED_TERM_RE` in `pipeline/setup_service.py`). Australian tenders define terms in a glossary section and
with "means", and parsers emit curly quotes. So the defined-term registry, one of OntoSmith's strengths for
contracts, would not engage on these tenders without a custom pack or rule.

## Fit for the bid knowledge base

- **Strong fit:** requirement-to-evidence links and entity relationships (projects, clients, subcontractors,
  standards) stored as checked facts with their source sentence — the traceability a compliance matrix needs.
- **Gaps:** no document parsing (text in; pair it with MinerU/Docling); no table handling; defined-term rules
  tuned to US contracts; schema design and approval needed up front; Neo4j required.
- **Residency:** the reference setup routes models through OpenRouter (offshore). Whether the Jev judge can run
  onshore or self-hosted is not stated in the README; resolve before sending tender text.
- **Maturity:** first release 24 Oct 2026, ten releases in two weeks, single author; quality figures are
  machine-adjudicated without a human spot-check.

## Next step if pursued

Draft a tender schema (Requirement, Obligation level, Deliverable, Standard, Insurance, Criterion, Party,
Defined term), add a glossary/"means" defined-term rule, run one capped build on `narembeen_rft` with an
onshore or self-hosted model binding, and score its retrieval against Manual Handling Track D questions.
