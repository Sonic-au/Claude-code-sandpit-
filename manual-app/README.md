# Manual Handling

**Let AI handle your manuals.** *The right answer, on the right page.*

Run it with `python -m manual_app`.

An evaluation harness for choosing how to ingest **technical manuals** into a knowledge base that answers
**technician questions** with page citations. It scores document parsers, and the extraction and retrieval steps
built on them, on what a technician relies on: procedure steps in order, warnings kept with their step, spec and
torque tables, values with their units, exact part numbers and commands, and answers that cite the right page.

Alongside the bench: a workbench for inspecting pages, reviewing answers and adding labelled questions, and a
knowledge graph that links related manuals.

## Why another benchmark

Existing benchmarks measure parsing in general, not technical manuals:

| Benchmark | What it gives us | Gap for manuals |
|---|---|---|
| [OmniDocBench](https://arxiv.org/abs/2412.07626) (CVPR 2025) | Page-level edit distance, TEDS, reading order | Academic/textbook/newspaper pages; no manuals, no safety notices |
| [ParseBench](https://arxiv.org/abs/2604.08538) (LlamaIndex) | Rule-based tests on enterprise pages | Vendor-run; no technician questions |
| [RealDocBench](https://arxiv.org/abs/2606.07401) (Extend) | Field-level accuracy, strict per-question scoring | Regulated forms, not manuals |
| olmOCR-Bench (in [olmOCR](https://arxiv.org/abs/2502.18443)) | Cheap deterministic unit tests | Mostly academic PDFs |

Manual Handling borrows one method from each and applies it to public technical manuals.

## Tracks

| Track | Measures | Method (borrowed from) |
|---|---|---|
| **A. Parse fidelity** | Text similarity on transcribed pages; table TEDS and TEDS-S | Normalised edit distance and TEDS ([OmniDocBench](https://arxiv.org/abs/2412.07626), [PubTabNet](https://arxiv.org/abs/1911.10683)) |
| **B. Rule tests** | Pass rate on checks: clause verbatim, table cell, reading order, headings, form labels, numbers, running headers absent | Deterministic unit tests ([ParseBench](https://arxiv.org/abs/2604.08538), olmOCR-Bench) |
| **C. Extraction** | Every WARNING/CAUTION/NOTE notice, warning recall, *all warnings found* | Field-level, strict scoring ([RealDocBench](https://arxiv.org/abs/2606.07401)) |
| **D. Retrieval and answers** | Evidence recall@5 and MRR for BM25, dense, hybrid, hybrid + heading context and hybrid + reranker; with an LLM: answer accuracy (LLM-judged, strict, lenient), citation accuracy, abstention on unanswerable questions | RAG evaluation practice (RAGAS-style context recall, faithfulness) |

Every score is also reported per document, with seconds per page, cost per 1,000 pages, data residency and licence.

Tracks C and D run the **same** extractor and retriever over each parser's output, so they show how parsing
quality flows through to the warnings found and to answers.

## Corpus

Public documents only; PDFs are downloaded and checksum-verified, not committed. Three manifests: `manuals` (below), `techmanualqa` (three consumer manuals from
TechManualQA-700) and `hvac` (four HVAC manuals for the knowledge graph).

**`corpus/manuals.yaml` (default)**

| Id | Document | Kind | Pages used | Why |
|---|---|---|---|---|
| `xylem_empa` | Xylem e-MPA/MPR/MPD pump instruction manual IM309 | Equipment O&M | 11 | Safety notices, coupling torque table, commissioning steps, troubleshooting tables |
| `postgresql_backup` | PostgreSQL 17 manual, ch. 25 Backup and Restore | Software | 7 of 3,100 | Commands and code blocks, WAL archiving, recovery procedure |
| `ti_lm317` | TI LM317 regulator datasheet | Specification | 9 | Min/typ/max spec tables with conditions and footnotes, pin functions |
| `faa_ac43` | FAA AC 43.13-1B ch. 7 (hardware, safetying, cables) | Aviation | 8 of 646 | Large grouped-header torque table, CAUTION boxes, AN/MS part numbers |
| `army_tm_tqg` | US Army TM 9-6115-639-13 (3 kW generator) | Defence | 11 of 304 | Warning summary, PMCS and troubleshooting tables, start-up procedures |
| `army_tm_scan` | Army TM pages as a simulated scan | Defence | 4 | OCR path, scored against the digital version's gold |

Gold annotations (`gold/`) were made from page images, never from a parser's output, following
[`gold/ANNOTATION.md`](gold/ANNOTATION.md), and checked with `python -m manual_app.validate_gold`.

## Parsers

`python -m manual_app parsers` shows which can run in your environment.

| Adapter | Type | Residency | Licence | Status |
|---|---|---|---|---|
| `pypdf-text` | PDF text layer (lower bound) | local | BSD | run |
| `pymupdf4llm` | Rule-based Markdown, RapidOCR | local | AGPL-3.0 / commercial | run |
| `liteparse`, `liteparse-md` | LlamaIndex open-source parser, Tesseract OCR | local | Apache-2.0 | run |
| `docling` | Layout model + TableFormer + RapidOCR | local | MIT | run |
| `mineru` | OmniDocBench's best pipeline tool | local | AGPL-3.0 | adapter (heavy on CPU) |
| `marker`, `unstructured-*` | Open-source pipelines | local | GPL-3.0 / Apache-2.0 | adapter |
| `vlm` | Any OpenAI-compatible vision model (olmOCR-2, Chandra, Qwen-VL via vLLM/Ollama) | self-hosted | per model | adapter, needs GPU |
| `claude-vlm` | Claude reading page images; onshore via Bedrock `ap-southeast-2` | cloud-au | commercial | adapter |
| `azure-di-layout` | Azure Document Intelligence (Australia East) | cloud-au | commercial | adapter |
| `llamaparse` | LlamaParse API (US/EU only) | offshore | commercial | adapter, `--allow-offshore` |
| `reducto` | Reducto API (AU endpoint claimed by vendor) | offshore / cloud-au | commercial | adapter |

"Adapter" means written against the service's documented API but not run when the bench was built (no keys or
GPU in that environment); smoke-test one document before a full run. Offshore parsers are skipped unless
`--allow-offshore` is passed, and should only ever see public documents.

## No-cost setup (current default)

Everything below runs with free, open-source software on a CPU: no API keys, no paid services, no data leaving
the machine. LLM steps are skipped automatically when no Anthropic credential is set.

```bash
cd manual_app
scripts/setup.sh                          # one-time install (parsers, models, scoring libraries)
. scripts/env.sh && scripts/run_all.sh    # fetch, build independent gold, parse with seven parsers, score
python -m manual_app run --parsers docling --no-llm   # just the recommended parser
```

| Parser | Licence | Notes |
|---|---|---|
| **Docling** (recommended start) | MIT | Best on manuals, large tables; safe for commercial use |
| LiteParse | Apache-2.0 | Light and fast, weaker on tables and scans |
| MinerU | AGPL-3.0 | Strong on simpler tables; AGPL obligations if offered as a service |
| PyMuPDF4LLM | AGPL-3.0 | Fastest good option; AGPL (commercial licence from Artifex) |

Retrieval uses the free BGE-small embedding model on CPU. Without an LLM you keep parsing, table, step-order,
warning and part-number checks, rule-based extraction, and page-cited retrieval; you give up generated answers and
Claude extraction, which switch on later just by setting `ANTHROPIC_API_KEY`.

## Running it

```bash
python -m venv .venv && . .venv/bin/activate
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu   # CPU builds
pip install -r requirements.txt
npm install @llamaindex/liteparse @tesseract.js-data/eng      # optional: LiteParse
export LITEPARSE_BIN=$PWD/node_modules/.bin/lit               # and LITEPARSE_CONFIG for local OCR data

python -m manual_app fetch                                   # download + build bench PDFs
python -m manual_app run                                     # default local parsers, all tracks
python -m manual_app run --parsers docling,vlm --docs narembeen_rft,narembeen_scan
python -m pytest -q tests
```

Results land in `results/<timestamp>/` as `report.md`, `summary.json` and `scores.json`. Parser outputs are cached
in `data/outputs/` (use `--force` to re-parse).

**LLM steps** run on **Claude** by default: safety-notice extraction
and answering each question with page citations (scored for accuracy, citations and abstention). They use Claude
Opus 5.5 (`claude-opus-5-5`, effort `medium`) through the official `anthropic` SDK, with structured outputs for
extraction and server-side refusal fallback on the Claude API. They run when an Anthropic credential is present
and are never simulated otherwise:

```bash
export ANTHROPIC_API_KEY=...                       # Claude API (US); public documents only
export TB_LLM_PROVIDER=bedrock TB_LLM_REGION=ap-southeast-2   # or Claude on Amazon Bedrock in Sydney (onshore)
export TB_LLM_EFFORT=high                          # optional: low | medium | high | xhigh | max
python -m manual_app run --parsers docling,mineru,pymupdf4llm
```

**On a Claude subscription (no API bill):** `TB_LLM_PROVIDER=session` writes each LLM task to
`data/session_llm/tasks.jsonl` instead of calling an API. Then, in a Claude Code session:

```bash
TB_LLM_PROVIDER=session python -m manual_app run --parsers docling   # queues tasks
python scripts/session_tool.py split 4 /tmp/shards                    # ask session agents to `show` and `answer` each
python scripts/session_tool.py merge /tmp/shards
TB_LLM_PROVIDER=session python -m manual_app run --parsers docling   # scores; repeat while tasks are pending
```

Answers are graded in a later pass, so expect three runs. Responses are cached by prompt hash, so re-scoring is free.

**Answer graders.** `TB_JUDGE` chooses who grades answers against the gold answer:

| `TB_JUDGE` | Grader |
|---|---|
| `claude` (default) | Claude grades every answer. |
| `jev` | [TypeSafe Jev](https://arxiv.org/abs/2609.26550) grades every answer: a typed decision model that returns a probability for each label (correct / partial / incorrect) and no text. Its top probability is the confidence. |
| `cascade` | Jev grades first. Grades with confidence at or above `TB_JEV_THRESHOLD` (default 0.9) are final; the rest go to Claude ("accept when confident, escalate when unsure"). |
| `compare` | Jev and Claude both grade everything. The report shows their agreement and a threshold sweep (escalation rate and agreement with Claude at each threshold); run it once to choose the threshold. |

Jev settings: `TB_JEV_URL` (default `https://api.typesafe.ai/v1/systemone`), `TB_JEV_MODEL` (default `jev-1.14.0`, the `jev-latest` build in November 2026;
it is pinned because a threshold is tuned to one build) and `TB_JEV_API_KEY` (bearer token; in a cloud session
save it as a network secret instead). Jev is a hosted, offshore service, priced at US$0.042 per million input tokens
in the paper (check current pricing), so send it public documents only. Access was invite-only (waitlist) in
September 2026. Grading never stops a run: when Jev fails, that answer is left ungraded and judged accuracy is
not reported for its document.

Using a different model family to grade avoids Claude grading Claude. To check either grader against a person:

```bash
python scripts/spot_check.py export results/<run> 20   # blind CSV: fill the `human` column
python scripts/spot_check.py score results/<run>/spot_check.csv
```

The sample takes Jev-Claude disagreements first, then low-confidence Jev grades, then random answers.

The report adds an LLM table (extraction F1, critical recall, all-critical-found, answer accuracy (judged, strict and
lenient), citation accuracy, abstention) and a usage line with token counts and estimated cost (`llm_usage.json`).

**Network notes.** Docling downloads models from Hugging Face; behind a proxy set `HF_HUB_DISABLE_XET=1` and allow
`huggingface.co` plus its CDN. LiteParse OCR fetches Tesseract data from GitHub unless `LITEPARSE_CONFIG` points at
a JSON file with `{"tessdataPath": "<dir with eng.traineddata>"}`.

## Results: technical manuals (9 Nov 2026, local parsers, CPU only)

The 9 Nov run's folder was superseded; the same parsers were re-run on 10 Nov:
[`results/2026-11-10-manuals-free/report.md`](results/2026-11-10-manuals-free/report.md).

| Parser | Overall | Table TEDS | Rule tests | Warning recall | Scan text | s/page | Licence |
|---|---|---|---|---|---|---|---|
| Docling | **80.5** | 75.1 | 95.2 | 90.9 | 92.3 | 4.7 | MIT |
| PyMuPDF4LLM | 77.5 | 68.6 | 83.6 | 90.9 | 90.2 | 1.1 | AGPL-3.0 |
| MinerU | 77.1 | 67.1 | 92.4 | 90.9 | 91.2 | 3.9 | AGPL-3.0 |
| LiteParse (Markdown) | 69.8 | 43.3 | 78.5 | 77.3 | 76.9 | 0.8 | Apache-2.0 |
| pypdf text layer | 54.9 | 0.0 | 65.0 | 35.3 | 0.0 | 0.02 | BSD |

- **Docling leads on manuals.** It kept the FAA's large grouped-header torque
  table (95% TEDS against 43% for MinerU) and passed every procedure-order, safety and part-number check.
- **MinerU is best on simpler tables** (Xylem torque and troubleshooting tables, 99.8% TEDS) but weakest on
  value-with-unit checks (79%), so no single parser wins every manual.
- **Procedure steps, warnings and part numbers survive** in every layout-aware parser (96-100% of checks).
  Running headers are the difference: PyMuPDF4LLM and LiteParse leave them in the text.
- **Warnings:** the rule-based extractor finds 91% of warnings from Docling, MinerU or PyMuPDF4LLM output, but
  no parser/extractor pair found every warning in the Army manual. Safety F1 is low (40-45%) because the baseline
  also picks up hazard definitions and misses notes printed as footnotes.
- **The simulated scan costs structure, not words:** text similarity stays at 90-93%, but rule pass rates drop to
  64-79%, mostly table cells.
- **The datasheet is hardest for text** (66-83% text similarity for every parser): dense two-column spec tables
  with conditions and footnotes.
- **Retrieval is at ceiling again** (95-100% recall@5); harder technician questions are needed to separate parsers.

## Independent gold: vendor websites and TechManualQA-700 (10 Nov 2026)

`python -m manual_app vendor` builds gold that does not come from our annotators (`corpus/vendor_sources.yaml`,
`manual_app/vendor.py`); vendor pages are snapshotted with URL, date and SHA-256. The report shows it as
**Independent checks**.

| Source | What it gives | Size |
|---|---|---|
| PostgreSQL HTML manual (vendor's own source) | Commands, headings, notices and heading order, mapped to PDF pages | 24 checks |
| TI LM317 product page | Spec values located in the datasheet, plus technician questions | 7 checks, 7 questions |
| [TechManualQA-700](https://zenodo.org/records/17410809) (CC BY 4.0) | External questions over vendor manuals (`--corpus techmanualqa`): Makita drill, Prusa MK4S, DJI Mavic Pro | 105 questions, 85 snippet checks |

- **The independent checks confirm the ranking from our own gold** on the manuals corpus: Docling 92.9%,
  PyMuPDF4LLM 85.7%, MinerU 78.6%.
- **The vendor website and the manual disagree.** Six of TI's 13 product-page parameters are not stated in the
  datasheet in that form (noise in µVrms, PSRR at 100 kHz, a single 24 °C/W θJA, 2000 mV dropout, quiescent current,
  accuracy); see `gold/ti_lm317/vendor_mismatches.json`. A knowledge base answering from the manual would give a
  technician a different answer from the website.
- **TechManualQA does not separate parsers:** every parser keeps 91-100% of the answer snippets and finds the evidence
  page for 91-96% of questions (hybrid + heading context, recall@5), with the plain PDF text layer as good as any.
  Its answers are text snippets extracted from text layers, so it tests retrieval and answering, not structure;
  table, order and safety checks from our own gold are what tell parsers apart.
- **Bias to note:** TechManualQA snippets and the TI spec checks are anchored to PDF text layers, which favours
  text-layer extraction (pypdf scores 87.5% on independent checks while failing every table check).
- **Vendor links rot:** two of five chosen TechManualQA manuals (DeWalt, Hilti) were 404 at the dataset's URLs.
  Six TechManualQA answers have defects (parser artefacts, abridged procedures); see `notes/techmanualqa.md`.

Full tables: [`results/2026-11-10-techmanualqa-free/report.md`](results/2026-11-10-techmanualqa-free/report.md).

## Results: Claude LLM steps on manuals (11 Nov 2026, Docling, Claude Code session)

Run with `TB_LLM_PROVIDER=session`: Claude answered every LLM task inside a Claude Code session (no API calls).
Answers use `hybrid-rerank` retrieval (top 5 chunks). Three answer scores are reported:

- **Judged**: Claude grades each answer against the gold answer (correct / partial / incorrect). The headline score.
- **Strict**: every number and key word of the gold answer appears in the answer.
- **Lenient**: at least 70% of them appear.

| Document | Safety F1 (LLM) | Safety F1 (rules) | Answers judged correct | Strict | Lenient | Citations | Abstention |
|---|---|---|---|---|---|---|---|
| xylem_empa | 97.9 | 84.6 | 100.0 | 87.5 | 100.0 | 100.0 | 100.0 |
| army_tm_tqg | 100.0 | 66.7 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 |
| army_tm_scan | 100.0 | 50.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 |
| faa_ac43 | 94.7 | 50.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 |
| postgresql_backup | 100.0 | 0.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 |
| ti_lm317 | - | - | 73.3 | 80.0 | 80.0 | 73.3 | 100.0 |
| tmqa_makita_drill | - | - | 96.7 | 43.3 | 100.0 | 100.0 | 100.0 |
| tmqa_prusa_mk4 | - | - | 93.3 | 36.7 | 90.0 | 93.3 | 100.0 |
| tmqa_dji_mavic_pro | - | - | 93.3 | 20.0 | 83.3 | 90.0 | 100.0 |

- **Strict scoring understates long answers.** TechManualQA gold answers are verbatim passages, so a correct short
  answer ("2,000 lbs" for "2,000 pounds") fails the strict check. Use the judged score for those.
- **Reranking helps where retrieval was weakest.** Recall@5 on Docling output rose from 86.7 to 93.3 on both the
  Prusa and DJI manuals; the other documents were already at 100 (TI LM317 stays at 86.7).
- **TI LM317 is the weak spot.** Its questions come from the TI product page, which names parameters differently
  from the datasheet ("Vin (max)" against "input-to-output differential voltage"), and one answer picked 100 µA from
  the prose instead of 50 µA from the table.
- Claude found every warning on Xylem and the Army TM. The rule baseline averaged 50% safety F1 on those five manuals.
- **Caveats.** Docling only. The grader is the same model family as the answerer, and no human has checked its
  grades. Compared with the 10 Nov run, the reranker and the answer prompt both changed, so the gain is not
  attributable to one of them.

Full tables: [`results/2026-11-11-manuals-claude-session/report.md`](results/2026-11-11-manuals-claude-session/report.md),
[`results/2026-11-11-techmanualqa-claude-session/report.md`](results/2026-11-11-techmanualqa-claude-session/report.md).

## Results: Jev vs Claude as answer graders (10 Nov 2026, Docling, `TB_JUDGE=compare`)

Jev (`jev-1.14.0`) and Claude each graded the 141 answers from the Claude session run that were not "NOT FOUND",
on the manuals and TechManualQA documents. Jev cost about US$0.004 for all 141.

- **They agree on 140 of 141 grades** (136 correct, 2 partial, 2 incorrect). Judged accuracy per document is
  unchanged.
- **The one disagreement was flagged by Jev's own confidence.** On the Makita drill weight, the answer hedged
  between 1.5 kg and 1.8 kg. Jev said correct with confidence 0.39; Claude said partial. Any cascade threshold
  above 0.39 escalates it to Claude.

| Cascade threshold | Escalated to Claude | Cascade agrees with Claude |
|---|---|---|
| 0.8 | 5 of 141 (4%) | 141 of 141 |
| 0.9 (default) | 12 of 141 (9%) | 141 of 141 |
| 0.95 | 26 of 141 (18%) | 141 of 141 |
| 0.99 | 56 of 141 (40%) | 141 of 141 |

- **Agreement is not accuracy.** Two graders agreeing does not make them right, and almost every answer here is
  easy to grade. Use `scripts/spot_check.py` to check both against a person, and use `compare` on harder sets.
- The paper chooses the threshold with a lower-bound rule on about 100 labelled items. With this little
  disagreement any threshold from 0.4 up passes, so the default 0.9 is kept.

Full tables: [`results/2026-11-10-manuals-jev-compare/report.md`](results/2026-11-10-manuals-jev-compare/report.md),
[`results/2026-11-10-techmanualqa-jev-compare/report.md`](results/2026-11-10-techmanualqa-jev-compare/report.md).

## Workbench: inspect manuals, review answers, add labelled questions

The [Manual Handling Workbench](https://claude.ai/artifact/QbUbwe44Vzcismk1YhUnLk) is a page for working with the
manuals by hand:

- **Pages:** each bench page as printed beside the parser's text, with WARNING, CAUTION and NOTE highlighted and
  links to the test questions answered on that page.
- **Test questions:** every question with its expected answer, Claude's answer, the grade (Jev, or Claude when Jev
  was unsure), the evidence page and whether search found it.
- **Ask and label:** ask a new question. The page runs a keyword search over the parsed text and Claude answers from
  the top five extracts, using the bench's own answer prompt. Correct the answer, tick the evidence pages and save
  it as a labelled test question. Claude runs on the viewer's Claude plan, so no API key is needed.

The page's search is keyword (BM25) only, unlike the bench's reranked hybrid search, so its extracts can differ.

Rebuild the page's data after a bench run, then import saved labels into the gold set:

```bash
python scripts/export_workbench.py <out_dir>          # data.json and page images, from cached answers
python scripts/import_labels.py <labels_dir>           # saved labels -> gold/<doc>/questions.jsonl
python -m manual_app.validate_gold                     # check them and rebuild gold/questions.jsonl
```

## Knowledge graph across manuals (HVAC, 10 Nov 2026)

`corpus/hvac.yaml` adds four related manuals from three makers (two Daikin split-system manuals, a Bard PH13
package heat pump and a Rheem heat pump; 97 pages). `python -m manual_app graph --corpus hvac` builds
`graph/hvac.json` from Docling output:

- **Nodes:** manuals, models, components, refrigerants and tools (shared across manuals), plus specs, procedures,
  faults and safety notices (one manual each). Every node and link keeps its manual, page and a short quote.
- **Extraction:** rules find refrigerants and safety notices; Claude reads each page for the rest (run in a Claude
  Code session), then groups different names for the same part.
- **Size:** 1,172 nodes and 2,057 links; 68 parts, tools and refrigerants appear in more than one manual.
- **Not reviewed:** no person has checked the extraction. The workbench's graph view has accept / reject buttons.

**Does it help search?** `python -m manual_app graph-eval --corpus hvac` searches all four manuals at once, using 40
single-manual and 8 cross-manual questions drafted by Claude (answers checked verbatim against the page):

| Search | Single-manual recall@5 | Cross-manual recall@5 | Manuals read per question |
|---|---|---|---|
| Text only (hybrid + headings) | 97.5 | 100.0 | 4.0 |
| Text + graph page boost | 92.5 | 100.0 | 4.0 |
| Text + graph boost, unmatched manuals dropped | 92.5 | 100.0 | 2.7 |

- **Not yet.** With four manuals, text search already finds the right page, and the graph boost makes it slightly
  worse: common parts ("outdoor unit") occur on many pages and pull in the wrong ones, and the two Daikin manuals
  share most of their parts.
- Query time is the same (about 36 ms): narrowing only filters the ranking, it does not skip any work yet.
- The graph does cut the manuals read from 4 to 2.7 with the right manual always kept, which is where a speed-up
  would come from on a corpus of hundreds of manuals. That is untested.
- Parsing note: Docling returned reversed, letter-spaced text for most of the Bard manual's tables.

Results: [`results/2026-11-10-hvac-graph/graph_eval.json`](results/2026-11-10-hvac-graph/graph_eval.json).

## Adding your own (private) documents

1. Add an entry to a corpus manifest (`corpus/manuals.yaml`, or a new `corpus/<name>.yaml` run with `--corpus <name>`) (a `file://` URL is not supported; copy the PDF to `data/source/<id>.pdf`
   and omit `url`; keep `sha256`).
2. Annotate `gold/<id>/` per `gold/ANNOTATION.md`. For manuals, your own technicians' common questions make the best `questions.jsonl`.
3. Keep private gold and PDFs out of git (`.gitignore` already excludes `data/`; put private gold in a separate repo).

## Running the general benchmarks too

For a general-quality check alongside Manual Handling, run candidates through the official harnesses:
[OmniDocBench](https://github.com/opendatalab/OmniDocBench) (page-level end-to-end evaluation) and
[ParseBench](https://arxiv.org/abs/2604.08538) (dataset and code on Hugging Face/GitHub). Their scores answer
"is this parser good in general"; Manual Handling answers "is it good on our documents".

## Limitations

- Small corpora (six manuals ~50 pages, three TechManualQA manuals, four HVAC manuals): differences of a few points are within noise. Add your own documents.
- Safety-notice gold depends on annotator judgement about what counts as one notice; the matcher is lenient
  (fuzzy, one-to-one) but splitting conventions still matter.
- The scan is simulated; real scans (skew, stamps, handwriting, signatures) are harder.
- Gold was produced with AI assistance from page images and validated automatically; spot-check before relying
  on small differences.
