"""Command line: `python -m manual_app <command>`."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import bench, corpus
from .parsers import FACTORIES, get_parser

LOCAL_DEFAULT = ["pypdf-text", "pymupdf4llm", "liteparse", "docling"]


def main(argv=None):
    ap = argparse.ArgumentParser(prog="manual_app", description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    f = sub.add_parser("fetch", help="download source PDFs and build the bench PDFs")
    f.add_argument("--corpus", default="", help="corpus manifest name (default: manuals; or tenders)")
    sub.add_parser("parsers", help="list parser adapters and whether they can run here")
    sub.add_parser("vendor", help="build independent gold from vendor websites and TechManualQA-700")

    p = sub.add_parser("run", help="parse (cached) and score")
    p.add_argument("--parsers", default=",".join(LOCAL_DEFAULT),
                   help=f"comma list; known: {', '.join(FACTORIES)}")
    p.add_argument("--docs", default="", help="comma list of document ids (default: all)")
    p.add_argument("--tracks", default="ABCD")
    p.add_argument("--allow-offshore", action="store_true",
                   help="allow parsers that send documents outside Australia (public documents only)")
    p.add_argument("--force", action="store_true", help="re-parse even if cached output exists")
    p.add_argument("--no-llm", action="store_true", help="skip LLM steps even if configured")
    p.add_argument("--out", default="", help="results directory")
    p.add_argument("--corpus", default="", help="corpus manifest name (default: manuals; or tenders)")

    g = sub.add_parser("graph", help="build the knowledge graph for a corpus (rules plus LLM page extraction)")
    g.add_argument("--corpus", default="hvac")
    g.add_argument("--parser", default="docling")
    g.add_argument("--no-llm", action="store_true", help="rules only: manuals, refrigerants and safety notices")

    ge = sub.add_parser("graph-eval", help="compare text-only and graph-narrowed search across a corpus's manuals")
    ge.add_argument("--corpus", default="hvac")
    ge.add_argument("--parser", default="docling")
    ge.add_argument("--out", default="", help="write the full result as JSON")

    a = ap.parse_args(argv)
    if a.cmd == "fetch":
        for d in corpus.load_manifest(corpus.manifest_path(a.corpus or None)):
            corpus.build(d)
            print(f"{d.id}: {len(d.page_map())} pages -> {d.bench_pdf}")
    elif a.cmd == "vendor":
        from .vendor import build_all
        for r in build_all():
            r = {k: v for k, v in r.items() if k not in ("source", "sources")}
            print(json.dumps(r, ensure_ascii=False))
    elif a.cmd == "parsers":
        for name in FACTORIES:
            pr = get_parser(name)
            ok, why = pr.available()
            print(f"{name:22} {'ready' if ok else 'unavailable':12} residency={pr.residency:12} {why}")
    elif a.cmd == "run":
        bench.run([x for x in a.parsers.split(",") if x], [x for x in a.docs.split(",") if x] or None,
                  allow_offshore=a.allow_offshore, force=a.force, tracks=a.tracks, use_llm=not a.no_llm,
                  out_dir=Path(a.out) if a.out else None, corpus=a.corpus or None)
    elif a.cmd == "graph":
        from . import graph
        from .llm import get_llm
        gr = graph.build(a.corpus, a.parser, None if a.no_llm else get_llm())
        print(json.dumps({**gr.stats(), "pending_llm_tasks": gr.meta.get("pending_llm_tasks", 0)}))
        if gr.meta.get("pending_llm_tasks"):
            print("LLM tasks are pending: answer them (scripts/session_tool.py) and run this again.")
        else:
            print(f"wrote {gr.save()}")
    elif a.cmd == "graph-eval":
        from . import graph
        from .bench import GOLD, _jsonl
        qs = []
        for d in corpus.load_manifest(corpus.manifest_path(a.corpus)):
            qs += [q for q in _jsonl(GOLD / d.id / "questions.jsonl") if q.get("answerable", True)]
        cross = [q for q in _jsonl(GOLD / f"{a.corpus}_cross_questions.jsonl") if q.get("answerable", True)]
        g = graph.Graph.load(graph.GRAPH_DIR / f"{a.corpus}.json")
        res = {"single_manual": graph.evaluate(a.corpus, qs, g, a.parser), "cross_manual": graph.evaluate(a.corpus, cross, g, a.parser)}
        for kind, r in res.items():
            for mode, v in r.items():
                print(f"{kind:14} {mode:15} recall@5 {100 * v['recall_at_5']:5.1f}  right manual {100 * v['right_manual_in_top5']:5.1f}  "
                      f"{v['ms_per_question']:6.0f} ms/question  manuals searched {v['manuals_searched_mean']:.2f}  n={v['n']}")
        if a.out:
            Path(a.out).parent.mkdir(parents=True, exist_ok=True)
            Path(a.out).write_text(json.dumps(res, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
