"""Command line: `python -m tenderbench <command>`."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import bench, corpus
from .parsers import FACTORIES, get_parser

LOCAL_DEFAULT = ["pypdf-text", "pymupdf4llm", "liteparse", "docling"]


def main(argv=None):
    ap = argparse.ArgumentParser(prog="tenderbench", description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("fetch", help="download source PDFs and build the bench PDFs")
    sub.add_parser("parsers", help="list parser adapters and whether they can run here")

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

    a = ap.parse_args(argv)
    if a.cmd == "fetch":
        for d in corpus.load_manifest():
            corpus.build(d)
            print(f"{d.id}: {len(d.page_map())} pages -> {d.bench_pdf}")
    elif a.cmd == "parsers":
        for name in FACTORIES:
            pr = get_parser(name)
            ok, why = pr.available()
            print(f"{name:22} {'ready' if ok else 'unavailable':12} residency={pr.residency:12} {why}")
    elif a.cmd == "run":
        bench.run([x for x in a.parsers.split(",") if x], [x for x in a.docs.split(",") if x] or None,
                  allow_offshore=a.allow_offshore, force=a.force, tracks=a.tracks, use_llm=not a.no_llm,
                  out_dir=Path(a.out) if a.out else None)
    return 0


if __name__ == "__main__":
    sys.exit(main())
