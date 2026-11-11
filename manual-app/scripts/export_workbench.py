#!/usr/bin/env python3
"""Export the manuals, their parsed pages, test questions and results for the Manual Handling Workbench page.

  python scripts/export_workbench.py <out_dir> [--parser docling] [--results <dir> ...]

Writes <out_dir>/data.json (manuals, parsed page text, search chunks, questions with Claude's answers and grades)
and <out_dir>/pages/<doc>/<page>.jpg (page images rendered from the bench PDFs). Claude's answers are read from the
session cache (data/session_llm), so nothing is sent to any model. Grades come from the newest results folders
that hold per-answer grades (TB_JUDGE=compare runs).
"""
import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("TB_LLM_PROVIDER", "session")

from manual_app import bench, retrieve  # noqa: E402
from manual_app.corpus import load_manifest, manifest_path  # noqa: E402
from manual_app.llm import LLMRefusal, get_llm  # noqa: E402
from manual_app.parsers.base import ParseResult  # noqa: E402

CORPORA = ("manuals", "techmanualqa", "hvac")
GRAPH_CORPUS = "hvac"
QUESTION_TYPES = ["spec", "procedure", "troubleshooting", "safety", "part_number", "definition", "location",
                  "tool_or_material", "conditional", "unanswerable"]


def render_pages(pdf: Path, page_map: list[int], out: Path, width: int = 900) -> None:
    import pypdfium2 as pdfium
    out.mkdir(parents=True, exist_ok=True)
    doc = pdfium.PdfDocument(str(pdf))
    for i, src in enumerate(page_map):
        target = out / f"{src}.jpg"
        if target.exists():
            continue
        page = doc[i]
        scale = width / page.get_width()
        page.render(scale=scale).to_pil().convert("RGB").save(target, "JPEG", quality=72, optimize=True)


def latest_grades(results_dirs: list[Path]) -> dict:
    grades = {}
    for d in results_dirs:
        for r in json.loads((d / "scores.json").read_text()):
            for g in (((r.get("D") or {}).get("answers") or {}).get("grades") or []):
                grades[(r["doc"], g.get("id"))] = {k: g.get(k) for k in ("final", "by", "jev", "confidence", "claude")}
    return grades


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--parser", default="docling")
    ap.add_argument("--results", nargs="*", default=None)
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    res_dirs = [Path(p) for p in a.results] if a.results else sorted(
        p for p in (ROOT / "results").glob("*-jev-compare") if (p / "scores.json").exists())
    grades = latest_grades(res_dirs)
    llm = get_llm()
    manuals = []
    for corpus in CORPORA:
        for doc in load_manifest(manifest_path(corpus)):
            r = ParseResult.load(bench.output_path(a.parser, doc.id))
            gold = bench.load_gold(doc)
            render_pages(doc.bench_pdf, r.page_map, out / "pages" / doc.id)
            chunks = retrieve.chunk_pages(r.pages, r.page_map)
            qs = []
            for q in gold["questions"]:
                top = retrieve.search(q["question"], chunks, bench.ANSWER_STRATEGY, doc.title)[:5]
                answer, cited = None, []
                try:
                    answer, cited = retrieve.answer(llm, q["question"], top, doc.title)
                except LLMRefusal:
                    pass
                g = grades.get((doc.id, q.get("id")), {})
                qs.append({"id": q.get("id"), "question": q["question"], "answer": q.get("answer", ""),
                           "evidence": [e["page"] for e in q.get("evidence", [])],
                           "answerable": q.get("answerable", True), "type": q.get("type", ""),
                           "claude_answer": answer, "cited_pages": cited,
                           "retrieved_pages": [c.page for c in top], **{f"grade_{k}": v for k, v in g.items()}})
            manuals.append({"id": doc.id, "corpus": corpus, "title": doc.title, "kind": doc.kind,
                            "category": doc.category, "pages": r.page_map,
                            "page_text": {str(p): md for p, md in zip(r.page_map, r.pages)},
                            "chunks": [{"page": c.page, "heading": c.heading, "text": c.text} for c in chunks],
                            "questions": qs})
            print(f"{doc.id}: {len(r.page_map)} pages, {len(chunks)} chunks, {len(qs)} questions")
    graph = None
    gpath = ROOT / "graph" / f"{GRAPH_CORPUS}.json"
    if gpath.exists():
        g = json.loads(gpath.read_text())
        graph = {"corpus": g["corpus"], "meta": g["meta"],
                 "nodes": [{k: n[k] for k in ("id", "type", "label", "aliases", "props", "sources", "by")} for n in g["nodes"]],
                 "edges": [{"src": e["src"], "type": e["type"], "dst": e["dst"]} for e in g["edges"]]}
    data = {"parser": a.parser, "graph": graph, "answer_strategy": bench.ANSWER_STRATEGY, "answer_prompt": retrieve.ANSWER_PROMPT,
            "question_types": QUESTION_TYPES, "results": [p.name for p in res_dirs], "manuals": manuals}
    (out / "data.json").write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")))
    print(f"wrote {out / 'data.json'} ({(out / 'data.json').stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
