# Manual Handling: technical-manual Q&A

`manual-app` (formerly TenderBench). Run it with `python -m manual_app`.

An evaluation harness for choosing how to ingest **technical manuals** into a knowledge base that answers
**technician questions** with page citations. It scores document parsers, and the extraction and retrieval steps
built on them, on what a technician relies on: procedure steps in order, warnings kept with their step, spec and
torque tables, values with their units, exact part numbers and commands, and answers that cite the right page.

It started as a tender (RFT/RFP) bench for bid responses; that corpus is kept and runs with `--corpus tenders`.

Tracking issues: #6 (harness), #7 (technical manuals). Background research: the *Bid Knowledge Base* doc.

## Why another benchmark

Existing benchmarks measure parsing in general, not tenders:

| Benchmark | What it gives us | Gap for tenders |
|---|---|---|
| [OmniDocBench](https://arxiv.org/abs/2412.07626) (CVPR 2025) | Page-level edit distance, TEDS, reading order | Academic/textbook/newspaper pages; no tenders, no requirements |
| [ParseBench](https://arxiv.org/abs/2604.08538) (LlamaIndex) | Rule-based tests on enterprise pages | Vendor-run; no compliance-matrix task |
| [RealDocBench](https://arxiv.org/abs/2606.07401) (Extend) | Field-level accuracy, strict per-question scoring | Regulated forms, not tenders |
| olmOCR-Bench (in [olmOCR](https://arxiv.org/abs/2502.18443)) | Cheap deterministic unit tests | Mostly academic PDFs |

Manual Handling borrows one method from each and applies it to public tenders and technical papers.

## Tracks

| Track | Measures | Method (borrowed from) |
|---|---|---|
| **A. Parse fidelity** | Text similarity on transcribed pages; table TEDS and TEDS-S | Normalised edit distance and TEDS ([OmniDocBench](https://arxiv.org/abs/2412.07626), [PubTabNet](https://arxiv.org/abs/1911.10683)) |
| **B. Rule tests** | Pass rate on checks: clause verbatim, table cell, reading order, headings, form labels, numbers, running headers absent | Deterministic unit tests ([ParseBench](https://arxiv.org/abs/2604.08538), olmOCR-Bench) |
| **C. Extraction** | Manuals: every WARNING/CAUTION/NOTE notice, warning recall, *all warnings found*. Tenders: compliance-matrix F1, mandatory recall, *all mandatory found* | Field-level, strict scoring ([RealDocBench](https://arxiv.org/abs/2606.07401)) |
| **D. Retrieval and answers** | Evidence recall@5 and MRR for BM25, dense, hybrid, hybrid + heading context and hybrid + reranker; with an LLM: answer accuracy (LLM-judged, strict, lenient), citation accuracy, abstention on unanswerable questions | RAG evaluation practice (RAGAS-style context recall, faithfulness) |

Every score is also reported per document, with seconds per page, cost per 1,000 pages, data residency and licence.

Tracks C and D run the **same** extractor and retriever over each parser's output, so they show how parsing
quality flows through to the compliance matrix and to answers.

## Corpus

Public documents only; PDFs are downloaded and checksum-verified, not committed. Two manifests:

**`corpus/manuals.yaml` (default)**

| Id | Document | Kind | Pages used | Why |
|---|---|---|---|---|
| `xylem_empa` | Xylem e-MPA/MPR/MPD pump instruction manual IM309 | Equipment O&M | 11 | Safety notices, coupling torque table, commissioning steps, troubleshooting tables |
| `postgresql_backup` | PostgreSQL 17 manual, ch. 25 Backup and Restore | Software | 7 of 3,100 | Commands and code blocks, WAL archiving, recovery procedure |
| `ti_lm317` | TI LM317 regulator datasheet | Specification | 9 | Min/typ/max spec tables with conditions and footnotes, pin functions |
| `faa_ac43` | FAA AC 43.13-1B ch. 7 (hardware, safetying, cables) | Aviation | 8 of 646 | Large grouped-header torque table, CAUTION boxes, AN/MS part numbers |
| `army_tm_tqg` | US Army TM 9-6115-639-13 (3 kW generator) | Defence | 11 of 304 | Warning summary, PMCS and troubleshooting tables, start-up procedures |
| `army_tm_scan` | Army TM pages as a simulated scan | Defence | 4 | OCR path, scored against the digital version's gold |

**`corpus/tenders.yaml`** (`--corpus tenders`)

| Id | Document | Pages used | Why |
|---|---|---|---|
| `newcastle_rft` | City of Newcastle (NSW) construction RFT 2026/062T | 15 of 212 | Criteria, two-column conditions of tendering, price schedules and returnable forms |
| `narembeen_rft` | Shire of Narembeen (WA) waste services RFT 2026-02 | 17 | WA local-government template, criteria tables, forms |
| `centralina_rfp` | Centralina Regional Council (NC, USA) IT managed services RFP | 18 | IT scope, tasks, attachments, environment table |
| `docling_report` | Docling Technical Report (arXiv) | 9 | Technical paper with performance table |
| `pubtabnet_paper` | PubTabNet / TEDS paper (arXiv) | 6 | Two-column paper, equations, result tables |
| `narembeen_scan` | Narembeen Part 4 forms as a simulated scan | 6 | OCR path; gold shared with the digital version, so OCR is scored against exact truth |

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
| MinerU | AGPL-3.0 | Best on tenders and simpler tables; AGPL obligations if offered as a service |
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

**LLM steps** run on **Claude** by default: requirement extraction (tenders), safety-notice extraction (manuals)
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

The report adds an LLM table (extraction F1, critical recall, all-critical-found, answer accuracy (judged, strict and
lenient), citation accuracy, abstention) and a usage line with token counts and estimated cost (`llm_usage.json`).

**Network notes.** Docling downloads models from Hugging Face; behind a proxy set `HF_HUB_DISABLE_XET=1` and allow
`huggingface.co` plus its CDN. LiteParse OCR fetches Tesseract data from GitHub unless `LITEPARSE_CONFIG` points at
a JSON file with `{"tessdataPath": "<dir with eng.traineddata>"}`.

## Results: technical manuals (9 Nov 2026, local parsers, CPU only)

Full tables: [`results/2026-11-09-manuals/report.md`](results/2026-11-09-manuals/report.md).

| Parser | Overall | Table TEDS | Rule tests | Warning recall | Scan text | s/page | Licence |
|---|---|---|---|---|---|---|---|
| Docling | **80.5** | 75.1 | 95.2 | 90.9 | 92.3 | 4.7 | MIT |
| PyMuPDF4LLM | 77.5 | 68.6 | 83.6 | 90.9 | 90.2 | 1.1 | AGPL-3.0 |
| MinerU | 77.1 | 67.1 | 92.4 | 90.9 | 91.2 | 3.9 | AGPL-3.0 |
| LiteParse (Markdown) | 69.8 | 43.3 | 78.5 | 77.3 | 76.9 | 0.8 | Apache-2.0 |
| pypdf text layer | 54.9 | 0.0 | 65.0 | 35.3 | 0.0 | 0.02 | BSD |

- **Docling leads on manuals**, the reverse of the tender result. It kept the FAA's large grouped-header torque
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

Full tables: [`results/2026-11-10-techmanualqa/report.md`](results/2026-11-10-techmanualqa/report.md).

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
The 10 Nov run (before the judge and reranker) is in `results/2026-11-10-*-claude-session/`.

## Results: tenders (7 Nov 2026, re-scored 9 Nov)

Full tables: [`results/2026-11-07-local/report.md`](results/2026-11-07-local/report.md).

| Parser | Overall | Table TEDS | Rule tests | Scan text | s/page | Licence |
|---|---|---|---|---|---|---|
| MinerU | **85.2** | 80.2 | 95.5 | 99.2 | 2.8 | AGPL-3.0 |
| Docling | 80.6 | 62.4 | 90.7 | 95.8 | 4.7 | MIT |
| PyMuPDF4LLM | 78.2 | 53.7 | 90.6 | 84.9 | 1.7 | AGPL-3.0 |
| LiteParse (Markdown) | 71.7 | 43.4 | 71.1 | 80.3 | 1.1 | Apache-2.0 |
| pypdf text layer | 60.7 | 0.0 | 57.4 | 0.0 | 0.04 | BSD |

- **Tables decide the ranking.** Text similarity is 94-98% for every layout-aware parser; table structure ranges from
  43% to 80% TEDS. MinerU kept merged cells best; Docling merged rows on the Docling paper's own multi-row table (35%).
- **Scans are handled well by MinerU and Docling** (95-99% text similarity on the simulated scan); LiteParse's
  Tesseract OCR lost most of the form structure (38% of rule tests).
- **Requirement extraction is limited by the extractor, not the parser.** The rule-based extractor finds 45-48% of
  mandatory requirements whichever parser feeds it, and no parser/extractor pair found *all* mandatory requirements
  in any tender. The LLM extractor (not run here: no LLM configured) is the step to test next.
- **Retrieval is near ceiling** on this small question set (92-95% recall@5 for every parser), so it does not separate
  parsers yet; it needs harder, cross-document questions.
- The router (Docling for digital pages, full-page OCR for image-only pages) matched plain Docling, because Docling
  already OCRs image pages. Evidence so far favours MinerU as the primary parser if its AGPL licence is acceptable,
  with Docling as the MIT-licensed alternative.

## Adding your own (private) documents

1. Add an entry to a corpus manifest (`corpus/manuals.yaml`, or a new `corpus/<name>.yaml` run with `--corpus <name>`) (a `file://` URL is not supported; copy the PDF to `data/source/<id>.pdf`
   and omit `url`; keep `sha256`).
2. Annotate `gold/<id>/` per `gold/ANNOTATION.md`. For manuals, your own technicians' common questions make the best `questions.jsonl`; for tenders, a past compliance matrix is a ready-made `requirements.jsonl`.
3. Keep private gold and PDFs out of git (`.gitignore` already excludes `data/`; put private gold in a separate repo).

## Running the general benchmarks too

For a general-quality check alongside Manual Handling, run candidates through the official harnesses:
[OmniDocBench](https://github.com/opendatalab/OmniDocBench) (page-level end-to-end evaluation) and
[ParseBench](https://arxiv.org/abs/2604.08538) (dataset and code on Hugging Face/GitHub). Their scores answer
"is this parser good in general"; Manual Handling answers "is it good on our documents".

## Limitations

- Small corpora (six manuals ~50 pages; six tender documents ~70 pages): differences of a few points are within noise. Add your own documents.
- Requirement gold depends on annotator judgement about what counts as one requirement; the matcher is lenient
  (fuzzy, one-to-one) but splitting conventions still matter.
- The scan is simulated; real scans (skew, stamps, handwriting, signatures) are harder.
- Gold was produced with AI assistance from page images and validated automatically; spot-check before relying
  on small differences.
