# TenderBench results

Corpus: manuals

Scores are percentages (higher is better) on the digital documents; the scan columns use the simulated scan. **Overall** is the mean of text similarity, TEDS, rule pass rate, Safety F1 (rule-based extractor) and evidence recall@5 (hybrid + context). Safety F1 scores extraction of WARNING/CAUTION/NOTE notices; warning recall counts warnings and dangers only.

| Parser | Overall | Text sim | Table TEDS | TEDS-S | Rule tests | Safety F1 | Warning recall | Recall@5 | Independent checks | Scan text | Scan rules | s/page | Residency | Licence |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| docling | **79.9** | 91.7 | 75.1 | 76.6 | 95.2 | 40.3 | 90.9 | 97.3 | 88.7 | 92.3 | 78.6 | 4.74 | local | MIT (models: Apache-2.0 / CDLA) |
| router[docling\|docling-forceocr] | **79.9** | 91.7 | 75.1 | 76.6 | 95.2 | 40.3 | 90.9 | 97.3 | 88.7 | 93.0 | 78.6 | 2.93 | local | mix (see component parsers) |
| pymupdf4llm | **77.5** | 90.0 | 68.6 | 70.0 | 83.6 | 45.2 | 90.9 | 100.0 | 81.5 | 90.2 | 64.3 | 1.07 | local | AGPL-3.0 (commercial licence from Artifex) |
| mineru | **76.3** | 89.9 | 67.1 | 71.7 | 92.4 | 40.3 | 90.9 | 91.5 | 74.4 | 91.2 | 71.4 | 3.88 | local | AGPL-3.0 |
| liteparse-md | **69.6** | 85.1 | 43.3 | 48.1 | 78.5 | 42.3 | 77.3 | 98.7 | 74.4 | 76.9 | 21.4 | 0.81 | local | Apache-2.0 |
| pypdf-text | **54.9** | 94.0 | 0.0 | 0.0 | 65.0 | 15.7 | 35.3 | 100.0 | 83.3 | 0.0 | 14.3 | 0.02 | local | BSD-3-Clause |
| liteparse | **48.9** | 76.2 | 0.0 | 0.0 | 52.4 | 18.4 | 35.3 | 97.3 | 47.6 | 78.5 | 42.9 | 0.39 | local | Apache-2.0 |

**Independent checks** are rules generated from vendor websites (HTML manual, product spec page) and TechManualQA-700 answer snippets, not from our own annotation (`python -m tenderbench vendor`).

No LLM was configured, so the LLM requirement extractor and answer scoring were not run (set TB_LLM_PROVIDER / TB_LLM_MODEL).

## Per document

| Document | Parser | Text sim | TEDS | Rules | Safety F1 | Warning recall | All warnings found | Recall@5 bm25 / dense / hybrid / hybrid-ctx |
|---|---|---|---|---|---|---|---|---|
| army_tm_scan | docling | 92.3 | 32.8 | 78.6 | 50.0 | - | - | 100.0 / 100.0 / 100.0 / 100.0 |
| army_tm_scan | liteparse | 78.5 | 0.0 | 42.9 | 0.0 | - | - | 100.0 / 100.0 / 100.0 / 100.0 |
| army_tm_scan | liteparse-md | 76.9 | 8.5 | 21.4 | 0.0 | - | - | 100.0 / 100.0 / 100.0 / 100.0 |
| army_tm_scan | mineru | 91.2 | 18.9 | 71.4 | 40.0 | - | - | 100.0 / 100.0 / 100.0 / 100.0 |
| army_tm_scan | pymupdf4llm | 90.2 | 26.8 | 64.3 | 66.7 | - | - | 100.0 / 100.0 / 100.0 / 100.0 |
| army_tm_scan | pypdf-text | 0.0 | 0.0 | 14.3 | 0.0 | - | - | 0.0 / 0.0 / 0.0 / 0.0 |
| army_tm_scan | router[docling\|docling-forceocr] | 93.0 | 32.8 | 78.6 | 40.0 | - | - | 100.0 / 100.0 / 100.0 / 100.0 |
| army_tm_tqg | docling | 93.7 | 19.7 | 80.8 | 66.7 | 81.8 | no | 100.0 / 100.0 / 100.0 / 100.0 |
| army_tm_tqg | liteparse | 80.7 | 0.0 | 61.5 | 7.7 | 0.0 | no | 90.0 / 100.0 / 100.0 / 100.0 |
| army_tm_tqg | liteparse-md | 88.5 | 18.7 | 57.7 | 46.7 | 54.5 | no | 100.0 / 100.0 / 100.0 / 100.0 |
| army_tm_tqg | mineru | 85.8 | 42.6 | 80.8 | 66.7 | 81.8 | no | 90.0 / 100.0 / 90.0 / 90.0 |
| army_tm_tqg | pymupdf4llm | 91.8 | 19.7 | 73.1 | 64.9 | 81.8 | no | 100.0 / 100.0 / 100.0 / 100.0 |
| army_tm_tqg | pypdf-text | 94.1 | 0.0 | 65.4 | 0.0 | 0.0 | no | 90.0 / 100.0 / 100.0 / 100.0 |
| army_tm_tqg | router[docling\|docling-forceocr] | 93.7 | 19.7 | 80.8 | 66.7 | 81.8 | no | 100.0 / 100.0 / 100.0 / 100.0 |
| faa_ac43 | docling | 94.4 | 95.4 | 95.5 | 50.0 | - | - | 100.0 / 100.0 / 100.0 / 100.0 |
| faa_ac43 | liteparse | 41.0 | 0.0 | 4.5 | 13.3 | - | - | 87.5 / 100.0 / 100.0 / 100.0 |
| faa_ac43 | liteparse-md | 96.2 | 70.3 | 81.8 | 76.2 | - | - | 87.5 / 100.0 / 100.0 / 100.0 |
| faa_ac43 | mineru | 94.2 | 42.9 | 95.5 | 45.2 | - | - | 87.5 / 100.0 / 100.0 / 87.5 |
| faa_ac43 | pymupdf4llm | 94.4 | 89.7 | 68.2 | 82.4 | - | - | 87.5 / 100.0 / 100.0 / 100.0 |
| faa_ac43 | pypdf-text | 98.2 | 0.0 | 63.6 | 9.1 | - | - | 87.5 / 100.0 / 100.0 / 100.0 |
| faa_ac43 | router[docling\|docling-forceocr] | 94.4 | 95.4 | 95.5 | 50.0 | - | - | 100.0 / 100.0 / 100.0 / 100.0 |
| postgresql_backup | docling | 100.0 | - | 100.0 | 0.0 | - | - | 100.0 / 100.0 / 100.0 / 100.0 |
| postgresql_backup | liteparse | 99.6 | - | 81.8 | 0.0 | - | - | 100.0 / 100.0 / 100.0 / 100.0 |
| postgresql_backup | liteparse-md | 99.7 | - | 90.9 | 0.0 | - | - | 100.0 / 100.0 / 100.0 / 100.0 |
| postgresql_backup | mineru | 100.0 | - | 100.0 | 0.0 | - | - | 100.0 / 100.0 / 100.0 / 100.0 |
| postgresql_backup | pymupdf4llm | 99.4 | - | 90.9 | 0.0 | - | - | 100.0 / 100.0 / 100.0 / 100.0 |
| postgresql_backup | pypdf-text | 99.6 | - | 81.8 | 0.0 | - | - | 100.0 / 100.0 / 100.0 / 100.0 |
| postgresql_backup | router[docling\|docling-forceocr] | 100.0 | - | 100.0 | 0.0 | - | - | 100.0 / 100.0 / 100.0 / 100.0 |
| ti_lm317 | docling | 73.1 | 89.1 | 100.0 | 0.0 | - | - | 80.0 / 80.0 / 73.3 / 86.7 |
| ti_lm317 | liteparse | 71.6 | 0.0 | 52.4 | 0.0 | - | - | 86.7 / 80.0 / 93.3 / 86.7 |
| ti_lm317 | liteparse-md | 65.9 | 46.6 | 85.7 | 0.0 | - | - | 80.0 / 80.0 / 80.0 / 93.3 |
| ti_lm317 | mineru | 71.8 | 83.2 | 95.2 | 0.0 | - | - | 73.3 / 86.7 / 80.0 / 80.0 |
| ti_lm317 | pymupdf4llm | 72.8 | 76.3 | 95.2 | 0.0 | - | - | 86.7 / 93.3 / 86.7 / 100.0 |
| ti_lm317 | pypdf-text | 83.0 | 0.0 | 52.4 | 0.0 | - | - | 86.7 / 80.0 / 80.0 / 100.0 |
| ti_lm317 | router[docling\|docling-forceocr] | 73.1 | 89.1 | 100.0 | 0.0 | - | - | 80.0 / 80.0 / 73.3 / 86.7 |
| xylem_empa | docling | 97.4 | 96.2 | 100.0 | 84.6 | 100.0 | yes | 100.0 / 100.0 / 100.0 / 100.0 |
| xylem_empa | liteparse | 88.0 | 0.0 | 61.9 | 70.8 | 70.6 | no | 100.0 / 100.0 / 100.0 / 100.0 |
| xylem_empa | liteparse-md | 75.1 | 37.7 | 76.2 | 88.5 | 100.0 | yes | 100.0 / 100.0 / 100.0 / 100.0 |
| xylem_empa | mineru | 97.9 | 99.8 | 90.5 | 89.8 | 100.0 | yes | 100.0 / 100.0 / 100.0 / 100.0 |
| xylem_empa | pymupdf4llm | 91.4 | 88.6 | 90.5 | 78.6 | 100.0 | yes | 100.0 / 100.0 / 100.0 / 100.0 |
| xylem_empa | pypdf-text | 94.8 | 0.0 | 61.9 | 69.4 | 70.6 | no | 100.0 / 100.0 / 100.0 / 100.0 |
| xylem_empa | router[docling\|docling-forceocr] | 97.4 | 96.2 | 100.0 | 84.6 | 100.0 | yes | 100.0 / 100.0 / 100.0 / 100.0 |

## Rule tests by category

| Parser | header | heading | order | part_number | safety | spec | step_order | table |
|---|---|---|---|---|---|---|---|---|
| docling | 93.3 | 100.0 | 100.0 | 100.0 | 100.0 | 92.0 | 100.0 | 81.2 |
| router[docling\|docling-forceocr] | 93.3 | 100.0 | 100.0 | 100.0 | 100.0 | 92.0 | 100.0 | 81.2 |
| pymupdf4llm | 10.0 | 90.0 | 100.0 | 100.0 | 96.0 | 92.0 | 100.0 | 68.8 |
| mineru | 100.0 | 90.0 | 100.0 | 100.0 | 100.0 | 78.7 | 100.0 | 81.2 |
| liteparse-md | 30.0 | 60.0 | 100.0 | 100.0 | 96.7 | 92.0 | 100.0 | 43.8 |
| pypdf-text | 0.0 | 0.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 0.0 |
| liteparse | 0.0 | 0.0 | 100.0 | 80.0 | 84.0 | 76.0 | 80.0 | 0.0 |

