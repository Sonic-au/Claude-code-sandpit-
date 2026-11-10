# TenderBench results

Corpus: techmanualqa

Scores are percentages (higher is better) on the digital documents; the scan columns use the simulated scan. **Overall** is the mean of text similarity, TEDS, rule pass rate, Req F1 (rule-based extractor) and evidence recall@5 (hybrid + context). 

| Parser | Overall | Text sim | Table TEDS | TEDS-S | Rule tests | Req F1 | Mand. recall | Recall@5 | Independent checks | Scan text | Scan rules | s/page | Residency | Licence |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| docling | **91.1** | - | - | - | - | - | - | 91.1 | 97.5 | - | - | 6.91 | local | MIT (models: Apache-2.0 / CDLA) |

LLM steps used `session:claude-code-session (effort session)`.
LLM usage: 105 calls, 0 input and 0 output tokens, 0 declined; data residency: offshore (Claude Code session).

| Document | Parser | LLM extraction F1 | LLM critical recall | All critical found | Answer accuracy | Lenient accuracy | Citation accuracy | Abstention accuracy |
|---|---|---|---|---|---|---|---|---|
| tmqa_dji_mavic_pro | docling | - | - | - | 10.0 | 60.0 | 86.7 | 100.0 |
| tmqa_makita_drill | docling | - | - | - | 40.0 | 76.7 | 100.0 | 100.0 |
| tmqa_prusa_mk4 | docling | - | - | - | 40.0 | 73.3 | 86.7 | 100.0 |

## Per document

| Document | Parser | Text sim | TEDS | Rules | Req F1 | Mand. recall | All mand. found | Recall@5 bm25 / dense / hybrid / hybrid-ctx |
|---|---|---|---|---|---|---|---|---|
| tmqa_dji_mavic_pro | docling | - | - | - | - | - | - | 83.3 / 90.0 / 83.3 / 86.7 |
| tmqa_makita_drill | docling | - | - | - | - | - | - | 93.3 / 100.0 / 100.0 / 100.0 |
| tmqa_prusa_mk4 | docling | - | - | - | - | - | - | 80.0 / 90.0 / 86.7 / 86.7 |

