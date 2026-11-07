# TenderBench

An evaluation harness for choosing how to ingest **tender (RFT/RFP) and technical documents** into a bid
knowledge base. It scores document parsers, and the extraction and retrieval steps built on them, on the
things a bid team needs: verbatim clauses, tables and returnable forms, a complete compliance matrix, and
answers that cite the right page.

Tracking issue: #6. Background research: the *Bid Knowledge Base* doc (document ingestion and understanding).

## Why another benchmark

Existing benchmarks measure parsing in general, not tenders:

| Benchmark | What it gives us | Gap for tenders |
|---|---|---|
| [OmniDocBench](https://arxiv.org/abs/2412.07626) (CVPR 2025) | Page-level edit distance, TEDS, reading order | Academic/textbook/newspaper pages; no tenders, no requirements |
| [ParseBench](https://arxiv.org/abs/2604.08538) (LlamaIndex) | Rule-based tests on enterprise pages | Vendor-run; no compliance-matrix task |
| [RealDocBench](https://arxiv.org/abs/2606.07401) (Extend) | Field-level accuracy, strict per-question scoring | Regulated forms, not tenders |
| olmOCR-Bench (in [olmOCR](https://arxiv.org/abs/2502.18443)) | Cheap deterministic unit tests | Mostly academic PDFs |

TenderBench borrows one method from each and applies it to public tenders and technical papers.

## Tracks

| Track | Measures | Method (borrowed from) |
|---|---|---|
| **A. Parse fidelity** | Text similarity on transcribed pages; table TEDS and TEDS-S | Normalised edit distance and TEDS ([OmniDocBench](https://arxiv.org/abs/2412.07626), [PubTabNet](https://arxiv.org/abs/1911.10683)) |
| **B. Rule tests** | Pass rate on checks: clause verbatim, table cell, reading order, headings, form labels, numbers, running headers absent | Deterministic unit tests ([ParseBench](https://arxiv.org/abs/2604.08538), olmOCR-Bench) |
| **C. Requirement extraction** | Compliance-matrix precision / recall / F1, mandatory recall, *all mandatory found*, obligation and page accuracy | Field-level, strict scoring ([RealDocBench](https://arxiv.org/abs/2606.07401)) |
| **D. Retrieval and answers** | Evidence recall@5 and MRR for BM25, dense, hybrid and hybrid + heading context; with an LLM: answer accuracy, citation accuracy, abstention on unanswerable questions | RAG evaluation practice (RAGAS-style context recall, faithfulness) |

Every score is also reported per document, with seconds per page, cost per 1,000 pages, data residency and licence.

Tracks C and D run the **same** extractor and retriever over each parser's output, so they show how parsing
quality flows through to the compliance matrix and to answers.

## Corpus

Public documents only (`corpus/manifest.yaml`); PDFs are downloaded and checksum-verified, not committed.

| Id | Document | Pages used | Why |
|---|---|---|---|
| `newcastle_rft` | City of Newcastle (NSW) construction RFT 2026/062T | 15 of 212 | Criteria, two-column conditions of tendering, price schedules and returnable forms |
| `narembeen_rft` | Shire of Narembeen (WA) waste services RFT 2026-02 | 17 | WA local-government template, criteria tables, forms |
| `centralina_rfp` | Centralina Regional Council (NC, USA) IT managed services RFP | 18 | IT scope, tasks, attachments, environment table |
| `docling_report` | Docling Technical Report (arXiv) | 9 | Technical paper with performance table |
| `pubtabnet_paper` | PubTabNet / TEDS paper (arXiv) | 6 | Two-column paper, equations, result tables |
| `narembeen_scan` | Narembeen Part 4 forms as a simulated scan | 6 | OCR path; gold shared with the digital version, so OCR is scored against exact truth |

Gold annotations (`gold/`) were made from page images, never from a parser's output, following
[`gold/ANNOTATION.md`](gold/ANNOTATION.md), and checked with `python -m tenderbench.validate_gold`.

## Parsers

`python -m tenderbench parsers` shows which can run in your environment.

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

## Running it

```bash
python -m venv .venv && . .venv/bin/activate
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu   # CPU builds
pip install -r requirements.txt
npm install @llamaindex/liteparse @tesseract.js-data/eng      # optional: LiteParse
export LITEPARSE_BIN=$PWD/node_modules/.bin/lit               # and LITEPARSE_CONFIG for local OCR data

python -m tenderbench fetch                                   # download + build bench PDFs
python -m tenderbench run                                     # default local parsers, all tracks
python -m tenderbench run --parsers docling,vlm --docs narembeen_rft,narembeen_scan
python -m pytest -q tests
```

Results land in `results/<timestamp>/` as `report.md`, `summary.json` and `scores.json`. Parser outputs are cached
in `data/outputs/` (use `--force` to re-parse).

**LLM steps** (LLM requirement extractor, answer scoring) run only when an LLM is configured, and are never
simulated otherwise:

```bash
export TB_LLM_PROVIDER=bedrock TB_LLM_REGION=ap-southeast-2 TB_LLM_MODEL=<model id available in Sydney>   # onshore
export TB_LLM_PROVIDER=openai TB_LLM_BASE_URL=http://localhost:8000/v1 TB_LLM_MODEL=<local model>          # self-hosted
```

**Network notes.** Docling downloads models from Hugging Face; behind a proxy set `HF_HUB_DISABLE_XET=1` and allow
`huggingface.co` plus its CDN. LiteParse OCR fetches Tesseract data from GitHub unless `LITEPARSE_CONFIG` points at
a JSON file with `{"tessdataPath": "<dir with eng.traineddata>"}`.

## Adding your own (private) tenders

1. Add an entry to `corpus/manifest.yaml` (a `file://` URL is not supported; copy the PDF to `data/source/<id>.pdf`
   and omit `url`; keep `sha256`).
2. Annotate `gold/<id>/` per `gold/ANNOTATION.md`. Your past compliance matrix is a ready-made `requirements.jsonl`.
3. Keep private gold and PDFs out of git (`.gitignore` already excludes `data/`; put private gold in a separate repo).

## Running the general benchmarks too

For a general-quality check alongside TenderBench, run candidates through the official harnesses:
[OmniDocBench](https://github.com/opendatalab/OmniDocBench) (page-level end-to-end evaluation) and
[ParseBench](https://arxiv.org/abs/2604.08538) (dataset and code on Hugging Face/GitHub). Their scores answer
"is this parser good in general"; TenderBench answers "is it good on our documents".

## Limitations

- Small corpus (six documents, ~70 pages): differences of a few points are within noise. Add your own tenders.
- Requirement gold depends on annotator judgement about what counts as one requirement; the matcher is lenient
  (fuzzy, one-to-one) but splitting conventions still matter.
- The scan is simulated; real scans (skew, stamps, handwriting, signatures) are harder.
- Gold was produced with AI assistance from page images and validated automatically; spot-check before relying
  on small differences.
