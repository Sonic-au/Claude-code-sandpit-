#!/usr/bin/env python3
"""Build the data file for the technician Q&A app from a workbench export.

  python scripts/export_workbench.py <workbench_dir>      # parsed pages, chunks, questions, page images
  python scripts/export_app.py <workbench_dir> <app_dir>  # data.json for the app (page images are shared)

The app needs each manual's parsed page text, search passages and a few example questions. It does not get the
expected answers, Claude's test answers, grades or the knowledge graph.
"""
import json
import sys
from pathlib import Path


def main() -> None:
    src, out = Path(sys.argv[1]), Path(sys.argv[2])
    d = json.loads((src / "data.json").read_text())
    manuals = []
    for m in d["manuals"]:
        if m["id"].endswith("_scan"):          # the simulated scan repeats pages of another manual
            continue
        examples = [q["question"] for q in m["questions"] if q.get("answerable", True)][:4]
        manuals.append({"id": m["id"], "corpus": m["corpus"], "title": m["title"], "pages": m["pages"],
                        "page_text": m["page_text"], "chunks": m["chunks"], "examples": examples})
    out.mkdir(parents=True, exist_ok=True)
    data = {"parser": d["parser"], "answer_prompt": d["answer_prompt"], "manuals": manuals}
    (out / "data.json").write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")))
    print(f"wrote {out / 'data.json'}: {len(manuals)} manuals, {sum(len(m['pages']) for m in manuals)} pages, "
          f"{(out / 'data.json').stat().st_size // 1024} KB")


if __name__ == "__main__":
    main()
