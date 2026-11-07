# TenderBench results

Scores are percentages (higher is better) on the digital documents; the scan columns use the simulated scan. **Overall** is the mean of text similarity, TEDS, rule pass rate, requirement F1 (rule-based extractor) and evidence recall@5 (hybrid + context).

| Parser | Overall | Text sim | Table TEDS | TEDS-S | Rule tests | Req F1 | Mand. recall | Recall@5 | Scan text | Scan rules | s/page | Residency | Licence |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| mineru | **85.2** | 97.5 | 80.2 | 89.2 | 95.5 | 57.9 | 47.3 | 95.0 | 99.2 | 100.0 | 2.79 | local | AGPL-3.0 |
| docling | **80.6** | 94.6 | 62.4 | 73.5 | 90.7 | 60.3 | 48.3 | 95.0 | 95.8 | 95.2 | 4.70 | local | MIT (models: Apache-2.0 / CDLA) |
| router[docling\|docling-forceocr] | **80.6** | 94.6 | 62.4 | 73.5 | 90.7 | 60.3 | 48.3 | 95.0 | 95.2 | 95.2 | 3.07 | local | mix (see component parsers) |
| pymupdf4llm | **78.2** | 94.9 | 53.7 | 66.3 | 90.6 | 56.8 | 46.0 | 95.0 | 84.9 | 95.2 | 1.70 | local | AGPL-3.0 (commercial licence from Artifex) |
| liteparse-md | **71.7** | 93.9 | 43.4 | 49.2 | 71.1 | 55.3 | 43.6 | 95.0 | 80.3 | 38.1 | 1.06 | local | Apache-2.0 |
| pypdf-text | **60.7** | 95.9 | 0.0 | 0.0 | 57.4 | 57.5 | 45.2 | 92.5 | 0.0 | 9.5 | 0.04 | local | BSD-3-Clause |
| liteparse | **53.3** | 77.5 | 0.0 | 0.0 | 42.5 | 54.3 | 40.7 | 92.5 | 87.4 | 42.9 | 0.41 | local | Apache-2.0 |

No LLM was configured, so the LLM requirement extractor and answer scoring were not run (set TB_LLM_PROVIDER / TB_LLM_MODEL).

## Per document

| Document | Parser | Text sim | TEDS | Rules | Req F1 | Mand. recall | All mand. found | Recall@5 bm25 / dense / hybrid / hybrid-ctx |
|---|---|---|---|---|---|---|---|---|
| centralina_rfp | docling | 94.2 | 61.2 | 100.0 | 56.3 | 35.6 | no | 100.0 / 87.5 / 87.5 / 100.0 |
| centralina_rfp | liteparse | 92.0 | 0.0 | 56.0 | 54.5 | 33.9 | no | 100.0 / 87.5 / 100.0 / 100.0 |
| centralina_rfp | liteparse-md | 99.0 | 67.2 | 84.0 | 52.6 | 32.2 | no | 100.0 / 87.5 / 87.5 / 100.0 |
| centralina_rfp | mineru | 97.1 | 87.3 | 96.0 | 55.9 | 35.6 | no | 100.0 / 87.5 / 87.5 / 100.0 |
| centralina_rfp | pymupdf4llm | 97.1 | 69.4 | 84.0 | 55.4 | 33.9 | no | 100.0 / 87.5 / 87.5 / 100.0 |
| centralina_rfp | pypdf-text | 98.9 | 0.0 | 56.0 | 54.5 | 33.9 | no | 87.5 / 87.5 / 100.0 / 100.0 |
| centralina_rfp | router[docling\|docling-forceocr] | 94.2 | 61.2 | 100.0 | 56.3 | 35.6 | no | 100.0 / 87.5 / 87.5 / 100.0 |
| docling_report | docling | 93.7 | 35.2 | 100.0 | - | - | - | 100.0 / 100.0 / 100.0 / 100.0 |
| docling_report | liteparse | 98.2 | 0.0 | 50.0 | - | - | - | 100.0 / 100.0 / 100.0 / 100.0 |
| docling_report | liteparse-md | 98.5 | 27.9 | 71.4 | - | - | - | 100.0 / 100.0 / 100.0 / 100.0 |
| docling_report | mineru | 98.3 | 22.9 | 85.7 | - | - | - | 100.0 / 100.0 / 100.0 / 100.0 |
| docling_report | pymupdf4llm | 98.5 | 21.3 | 100.0 | - | - | - | 100.0 / 100.0 / 100.0 / 100.0 |
| docling_report | pypdf-text | 98.8 | 0.0 | 57.1 | - | - | - | 100.0 / 100.0 / 100.0 / 100.0 |
| docling_report | router[docling\|docling-forceocr] | 93.7 | 35.2 | 100.0 | - | - | - | 100.0 / 100.0 / 100.0 / 100.0 |
| narembeen_rft | docling | 98.9 | 88.6 | 84.0 | 57.8 | 50.7 | no | 87.5 / 100.0 / 100.0 / 87.5 |
| narembeen_rft | liteparse | 89.3 | 0.0 | 52.0 | 58.1 | 46.7 | no | 87.5 / 75.0 / 87.5 / 62.5 |
| narembeen_rft | liteparse-md | 85.2 | 42.8 | 60.0 | 47.8 | 41.3 | no | 87.5 / 100.0 / 100.0 / 87.5 |
| narembeen_rft | mineru | 99.8 | 99.6 | 100.0 | 50.0 | 45.3 | no | 87.5 / 100.0 / 100.0 / 87.5 |
| narembeen_rft | pymupdf4llm | 90.6 | 63.7 | 84.0 | 48.0 | 46.7 | no | 87.5 / 100.0 / 100.0 / 87.5 |
| narembeen_rft | pypdf-text | 91.5 | 0.0 | 60.0 | 56.1 | 48.0 | no | 87.5 / 75.0 / 100.0 / 87.5 |
| narembeen_rft | router[docling\|docling-forceocr] | 98.9 | 88.6 | 84.0 | 57.8 | 50.7 | no | 87.5 / 100.0 / 100.0 / 87.5 |
| narembeen_scan | docling | 95.8 | 88.6 | 95.2 | 53.8 | 52.4 | no | 100.0 / 100.0 / 100.0 / 100.0 |
| narembeen_scan | liteparse | 87.4 | 0.0 | 42.9 | 50.5 | 47.6 | no | 100.0 / 100.0 / 100.0 / 100.0 |
| narembeen_scan | liteparse-md | 80.3 | 10.0 | 38.1 | 48.3 | 47.6 | no | 100.0 / 100.0 / 100.0 / 100.0 |
| narembeen_scan | mineru | 99.2 | 70.5 | 100.0 | 36.9 | 47.6 | no | 100.0 / 100.0 / 100.0 / 100.0 |
| narembeen_scan | pymupdf4llm | 84.9 | 42.6 | 95.2 | 50.6 | 57.1 | no | 100.0 / 100.0 / 100.0 / 100.0 |
| narembeen_scan | pypdf-text | 0.0 | 0.0 | 9.5 | 0.0 | 0.0 | no | 0.0 / 0.0 / 0.0 / 0.0 |
| narembeen_scan | router[docling\|docling-forceocr] | 95.2 | 88.7 | 95.2 | 55.7 | 47.6 | no | 100.0 / 100.0 / 100.0 / 100.0 |
| newcastle_rft | docling | 95.5 | 55.4 | 84.0 | 66.7 | 58.5 | no | 100.0 / 100.0 / 100.0 / 87.5 |
| newcastle_rft | liteparse | 78.4 | 0.0 | 40.0 | 50.2 | 41.5 | no | 100.0 / 100.0 / 100.0 / 100.0 |
| newcastle_rft | liteparse-md | 93.8 | 20.8 | 76.0 | 65.5 | 57.3 | no | 100.0 / 100.0 / 100.0 / 87.5 |
| newcastle_rft | mineru | 97.2 | 95.8 | 96.0 | 67.9 | 61.0 | no | 100.0 / 100.0 / 100.0 / 87.5 |
| newcastle_rft | pymupdf4llm | 95.9 | 49.5 | 92.0 | 67.0 | 57.3 | no | 100.0 / 75.0 / 100.0 / 87.5 |
| newcastle_rft | pypdf-text | 96.5 | 0.0 | 64.0 | 61.8 | 53.7 | no | 100.0 / 75.0 / 87.5 / 75.0 |
| newcastle_rft | router[docling\|docling-forceocr] | 95.5 | 55.4 | 84.0 | 66.7 | 58.5 | no | 100.0 / 100.0 / 100.0 / 87.5 |
| pubtabnet_paper | docling | 90.7 | 71.7 | 85.7 | - | - | - | 100.0 / 100.0 / 100.0 / 100.0 |
| pubtabnet_paper | liteparse | 29.5 | 0.0 | 14.3 | - | - | - | 100.0 / 80.0 / 100.0 / 100.0 |
| pubtabnet_paper | liteparse-md | 92.7 | 58.4 | 64.3 | - | - | - | 100.0 / 100.0 / 100.0 / 100.0 |
| pubtabnet_paper | mineru | 95.2 | 95.4 | 100.0 | - | - | - | 100.0 / 100.0 / 100.0 / 100.0 |
| pubtabnet_paper | pymupdf4llm | 92.5 | 64.4 | 92.9 | - | - | - | 100.0 / 80.0 / 100.0 / 100.0 |
| pubtabnet_paper | pypdf-text | 93.7 | 0.0 | 50.0 | - | - | - | 100.0 / 100.0 / 100.0 / 100.0 |
| pubtabnet_paper | router[docling\|docling-forceocr] | 90.7 | 71.7 | 85.7 | - | - | - | 100.0 / 100.0 / 100.0 / 100.0 |

## Rule tests by category

| Parser | clause | form | header | heading | number | order | table |
|---|---|---|---|---|---|---|---|
| mineru | 100.0 | 100.0 | 100.0 | 88.3 | 100.0 | 90.0 | 93.3 |
| docling | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 93.3 | 58.0 |
| router[docling\|docling-forceocr] | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 93.3 | 58.0 |
| pymupdf4llm | 100.0 | 100.0 | 16.7 | 100.0 | 100.0 | 100.0 | 75.0 |
| liteparse-md | 93.3 | 88.9 | 0.0 | 68.3 | 100.0 | 83.3 | 34.0 |
| pypdf-text | 100.0 | 100.0 | 0.0 | 0.0 | 100.0 | 100.0 | 0.0 |
| liteparse | 68.0 | 100.0 | 0.0 | 0.0 | 89.3 | 43.3 | 0.0 |

