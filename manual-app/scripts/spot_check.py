#!/usr/bin/env python3
"""Blind human spot check of the answer graders.

  export <results_dir> [n] [out.csv]   sample n graded answers (default 20) into a CSV with an empty
                                       `human` column; judge verdicts are kept in a separate key file
  score  <out.csv>                     after filling `human` with correct / partial / incorrect, report how
                                       often each grader (Claude, Jev, the final grade) agrees with the person

The sample takes every Jev-Claude disagreement first, then the lowest-confidence Jev grades, then a random
remainder, so it spends the person's time where the graders are most likely to be wrong.
"""
import csv
import json
import random
import sys
from pathlib import Path

LABELS = ("correct", "partial", "incorrect")


def _grades(results_dir: Path) -> list[dict]:
    out = []
    for r in json.loads((results_dir / "scores.json").read_text()):
        for g in (((r.get("D") or {}).get("answers") or {}).get("grades") or []):
            if g.get("by") != "rule" and g.get("answer"):          # NOT FOUND answers need no human
                out.append({"doc": r["doc"], "parser": r["parser"], **g})
    return out


def export(results_dir: str, n: int = 20, out: str | None = None) -> None:
    gs = _grades(Path(results_dir))
    random.Random(0).shuffle(gs)
    disagree = [g for g in gs if "jev" in g and "claude" in g and g["jev"] != g["claude"]]
    rest = sorted((g for g in gs if g not in disagree), key=lambda g: g.get("confidence", 2.0))
    low = [g for g in rest if g.get("confidence", 2.0) < 0.9]
    other = [g for g in rest if g not in low]
    random.Random(1).shuffle(other)
    pick = (disagree + low + other)[:n]
    random.Random(2).shuffle(pick)                       # do not reveal why an item was picked
    out = Path(out or Path(results_dir) / "spot_check.csv")
    with out.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["item", "doc", "question", "reference", "answer", "human"])
        for i, g in enumerate(pick, 1):
            w.writerow([i, g["doc"], g["question"], g["reference"], g["answer"], ""])
    key = [{"item": i, **{k: g.get(k) for k in ("doc", "parser", "id", "final", "by", "jev", "confidence", "claude")}}
           for i, g in enumerate(pick, 1)]
    out.with_suffix(".key.json").write_text(json.dumps(key, indent=1))
    print(f"wrote {out} ({len(pick)} items; fill the `human` column with {' / '.join(LABELS)}) "
          f"and {out.with_suffix('.key.json')} (judge verdicts; do not open it before grading)")


def score(csv_path: str) -> None:
    p = Path(csv_path)
    human = {int(r["item"]): r["human"].strip().lower() for r in csv.DictReader(p.open())}
    key = {k["item"]: k for k in json.loads(p.with_suffix(".key.json").read_text())}
    bad = [i for i, h in human.items() if h not in LABELS]
    if bad:
        sys.exit(f"items {bad} need a human grade of {' / '.join(LABELS)}")
    # The `claude` field is missing when Claude graded alone; then the final grade is Claude's.
    for name, get in (("Claude", lambda k: k.get("claude") or (k["final"] if k["by"] == "claude" else None)),
                      ("Jev", lambda k: k.get("jev")), ("Final grade", lambda k: k["final"])):
        pairs = [(get(key[i]), h) for i, h in human.items() if get(key[i])]
        if pairs:
            agree = sum(a == h for a, h in pairs)
            print(f"{name:12s} agrees with the person on {agree}/{len(pairs)} ({100 * agree / len(pairs):.0f}%)")


if __name__ == "__main__":
    if len(sys.argv) < 3 or sys.argv[1] not in ("export", "score"):
        sys.exit(__doc__)
    if sys.argv[1] == "export":
        export(sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 20, sys.argv[4] if len(sys.argv) > 4 else None)
    else:
        score(sys.argv[2])
