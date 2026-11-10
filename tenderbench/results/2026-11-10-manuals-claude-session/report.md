# TenderBench results

Corpus: manuals

Scores are percentages (higher is better) on the digital documents; the scan columns use the simulated scan. **Overall** is the mean of text similarity, TEDS, rule pass rate, Safety F1 (rule-based extractor) and evidence recall@5 (hybrid + context). Safety F1 scores extraction of WARNING/CAUTION/NOTE notices; warning recall counts warnings and dangers only.

| Parser | Overall | Text sim | Table TEDS | TEDS-S | Rule tests | Safety F1 | Warning recall | Recall@5 | Independent checks | Scan text | Scan rules | s/page | Residency | Licence |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| docling | **79.9** | 91.7 | 75.1 | 76.6 | 95.2 | 40.3 | 90.9 | 97.3 | 92.9 | 92.3 | 78.6 | 4.74 | local | MIT (models: Apache-2.0 / CDLA) |

LLM steps used `session:claude-code-session (effort session)`.
LLM usage: 113 calls, 0 input and 0 output tokens, 0 declined; data residency: offshore (Claude Code session).

| Document | Parser | LLM extraction F1 | LLM critical recall | All critical found | Answer accuracy | Lenient accuracy | Citation accuracy | Abstention accuracy |
|---|---|---|---|---|---|---|---|---|
| army_tm_scan | docling | 100.0 | - | - | 100.0 | 100.0 | 100.0 | 100.0 |
| army_tm_tqg | docling | 100.0 | 100.0 | yes | 90.0 | 90.0 | 90.0 | 100.0 |
| faa_ac43 | docling | 94.7 | - | - | 87.5 | 87.5 | 100.0 | 100.0 |
| postgresql_backup | docling | 100.0 | - | - | 100.0 | 100.0 | 100.0 | 100.0 |
| ti_lm317 | docling | 0.0 | - | - | 66.7 | 66.7 | 66.7 | 100.0 |
| xylem_empa | docling | 97.9 | 100.0 | yes | 87.5 | 100.0 | 100.0 | 100.0 |

## Per document

| Document | Parser | Text sim | TEDS | Rules | Safety F1 | Warning recall | All warnings found | Recall@5 bm25 / dense / hybrid / hybrid-ctx |
|---|---|---|---|---|---|---|---|---|
| army_tm_scan | docling | 92.3 | 32.8 | 78.6 | 50.0 | - | - | 100.0 / 100.0 / 100.0 / 100.0 |
| army_tm_tqg | docling | 93.7 | 19.7 | 80.8 | 66.7 | 81.8 | no | 100.0 / 100.0 / 100.0 / 100.0 |
| faa_ac43 | docling | 94.4 | 95.4 | 95.5 | 50.0 | - | - | 100.0 / 100.0 / 100.0 / 100.0 |
| postgresql_backup | docling | 100.0 | - | 100.0 | 0.0 | - | - | 100.0 / 100.0 / 100.0 / 100.0 |
| ti_lm317 | docling | 73.1 | 89.1 | 100.0 | 0.0 | - | - | 80.0 / 80.0 / 73.3 / 86.7 |
| xylem_empa | docling | 97.4 | 96.2 | 100.0 | 84.6 | 100.0 | yes | 100.0 / 100.0 / 100.0 / 100.0 |

## Rule tests by category

| Parser | header | heading | order | part_number | safety | spec | step_order | table |
|---|---|---|---|---|---|---|---|---|
| docling | 93.3 | 100.0 | 100.0 | 100.0 | 100.0 | 92.0 | 100.0 | 81.2 |

