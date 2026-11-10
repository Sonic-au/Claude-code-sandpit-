# TechManualQA-700 in TenderBench

Source: Duricic et al., *A Semi-Automated Pipeline for Synthetic Generation of Grounded, Structurally-Aware QA
Datasets for Technical Manuals* (ECIR 2026; archive README cites CIKM 2025). Dataset CC BY 4.0,
[Zenodo record 17410809](https://zenodo.org/records/17410809); code: `tduricic/techmanualqa` on GitHub.

- 700 questions, 35 per manual over 20 manuals, 100 per type: Specification Lookup, Tool/Material Identification,
  Procedural Step Inquiry, Location/Definition, Conditional Logic/Causal Reasoning, Safety Information Lookup,
  Unanswerable. Questions were drafted by an LLM (Gemini 2.5 Pro), filtered, and audited by two annotators.
- Manuals are not in the archive; the dataset README lists vendor URLs. Used here (`corpus/techmanualqa.yaml`):
  Makita XFD12 drill, Prusa MK4S printer, DJI Mavic Pro. DeWalt DWE575 and Hilti TE 60 returned HTTP 404 at
  their listed URLs on 10 Nov 2026.
- Edition check: 85 of 90 answerable snippets are found on their stated page in the downloaded PDFs (fuzzy
  match); those 85 become `tmqa_snippet` rules (`vendor_rules.jsonl`), all 105 questions go to Track D.

## Known issues in the external gold (kept as published)

Six answers fail our validator against the PDF text layer:

| Question | Issue |
|---|---|
| tmk-099 | Answer snippet contains parser artefacts: "~~h~~ ave ~~b~~ een a ~~lt~~ ere ~~d~~" for "have been altered" |
| tmk-007 | Line-broken snippet not matched on the stated page |
| tdj-047, tdj-117 | Long procedures abridged with "..." or icons dropped, so not verbatim |
| tdj-091, tdj-133 | Short snippets with line breaks not matched on the stated page |

Generated benchmarks inherit their generator's parsing; spot-check before relying on per-question results.
