# Manual Handling annotation guide

Gold data is the bench. Annotate from the **page image** (what a person sees), never from a
parser's output: copying a parser's text would bias the bench towards that parser. The PDF text
layer may be used to copy exact wording, but check reading order and table structure against the
image.

All page numbers are **original document page numbers** (see `corpus/<name>.yaml`).

Files per document, under `gold/<doc_id>/`:

| File | Track | What it holds |
|---|---|---|
| `pages/pNNN.md` | A | Full transcription of selected pages |
| `tables.jsonl` | A | Selected tables as HTML |
| `rules.jsonl` | B | Pass/fail checks |
| `safety.jsonl` | C | Safety notices (WARNING, CAUTION, NOTE) |
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

One JSON object per line: `{"id": "xyl-t1", "page": 8, "caption": "1.5.1 Spare parts - recommended spare parts stock (i= number of stages)", "html": "<table>...</table>"}`.
Same table conventions as above. Cell text exactly as printed; omit checkbox glyphs. A table that continues across pages
is annotated per page.

## Track B: rules (`rules.jsonl`)

One check per line, each verified true against the page image. Types:

```json
{"id": "xyl-b05", "type": "present", "page": 19, "category": "safety", "text": "Do not use this unit in environments that may contain flammable/explosive or chemically aggressive gases or powders."}
{"id": "xyl-b13", "type": "table_value", "page": 26, "category": "table", "row": "60", "col": "Ft-lb", "value": "75"}
{"id": "xyl-b18", "type": "heading", "page": 34, "category": "heading", "text": "7.2 The main switch is on, but the electric pump does not start"}
{"id": "xyl-b20", "type": "absent", "page": 34, "category": "header", "text": "e-MPA, e-MPR, e-MPD INSTRUCTION MANUAL"}
```

Categories: `clause` (a key sentence survives verbatim), `number` (dates, amounts, percentages, clause
references), `table` (cell lookups), `form` (returnable form labels and order), `order` (reading order across
columns, sections and table cells), `heading` (section headings marked up as headings), `header` (running headers,
footers and page numbers that should NOT pollute the text; use only for text repeated on many pages).

`present` text: 6-30 words copied exactly; avoid text that spans a table cell boundary. `table_value`: `row` is text
that appears in exactly one row, `col` is header text, `value` the exact cell content.

## Track D: questions (`questions.jsonl`)

```json
{"id": "xyl-q01", "doc": "xylem_empa", "question": "What dry torque do the capscrews on a size 60 coupling get, in ft-lb?", "answer": "75 Ft-lb", "evidence": [{"page": 26}], "answerable": true, "type": "spec"}
{"id": "xyl-q09", "doc": "xylem_empa", "question": "What is the maximum permissible radial misalignment between the coupling halves, in mm?", "answer": "", "evidence": [], "answerable": false, "type": "unanswerable"}
```

- Answers short and exact (a number, date, name or short phrase) so they can be checked automatically.
- `evidence`: every page where the answer is stated.
- Phrase questions the way a bid writer would ask, not by copying the sentence that answers them.
- Mix types: `table`, `number`, `procedure`, `definition`, `cross-reference`, `form`.
- Include 1-2 `answerable: false` questions per document: plausible, but the document does not answer them
  (check the full text to be sure).

## Technical manuals (`corpus/manuals.yaml`)

The use case is a **technician asking a question** ("what torque for a 1/4-28 bolt?", "what do I check if the
engine cranks but won't start?") and needing the right answer with the page to check. Tracks A and B work as
above; the differences are:

### Track B: extra rule categories and types for manuals

| Category | Checks | Typical type |
|---|---|---|
| `step_order` | A procedure's steps survive complete and in order | `steps` |
| `safety` | A WARNING/CAUTION survives verbatim, and stays next to the step it governs | `present`, `near` |
| `spec` | A value keeps its unit and its parameter (e.g. "37 V" next to "Input voltage") | `near`, `present` |
| `table` | Spec, torque or troubleshooting table cells | `table_value` |
| `part_number` | Part numbers, model codes, fault codes and command names survive exactly (`AN310`, `pg_dump -Fc`) | `present` |
| `heading`, `header`, `order` | As above | |

```json
{"id": "xyl-b07", "type": "steps", "page": 31, "category": "step_order", "steps": ["Locate the arrows on the adaptor", "Start the pump", "Stop the pump"]}
{"id": "xyl-b08", "type": "near", "page": 32, "category": "safety", "a": "Disconnect and lock out electrical power", "b": "before installing or servicing", "window": 120}
{"id": "ti-b03", "type": "near", "page": 6, "category": "spec", "a": "Input-to-output differential voltage", "b": "40", "window": 120}
```

`near` windows count characters of normalised text; keep them tight (60-200) so the rule tests adjacency.

### Track C: safety notices (`safety.jsonl`)

Every safety notice on the bench pages: one item per distinct statement (split bulleted notices into one item
per bullet).

```json
{"id": "xyl-s01", "page": 32, "kind": "warning", "text": "Disconnect and lock out electrical power before installing or servicing the unit."}
```

- Only notices printed with a signal word count. Table footnotes and legal notices do not, so the TI LM317
  datasheet has no `safety.jsonl` (its three earlier items were footnotes with no signal word).
- `kind`: `danger`, `warning`, `caution` (includes NOTICE), `note` (includes IMPORTANT). Use the signal word printed
  on the page.
- `text`: the notice body verbatim, without the signal word.
- Warnings and dangers are the critical class: the report's "all warnings found" check requires every one.

### Track D for manuals: technician questions

8-10 per manual, phrased as a technician would ask, short exact answers (a value with unit, a part number, a step,
a remedy), evidence pages listed. Mix types: `spec` (table/spec lookup), `procedure` (what to do / which step comes
next), `troubleshooting` (symptom to cause or remedy), `safety` (what precaution), `part_number`, `definition`, and
1-2 `unanswerable` ones the bench pages do not answer.
