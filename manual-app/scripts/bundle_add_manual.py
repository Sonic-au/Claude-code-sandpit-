#!/usr/bin/env python3
"""Write a single-file copy of scripts/add_manual.py that runs without this repository.

  python scripts/bundle_add_manual.py <out_file>

The hourly task that fetches requested manuals starts with no repository attached, so the app carries this copy
(published beside it as tools/add_manual.txt). It inlines the chunker and the figure finder; behaviour is the same.
"""
import inspect
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import add_manual  # noqa: E402
import export_figures  # noqa: E402
from manual_app import normalize, retrieve  # noqa: E402


def main() -> None:
    src = (ROOT / "scripts" / "add_manual.py").read_text()
    head, rest = src.split("ROOT = Path(__file__)", 1)
    body = rest.split("MAX_BYTES", 1)[1]
    head = head.replace("Needs only pymupdf4llm, pyyaml and lxml (no PyTorch); the bundled single-file copy needs only the first two", "Single-file copy (made by bundle_add_manual.py). Needs only pymupdf4llm and pyyaml (no PyTorch)")
    parts = [head.rstrip(), "import html\nfrom dataclasses import dataclass\n",
             "_BULLETS = " + f're.compile(r"""{normalize._BULLETS.pattern}""", re.M)',
             inspect.getsource(normalize.markdown_to_text), inspect.getsource(retrieve.Chunk), inspect.getsource(retrieve.chunk_pages),
             f"MAX_PER_PAGE = {export_figures.MAX_PER_PAGE}", inspect.getsource(export_figures._merge), inspect.getsource(export_figures.page_figures),
             "MAX_BYTES" + body]
    out = Path(sys.argv[1])
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n\n".join(p.rstrip() for p in parts) + "\n")
    compile(out.read_text(), str(out), "exec")
    assert add_manual.MAX_BYTES and not re.search(r"^from (manual_app|export_figures)", out.read_text(), re.M)
    print(f"wrote {out} ({out.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
