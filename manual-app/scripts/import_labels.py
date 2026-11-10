#!/usr/bin/env python3
"""Import questions labelled in the Manual Handling Workbench into the gold test set.

  python scripts/import_labels.py <labels_dir> [--dry-run]

<labels_dir> holds one JSON file per saved label, as exported from the workbench's `labels` collection.
Each label is appended to gold/<doc>/questions.jsonl with a new id (<prefix>-wbNN, the prefix taken from the
manual's existing question ids) unless the same question is already there. Run `python -m manual_app.validate_gold`
afterwards to check the new questions against the parsed pages and rebuild gold/questions.jsonl.
"""
import argparse
import json
import re
import sys
from pathlib import Path

GOLD = Path(__file__).resolve().parent.parent / "gold"


def _norm(s: str) -> str:
    return re.sub(r"\W+", " ", s.lower()).strip()


def load_labels(d: Path) -> list[dict]:
    out = []
    for f in sorted(d.rglob("*.json")):
        raw = json.loads(f.read_text())
        rec = raw.get("data") if isinstance(raw.get("data"), dict) else raw   # a document file or a bare record
        rec = dict(rec, _source_id=raw.get("id") or f.stem)
        out.append(rec)
    return out


def to_question(label: dict, qid: str) -> dict:
    answerable = bool(label.get("answerable", True))
    return {"id": qid, "doc": label["doc"], "question": label["question"].strip(),
            "answer": label.get("answer", "").strip() if answerable else "",
            "evidence": [{"page": int(p)} for p in label.get("evidence", [])] if answerable else [],
            "answerable": answerable, "type": label.get("type") or ("spec" if answerable else "unanswerable"),
            "source": "workbench", "workbench_id": label["_source_id"]}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("labels_dir")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    added, skipped = 0, []
    for label in load_labels(Path(a.labels_dir)):
        doc = label.get("doc", "")
        qfile = GOLD / doc / "questions.jsonl"
        if not doc or not qfile.parent.is_dir():
            skipped.append(f"{label['_source_id']}: unknown manual {doc!r}")
            continue
        if not label.get("question", "").strip() or (label.get("answerable", True) and not label.get("evidence")):
            skipped.append(f"{label['_source_id']}: missing question or evidence pages")
            continue
        existing = [json.loads(l) for l in qfile.read_text().splitlines() if l.strip()] if qfile.exists() else []
        if any(_norm(q["question"]) == _norm(label["question"]) or q.get("workbench_id") == label["_source_id"]
               for q in existing):
            skipped.append(f"{label['_source_id']}: already in {doc}")
            continue
        prefix = existing[0]["id"].rsplit("-", 1)[0] if existing else doc[:3]
        n = 1 + max([int(m.group(1)) for q in existing if (m := re.search(r"-wb(\d+)$", q["id"]))] or [0])
        q = to_question(label, f"{prefix}-wb{n:02d}")
        if not a.dry_run:
            with qfile.open("a") as f:
                f.write(json.dumps(q, ensure_ascii=False) + "\n")
        added += 1
        print(("would add " if a.dry_run else "added ") + f"{q['id']}: {q['question']}")
    for s in skipped:
        print("skipped", s)
    print(f"{added} added, {len(skipped)} skipped")
    sys.exit(0)


if __name__ == "__main__":
    main()
