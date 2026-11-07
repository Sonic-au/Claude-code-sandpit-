# TenderBench annotation guide

Gold data is the bench. Annotate from the **page image** (what a person sees), never from a
parser's output: copying a parser's text would bias the bench towards that parser. The PDF text
layer may be used to copy exact wording, but check reading order and table structure against the
image.

All page numbers are **original document page numbers** (see `corpus/manifest.yaml`).

Files per document, under `gold/<doc_id>/`:

| File | Track | What it holds |
|---|---|---|
| `pages/pNNN.md` | A | Full transcription of selected pages |
| `tables.jsonl` | A | Selected tables as HTML |
| `rules.jsonl` | B | Pass/fail checks |
| `requirements.jsonl` | C | Compliance matrix (tenders only) |
| `questions.jsonl` | D | Questions with evidence pages (merged into `gold/questions.jsonl`) |

## Track A: page transcriptions (`pages/pNNN.md`)

Transcribe the whole page body as Markdown, in the order a person reads it.

- Headings as `#`/`##`/`###` (by visual level). Keep clause numbers with the heading text (`## 4.4 QUALITATIVE CRITERIA`).
- Lists: one item per line starting `- `, keep the printed enumerator as text (`- (a) Provide details...`).
- Tables as HTML `<table>` with `<th>` for header cells and `colspan`/`rowspan` for merged cells.
- Two-column layouts: whole left column, then whole right column.
- Leave out: running headers and footers, page numbers, watermarks, images, checkbox glyphs (☐), dot leaders and
  blank fill-in lines. Keep form labels ("ABN", "Telephone No:") and figure/table captions.
- Equations: write as plain text the way they read (e.g. `TEDS(Ta, Tb) = 1 - EditDist(Ta, Tb) / max(|Ta|, |Tb|)`).
- Keep spelling exactly as printed, including errors.

## Track A: tables (`tables.jsonl`)

One JSON object per line: `{"id": "nar-t1", "page": 16, "caption": "4.4 Qualitative criteria", "html": "<table>...</table>"}`.
Same table conventions as above. Cell text exactly as printed; omit checkbox glyphs. A table that continues across pages
is annotated per page.

## Track B: rules (`rules.jsonl`)

One check per line, each verified true against the page image. Types:

```json
{"id": "nar-b01", "type": "present", "page": 16, "category": "clause", "text": "Respondents are to address each issue outlined within a qualitative criterion"}
{"id": "nar-b02", "type": "table_value", "page": 16, "category": "table", "row": "(B) Price", "col": "Weighting", "value": "50%"}
{"id": "nar-b03", "type": "order", "page": 3, "category": "order", "before": "1.1 INTERPRETATION", "after": "1.2 DEFINITIONS"}
{"id": "nar-b04", "type": "heading", "page": 16, "category": "heading", "text": "4.4 QUALITATIVE CRITERIA"}
{"id": "nar-b05", "type": "absent", "page": 16, "category": "header", "text": "PART 4 COMPLETE AND RETURN THIS PART"}
```

Categories: `clause` (a requirement sentence survives verbatim), `number` (dates, amounts, percentages, clause
references), `table` (cell lookups), `form` (returnable form labels and order), `order` (reading order across
columns, sections and table cells), `heading` (section headings marked up as headings), `header` (running headers,
footers and page numbers that should NOT pollute the text; use only for text repeated on many pages).

`present` text: 6-30 words copied exactly; avoid text that spans a table cell boundary. `table_value`: `row` is text
that appears in exactly one row, `col` is header text, `value` the exact cell content.

## Track C: compliance matrix (`requirements.jsonl`)

Every requirement the document places on the tenderer / respondent / contractor, on the bench pages:

```json
{"id": "nar-r001", "page": 16, "text": "Respondents are to provide full details for any claims, statements or examples used to address the qualitative criteria", "obligation": "mandatory", "category": "submission"}
```

- `text`: verbatim, one requirement per item. Split lettered sub-items into separate items. Keep enough words
  for the item to stand alone.
- `obligation`:
  - `mandatory`: must / shall / is to / required; failing it can exclude the bid or breach the contract.
  - `evaluated`: scored against criteria (describe, demonstrate, provide details of experience...).
  - `administrative`: submission mechanics (forms, signatures, format, copies, deadline, lodgement).
  - `informational`: should / may / guidance with no hard obligation.
- `category`: free text such as `submission`, `evaluation`, `insurance`, `whs`, `pricing`, `contract`, `delivery`.
- Exclude: what the buyer will do, definitions, background, and general legal boilerplate with no action for the tenderer.

## Track D: questions (`questions.jsonl`)

```json
{"id": "nar-q01", "doc": "narembeen_rft", "question": "What weighting does price carry in the evaluation?", "answer": "50%", "evidence": [{"page": 17}], "answerable": true, "type": "table"}
{"id": "nar-q09", "doc": "narembeen_rft", "question": "What is the liquidated damages rate per day?", "answer": "", "evidence": [], "answerable": false, "type": "unanswerable"}
```

- Answers short and exact (a number, date, name or short phrase) so they can be checked automatically.
- `evidence`: every page where the answer is stated.
- Phrase questions the way a bid writer would ask, not by copying the sentence that answers them.
- Mix types: `table`, `number`, `procedure`, `definition`, `cross-reference`, `form`.
- Include 1-2 `answerable: false` questions per document: plausible, but the document does not answer them
  (check the full text to be sure).
