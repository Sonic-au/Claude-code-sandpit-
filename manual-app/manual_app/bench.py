"""Run parsers over the corpus and score them on the four tracks.

Track A  parse fidelity   text similarity on gold pages; TEDS / TEDS-S on gold tables
Track B  rule tests       pass rate of deterministic checks (clauses, tables, forms, order, OCR)
Track C  requirements     compliance-matrix F1, mandatory recall, all-mandatory-found
Track D  retrieval / QA   evidence recall@5, MRR; answer accuracy and abstention if an LLM is set
"""
from __future__ import annotations

import json
import os
import statistics
import time
from pathlib import Path

from . import extract, retrieve
from .corpus import DATA, ROOT, Document, build, load_manifest
from .llm import get_llm
from .metrics import (answer_coverage, best_teds, contains_answer, recall_at_k, reciprocal_rank, score_requirements,
                      score_rules, text_similarity, token_f1)
from .normalize import extract_tables
from .parsers import ParseResult, get_parser

GOLD = ROOT / "gold"
OUTPUTS = DATA / "outputs"


# ------------------------------------------------------------------ gold

def _jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(l) for l in path.read_text().splitlines() if l.strip() and not l.startswith("//")]


def load_gold(doc: Document) -> dict:
    gdir = GOLD / doc.gold_id
    pages_in = set(doc.page_map())

    def keep(item):  # derived docs (e.g. the scan) only cover some pages of their source
        return item.get("page") is None or item["page"] in pages_in

    gold_pages = {}
    for f in sorted((gdir / "pages").glob("p*.md")) if (gdir / "pages").exists() else []:
        pg = int(f.stem[1:])
        if pg in pages_in:
            gold_pages[pg] = f.read_text()
    rules = [r for r in _jsonl(gdir / "rules.jsonl") if keep(r)]
    if doc.derived_from:   # page-less rules can't be attributed to the subset
        rules = [r for r in rules if r.get("page")]
    return {
        "pages": gold_pages,
        "tables": [t for t in _jsonl(gdir / "tables.jsonl") if keep(t)],
        "rules": rules,
        "requirements": [r for r in _jsonl(gdir / "requirements.jsonl") if keep(r)],
        "safety": [r for r in _jsonl(gdir / "safety.jsonl") if keep(r)],
        # Independent gold: vendor HTML/spec pages and TechManualQA snippets (see vendor.py).
        "vendor_rules": [r for r in _jsonl(gdir / "vendor_rules.jsonl") if keep(r)],
        "questions": [q for q in _jsonl(GOLD / "questions.jsonl") + _jsonl(gdir / "vendor_questions.jsonl")
                      if q["doc"] == doc.gold_id and all(e["page"] in pages_in for e in q.get("evidence", []))],
    }


# ------------------------------------------------------------------ parsing

def output_path(parser: str, doc_id: str) -> Path:
    import re
    return OUTPUTS / re.sub(r"[^A-Za-z0-9_.-]+", "_", parser) / f"{doc_id}.json"


def run_parser(parser_name: str, docs: list[Document], allow_offshore: bool = False, force: bool = False,
               log=print) -> list[ParseResult]:
    parser = get_parser(parser_name)
    ok, why = parser.available()
    if not ok:
        log(f"  skip {parser_name}: {why}")
        return []
    if parser.residency == "offshore" and not allow_offshore:
        log(f"  skip {parser_name}: sends documents offshore (use --allow-offshore for public documents)")
        return []
    results = []
    for d in docs:
        out = output_path(parser.name, d.id)
        if out.exists() and not force:
            results.append(ParseResult.load(out))
            continue
        if not d.bench_pdf.exists():
            build(d)
        log(f"  {parser.name} <- {d.id}")
        r = parser.parse(d.bench_pdf, d.id, d.page_map())
        r.meta.update({"residency": parser.residency, "licence": parser.licence})
        r.save(out)
        results.append(r)
    return results


# ------------------------------------------------------------------ tracks

def track_a(result: ParseResult, gold: dict) -> dict:
    sims = {pg: text_similarity(result.page(pg), md) for pg, md in gold["pages"].items()}
    teds_full, teds_struct = {}, {}
    for t in gold["tables"]:
        preds = extract_tables(result.page(t["page"]))
        teds_full[t["id"]] = best_teds(preds, t["html"])
        teds_struct[t["id"]] = best_teds(preds, t["html"], structure_only=True)
    mean = lambda d: statistics.fmean(d.values()) if d else None
    return {"text_similarity": mean(sims), "teds": mean(teds_full), "teds_struct": mean(teds_struct),
            "per_page": sims, "per_table": teds_full}


def track_c(result: ParseResult, gold: dict, doc: Document, llm=None) -> dict:
    if gold.get("safety"):          # manuals: safety-notice extraction, warnings/dangers are critical
        preds = extract.extract_safety(result.pages, result.page_map)
        out = {"rules_baseline": score_requirements(preds, gold["safety"], label="kind",
                                                    critical=("warning", "danger")), "task": "safety"}
        if llm is not None:
            preds = extract.extract_safety_llm(llm, result.pages, result.page_map, doc.title)
            out["llm"] = score_requirements(preds, gold["safety"], label="kind", critical=("warning", "danger"))
            out["llm"]["model"] = llm.label
        return out
    if not gold["requirements"]:
        return {}
    out = {"task": "requirements"}
    preds = extract.extract_rules(result.pages, result.page_map)
    out["rules_baseline"] = score_requirements(preds, gold["requirements"])
    if llm is not None:
        preds = extract.extract_llm(llm, result.pages, result.page_map, doc.title)
        out["llm"] = score_requirements(preds, gold["requirements"])
        out["llm"]["model"] = llm.label
    return out


ANSWER_STRATEGY = os.environ.get("TB_ANSWER_STRATEGY", "hybrid-rerank")   # retrieval used for the answer step


def track_d(result: ParseResult, gold: dict, doc: Document, llm=None,
            strategies=("bm25", "dense", "hybrid", "hybrid-ctx", "hybrid-rerank"), k: int = 5, grader=None) -> dict:
    qs = gold["questions"]
    if not qs:
        return {}
    chunks = retrieve.chunk_pages(result.pages, result.page_map)
    out = {}
    for strat in strategies:
        rec, mrr = [], []
        for q in qs:
            if not q.get("answerable", True):
                continue
            ranked = retrieve.search(q["question"], chunks, strat, doc.title)
            pages = [c.page for c in ranked]
            ev = [e["page"] for e in q["evidence"]]
            rec.append(recall_at_k(pages, ev, k))
            mrr.append(reciprocal_rank(pages, ev))
        out[strat] = {"recall@5": statistics.fmean(rec) if rec else None, "mrr": statistics.fmean(mrr) if mrr else None,
                      "n": len(rec)}
    if llm is not None:
        correct, lenient, f1s, cite_ok, abstain_ok, n_ans, n_un = 0, 0, [], 0, 0, 0, 0
        from .judge import Grader, JevError, summarise
        from .llm import LLMRefusal
        grader = grader or Grader(llm)
        refused, grades = 0, []
        for q in qs:
            top = retrieve.search(q["question"], chunks, ANSWER_STRATEGY, doc.title)[:k]
            try:
                ans, cited = retrieve.answer(llm, q["question"], top, doc.title)
            except LLMRefusal:
                refused += 1
                ans, cited = "", []
            if q.get("answerable", True):
                n_ans += 1
                ok = contains_answer(ans, q["answer"])
                correct += ok
                lenient += ok or answer_coverage(ans, q["answer"]) >= 0.7
                f1s.append(token_f1(ans, q["answer"]))
                cite_ok += bool(set(cited) & {e["page"] for e in q["evidence"]})
                try:
                    grades.append({"id": q.get("id"), "question": q["question"], "reference": q["answer"], "answer": ans,
                                   **grader.grade(q["question"], q["answer"], ans, doc.title)})
                except (LLMRefusal, JevError):
                    pass
            else:
                n_un += 1
                abstain_ok += "not found" in ans.lower()
        out["answers"] = {"model": llm.label, "retrieval": ANSWER_STRATEGY, "grader": grader.label,
                          "accuracy": correct / n_ans if n_ans else None,
                          "lenient_accuracy": lenient / n_ans if n_ans else None,
                          **summarise(grades, n_ans), "grades": grades,
                          "token_f1": statistics.fmean(f1s) if f1s else None,
                          "citation_accuracy": cite_ok / n_ans if n_ans else None,
                          "abstention_accuracy": abstain_ok / n_un if n_un else None, "refused": refused}
    return out


def score(result: ParseResult, doc: Document, llm=None, tracks="ABCD", grader=None) -> dict:
    gold = load_gold(doc)
    s = {"doc": doc.id, "kind": doc.kind, "category": doc.category, "parser": result.parser, "error": result.error,
         "seconds": result.seconds, "pages": len(result.page_map),
         "sec_per_page": result.seconds / max(1, len(result.page_map)), "cost_usd": result.cost_usd}
    if "A" in tracks:
        s["A"] = track_a(result, gold)
    if "B" in tracks and gold["rules"]:
        s["B"] = score_rules(gold["rules"], result)
    if "B" in tracks and gold["vendor_rules"]:
        s["V"] = score_rules(gold["vendor_rules"], result)
    if "C" in tracks:
        s["C"] = track_c(result, gold, doc, llm)
    if "D" in tracks:
        s["D"] = track_d(result, gold, doc, llm, grader=grader)
    return s


# ------------------------------------------------------------------ orchestration

def run(parsers: list[str], doc_ids: list[str] | None = None, allow_offshore: bool = False, force: bool = False,
        tracks: str = "ABCD", use_llm: bool = True, out_dir: Path | None = None, log=print,
        corpus: str | None = None) -> Path:
    from .corpus import manifest_path
    mpath = manifest_path(corpus)
    docs = [d for d in load_manifest(mpath) if not doc_ids or d.id in doc_ids]
    llm = get_llm() if use_llm else None
    if llm and llm.residency == "offshore":
        log(f"note: LLM {llm.label} is offshore; only public documents are in this corpus.")
    grader = None
    if llm and "D" in tracks:
        from .judge import Grader
        grader = Grader(llm)
        if grader.jev:
            log(f"note: answers graded by {grader.label}; Jev is a hosted offshore service (public documents only).")
    rows = []
    for name in parsers:
        log(f"parser {name}")
        for r in run_parser(name, docs, allow_offshore, force, log):
            d = next(x for x in docs if x.id == r.doc_id)
            row = score(r, d, llm, tracks, grader)
            row["corpus"] = mpath.stem
            rows.append(row)
    out_dir = out_dir or (ROOT / "results" / time.strftime("%Y%m%d-%H%M%S"))
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "scores.json").write_text(json.dumps(rows, indent=1, default=str))
    from .report import write_report
    llm_info = None
    if llm:
        llm_info = {"label": llm.label, "residency": llm.residency, **llm.usage, "cost_usd": llm.cost_usd}
        if grader and grader.jev:
            from .judge import threshold_sweep
            llm_info["judge"] = {"label": grader.label, **grader.jev.usage, "cost_usd": grader.jev.cost_usd,
                                 "threshold_sweep": threshold_sweep(
                                     [g for r in rows for g in ((r.get("D") or {}).get("answers") or {}).get("grades", [])])}
        (out_dir / "llm_usage.json").write_text(json.dumps(llm_info, indent=1))
    write_report(rows, out_dir, llm_label=llm.label if llm else None, llm_info=llm_info)
    log(f"wrote {out_dir}")
    return out_dir
