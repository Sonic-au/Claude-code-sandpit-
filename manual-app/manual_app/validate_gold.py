"""Consistency checks for gold annotations: `python -m manual_app.validate_gold [doc_id ...]`.

- every JSONL line parses and has the required fields
- rules pass against the gold transcription of their page (or, for `present`/`absent`, the PDF text layer)
- `table_value` rules pass against the gold table on that page, where one exists
- each safety notice's text is found on its page's text layer
- each answerable question's answer appears on one of its evidence pages
Exit code 1 if anything fails.
"""
from __future__ import annotations

import json
import sys

import pypdf
from rapidfuzz import fuzz

from .bench import GOLD, _jsonl
from .corpus import get_document, load_manifest
from .metrics import check_rule, contains_answer
from .normalize import content_text, norm_text
from .parsers.base import ParseResult

REQ = {"rules": {"id", "type", "category"},
       "safety": {"id", "page", "text", "kind"},
       "tables": {"id", "page", "html"}, "questions": {"id", "doc", "question", "answer", "evidence", "answerable"}}
KINDS = {"danger", "warning", "caution", "note"}


def validate(doc_id: str) -> list[str]:
    doc = get_document(doc_id)
    if doc.derived_from:
        return []
    errs = []
    gdir = GOLD / doc_id
    pm = doc.page_map()
    reader = pypdf.PdfReader(str(doc.bench_pdf))
    layer = {pg: reader.pages[i].extract_text() or "" for i, pg in enumerate(pm)}
    gold_pages = {int(f.stem[1:]): f.read_text() for f in sorted((gdir / "pages").glob("p*.md"))} \
        if (gdir / "pages").exists() else {}
    tables = _jsonl(gdir / "tables.jsonl")

    for kind in ("rules", "safety", "tables", "questions"):
        for i, item in enumerate(_jsonl(gdir / f"{kind}.jsonl")):
            missing = REQ[kind] - set(item)
            if missing:
                errs.append(f"{doc_id} {kind}[{i}] missing {missing}")
            pg = item.get("page")
            if pg is not None and pg not in pm:
                errs.append(f"{doc_id} {item.get('id')}: page {pg} not in bench pages")

    ids = [x.get("id") for k in ("rules", "safety", "tables", "questions")
           for x in _jsonl(gdir / f"{k}.jsonl")]
    dup = {i for i in ids if ids.count(i) > 1}
    if dup:
        errs.append(f"{doc_id} duplicate ids: {sorted(dup)}")

    gold_result = ParseResult("gold", doc_id, [gold_pages.get(p, "") for p in pm], pm, 0)
    layer_result = ParseResult("layer", doc_id, [layer[p] for p in pm], pm, 0)
    for r in _jsonl(gdir / "rules.jsonl"):
        pg = r.get("page")
        if r["type"] == "table_value":
            tabs = [t for t in tables if t["page"] == pg]
            if tabs:
                tr = ParseResult("tab", doc_id, ["\n".join(t["html"] for t in tabs if t["page"] == p) for p in pm], pm, 0)
                if not check_rule(r, tr):
                    errs.append(f"{doc_id} {r['id']}: table_value fails against gold table(s) on p{pg}")
            continue
        if pg in gold_pages:
            if r["type"] == "absent":
                continue  # absent rules target running headers, which transcriptions leave out by design
            if not check_rule(r, gold_result):
                errs.append(f"{doc_id} {r['id']}: {r['type']} fails against gold transcription p{pg}")
        elif r["type"] in ("present", "absent"):
            ok = check_rule({**r, "type": "present"}, layer_result)
            if not ok:
                errs.append(f"{doc_id} {r['id']}: text not found on PDF text layer p{pg}")
        elif r["type"] in ("steps", "near", "order") and not check_rule(r, layer_result):
            # The text layer's reading order is unreliable, so this is a prompt to look, not a failure.
            print(f"  warning: {doc_id} {r['id']}: {r['type']} does not hold on the PDF text layer p{pg} "
                  "(check against the page image)")

    items = [(q, "kind", KINDS) for q in _jsonl(gdir / "safety.jsonl")]
    for q, field, allowed in items:
        if q.get(field) not in allowed:
            errs.append(f"{doc_id} {q['id']}: bad {field} {q.get(field)}")
        # A notice may start on its page and run onto the next one.
        nxt = pm[pm.index(q["page"]) + 1] if q["page"] in pm and pm.index(q["page"]) + 1 < len(pm) else None
        here, there = content_text(layer.get(q["page"], "")), content_text(layer.get(nxt, "") if nxt else "")
        t = norm_text(q["text"])
        on_page = fuzz.partial_ratio(t, here) >= 88
        # Running headers/footers interrupt a sentence that crosses the page break, so check the halves.
        spans = False
        if there and not on_page:
            cuts = [i for i, ch in enumerate(t) if ch == " "]
            spans = any(fuzz.partial_ratio(t[:c], here) >= 88 and fuzz.partial_ratio(t[c + 1:], there) >= 88
                        for c in cuts)
        if not (on_page or spans):
            errs.append(f"{doc_id} {q['id']}: notice text not found on p{q['page']}")

    for q in _jsonl(gdir / "questions.jsonl"):
        if q.get("answerable", True):
            pages = [e["page"] for e in q.get("evidence", [])]
            if not pages:
                errs.append(f"{doc_id} {q['id']}: answerable question without evidence")
            elif not any(contains_answer(layer.get(p, "") + " " + gold_pages.get(p, ""), q["answer"]) or
                         # long, multi-line answers (procedures): a fuzzy match on the page is the fair test
                         (len(q["answer"]) > 60 and fuzz.partial_ratio(norm_text(q["answer"]),
                                                                        content_text(layer.get(p, ""))) >= 85)
                         for p in pages):
                errs.append(f"{doc_id} {q['id']}: answer '{q['answer']}' not found on evidence pages {pages}")
    return errs


def merge_questions() -> int:
    """Concatenate every document's gold/<doc>/questions.jsonl (all corpora) into gold/questions.jsonl."""
    from .corpus import CORPORA
    lines = []
    for d in [d for p in sorted(CORPORA.glob("*.yaml")) for d in load_manifest(p)]:
        lines += [json.dumps(q, ensure_ascii=False) for q in _jsonl(GOLD / d.id / "questions.jsonl")]
    (GOLD / "questions.jsonl").write_text("\n".join(lines) + "\n")
    return len(lines)


def main(argv=None):
    ids = (argv if argv is not None else sys.argv[1:]) or [d.id for d in load_manifest()]  # default corpus
    all_errs = []
    for i in ids:
        e = validate(i)
        all_errs += e
        print(f"{i}: {'OK' if not e else str(len(e)) + ' problem(s)'}")
    for e in all_errs:
        print("  " + e)
    n = merge_questions()
    print(f"merged {n} questions into gold/questions.jsonl")
    return 1 if all_errs else 0


if __name__ == "__main__":
    raise SystemExit(main())
