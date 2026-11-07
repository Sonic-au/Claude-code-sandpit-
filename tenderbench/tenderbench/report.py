"""Turn per-document scores into a leaderboard (Markdown + JSON)."""
from __future__ import annotations

import json
import statistics
from collections import defaultdict
from pathlib import Path

from .parsers import FACTORIES


def _mean(xs):
    xs = [x for x in xs if x is not None]
    return statistics.fmean(xs) if xs else None


def _fmt(x, pct=True, nd=1):
    if x is None:
        return "-"
    return f"{x * 100:.{nd}f}" if pct else f"{x:.{nd}f}"


def summarise(rows: list[dict]) -> dict:
    by_parser = defaultdict(list)
    for r in rows:
        by_parser[r["parser"]].append(r)
    summary = {}
    for p, rs in by_parser.items():
        def g(fn, subset=None):
            return _mean([fn(r) for r in (subset or rs)])
        scan = [r for r in rs if r["doc"].endswith("_scan")]
        digital = [r for r in rs if not r["doc"].endswith("_scan")]
        row = {
            "text_similarity": g(lambda r: r.get("A", {}).get("text_similarity"), digital),
            "teds": g(lambda r: r.get("A", {}).get("teds"), digital),
            "teds_struct": g(lambda r: r.get("A", {}).get("teds_struct"), digital),
            "rules": g(lambda r: (r.get("B") or {}).get("pass_rate"), digital),
            "req_f1": g(lambda r: (r.get("C") or {}).get("rules_baseline", {}).get("f1"), digital),
            "req_recall_mand": g(lambda r: (r.get("C") or {}).get("rules_baseline", {}).get("recall_mandatory"), digital),
            "req_f1_llm": g(lambda r: (r.get("C") or {}).get("llm", {}).get("f1"), digital),
            "recall5": g(lambda r: (r.get("D") or {}).get("hybrid-ctx", {}).get("recall@5"), digital),
            "scan_text_similarity": g(lambda r: r.get("A", {}).get("text_similarity"), scan) if scan else None,
            "scan_rules": g(lambda r: (r.get("B") or {}).get("pass_rate"), scan) if scan else None,
            "sec_per_page": g(lambda r: r.get("sec_per_page")),
            "cost_per_1k_pages": (lambda c: None if c is None else c * 1000)(
                g(lambda r: (r["cost_usd"] / r["pages"]) if r.get("cost_usd") is not None else None)),
            "errors": [f"{r['doc']}: {r['error']}" for r in rs if r.get("error")],
        }
        parts = [row["text_similarity"], row["teds"], row["rules"], row["req_f1"], row["recall5"]]
        row["overall"] = _mean(parts)
        summary[p] = row
    return summary


def write_report(rows: list[dict], out_dir: Path, llm_label: str | None = None) -> None:
    s = summarise(rows)
    (out_dir / "summary.json").write_text(json.dumps(s, indent=1, default=str))
    meta = {}
    for name, f in FACTORIES.items():
        try:
            p = f()
            meta[p.name] = (p.residency, p.licence)
        except Exception:
            pass
    order = sorted(s, key=lambda p: -(s[p]["overall"] or 0))
    L = ["# TenderBench results", ""]
    L.append("Scores are percentages (higher is better) on the digital documents; the scan columns use the "
             "simulated scan. **Overall** is the mean of text similarity, TEDS, rule pass rate, requirement F1 "
             "(rule-based extractor) and evidence recall@5 (hybrid + context).")
    L.append("")
    L.append("| Parser | Overall | Text sim | Table TEDS | TEDS-S | Rule tests | Req F1 | Mand. recall | Recall@5 | "
             "Scan text | Scan rules | s/page | Residency | Licence |")
    L.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for p in order:
        r = s[p]
        res, lic = meta.get(p, ("?", "?"))
        L.append(f"| {p} | **{_fmt(r['overall'])}** | {_fmt(r['text_similarity'])} | {_fmt(r['teds'])} | "
                 f"{_fmt(r['teds_struct'])} | {_fmt(r['rules'])} | {_fmt(r['req_f1'])} | {_fmt(r['req_recall_mand'])} | "
                 f"{_fmt(r['recall5'])} | {_fmt(r['scan_text_similarity'])} | {_fmt(r['scan_rules'])} | "
                 f"{_fmt(r['sec_per_page'], pct=False, nd=2)} | {res} | {lic} |")
    L.append("")
    if llm_label:
        L.append(f"LLM steps used `{llm_label}`.")
    else:
        L.append("No LLM was configured, so the LLM requirement extractor and answer scoring were not run "
                 "(set TB_LLM_PROVIDER / TB_LLM_MODEL).")
    L.append("")
    # Per-document detail
    L.append("## Per document")
    L.append("")
    L.append("| Document | Parser | Text sim | TEDS | Rules | Req F1 | Mand. recall | All mand. found | Recall@5 bm25 / dense / hybrid / hybrid-ctx |")
    L.append("|---|---|---|---|---|---|---|---|---|")
    for r in sorted(rows, key=lambda r: (r["doc"], r["parser"])):
        a, b, c, d = r.get("A", {}), r.get("B") or {}, (r.get("C") or {}).get("rules_baseline", {}), r.get("D") or {}
        rec = " / ".join(_fmt(d.get(k, {}).get("recall@5")) for k in ("bm25", "dense", "hybrid", "hybrid-ctx"))
        amf = c.get("all_mandatory_found")
        L.append(f"| {r['doc']} | {r['parser']} | {_fmt(a.get('text_similarity'))} | {_fmt(a.get('teds'))} | "
                 f"{_fmt(b.get('pass_rate'))} | {_fmt(c.get('f1'))} | {_fmt(c.get('recall_mandatory'))} | "
                 f"{'-' if amf is None else ('yes' if amf else 'no')} | {rec} |")
    L.append("")
    # Rule categories
    cats = defaultdict(lambda: defaultdict(list))
    for r in rows:
        if r["doc"].endswith("_scan"):
            continue
        for k, v in (r.get("B") or {}).get("by_category", {}).items():
            cats[r["parser"]][k].append(v)
    allc = sorted({k for p in cats for k in cats[p]})
    if allc:
        L.append("## Rule tests by category")
        L.append("")
        L.append("| Parser | " + " | ".join(allc) + " |")
        L.append("|---|" + "---|" * len(allc))
        for p in order:
            L.append(f"| {p} | " + " | ".join(_fmt(_mean(cats[p].get(k, []))) for k in allc) + " |")
        L.append("")
    errs = [(p, e) for p in order for e in s[p]["errors"]]
    if errs:
        L.append("## Errors")
        L.append("")
        for p, e in errs:
            L.append(f"- {p}: {e}")
    (out_dir / "report.md").write_text("\n".join(L) + "\n")
