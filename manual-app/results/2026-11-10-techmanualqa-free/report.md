# TenderBench results

Corpus: techmanualqa

Scores are percentages (higher is better) on the digital documents; the scan columns use the simulated scan. **Overall** is the mean of text similarity, TEDS, rule pass rate, Req F1 (rule-based extractor) and evidence recall@5 (hybrid + context). 

| Parser | Overall | Text sim | Table TEDS | TEDS-S | Rule tests | Req F1 | Mand. recall | Recall@5 | Independent checks | Scan text | Scan rules | s/page | Residency | Licence |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| liteparse | **95.6** | - | - | - | - | - | - | 95.6 | 90.6 | - | - | 0.45 | local | Apache-2.0 |
| pypdf-text | **94.4** | - | - | - | - | - | - | 94.4 | 100.0 | - | - | 0.48 | local | BSD-3-Clause |
| liteparse-md | **93.3** | - | - | - | - | - | - | 93.3 | 100.0 | - | - | 1.24 | local | Apache-2.0 |
| pymupdf4llm | **92.2** | - | - | - | - | - | - | 92.2 | 98.8 | - | - | 1.31 | local | AGPL-3.0 (commercial licence from Artifex) |
| mineru | **92.2** | - | - | - | - | - | - | 92.2 | 98.8 | - | - | 2.43 | local | AGPL-3.0 |
| docling | **91.1** | - | - | - | - | - | - | 91.1 | 97.5 | - | - | 6.91 | local | MIT (models: Apache-2.0 / CDLA) |

**Independent checks** are rules generated from vendor websites (HTML manual, product spec page) and TechManualQA-700 answer snippets, not from our own annotation (`python -m tenderbench vendor`).

No LLM was configured, so the LLM requirement extractor and answer scoring were not run (set TB_LLM_PROVIDER / TB_LLM_MODEL).

## Per document

| Document | Parser | Text sim | TEDS | Rules | Req F1 | Mand. recall | All mand. found | Recall@5 bm25 / dense / hybrid / hybrid-ctx |
|---|---|---|---|---|---|---|---|---|
| tmqa_dji_mavic_pro | docling | - | - | - | - | - | - | 83.3 / 90.0 / 83.3 / 86.7 |
| tmqa_dji_mavic_pro | liteparse | - | - | - | - | - | - | 93.3 / 80.0 / 90.0 / 93.3 |
| tmqa_dji_mavic_pro | liteparse-md | - | - | - | - | - | - | 93.3 / 80.0 / 83.3 / 90.0 |
| tmqa_dji_mavic_pro | mineru | - | - | - | - | - | - | 93.3 / 80.0 / 93.3 / 90.0 |
| tmqa_dji_mavic_pro | pymupdf4llm | - | - | - | - | - | - | 93.3 / 80.0 / 96.7 / 93.3 |
| tmqa_dji_mavic_pro | pypdf-text | - | - | - | - | - | - | 90.0 / 76.7 / 90.0 / 90.0 |
| tmqa_makita_drill | docling | - | - | - | - | - | - | 93.3 / 100.0 / 100.0 / 100.0 |
| tmqa_makita_drill | liteparse | - | - | - | - | - | - | 96.7 / 96.7 / 100.0 / 100.0 |
| tmqa_makita_drill | liteparse-md | - | - | - | - | - | - | 93.3 / 100.0 / 96.7 / 100.0 |
| tmqa_makita_drill | mineru | - | - | - | - | - | - | 96.7 / 100.0 / 100.0 / 100.0 |
| tmqa_makita_drill | pymupdf4llm | - | - | - | - | - | - | 93.3 / 100.0 / 100.0 / 100.0 |
| tmqa_makita_drill | pypdf-text | - | - | - | - | - | - | 96.7 / 100.0 / 100.0 / 100.0 |
| tmqa_prusa_mk4 | docling | - | - | - | - | - | - | 80.0 / 90.0 / 86.7 / 86.7 |
| tmqa_prusa_mk4 | liteparse | - | - | - | - | - | - | 96.7 / 90.0 / 93.3 / 93.3 |
| tmqa_prusa_mk4 | liteparse-md | - | - | - | - | - | - | 86.7 / 86.7 / 90.0 / 90.0 |
| tmqa_prusa_mk4 | mineru | - | - | - | - | - | - | 83.3 / 90.0 / 86.7 / 86.7 |
| tmqa_prusa_mk4 | pymupdf4llm | - | - | - | - | - | - | 76.7 / 93.3 / 83.3 / 83.3 |
| tmqa_prusa_mk4 | pypdf-text | - | - | - | - | - | - | 90.0 / 80.0 / 93.3 / 93.3 |

