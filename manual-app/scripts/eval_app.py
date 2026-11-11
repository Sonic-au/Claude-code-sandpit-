#!/usr/bin/env python3
"""Measure the technician app's accuracy on the test questions.

  python scripts/eval_app.py <out_dir> [--mode single|all|both]

Reproduces what web/app/index.html does: keyword (BM25) search over the parsed passages, the top 8 passages,
the bench's answer prompt, then Claude's answer. `single` searches the question's own manual (the app with a
manual picked); `all` searches every manual at once (the app's "All manuals"). Answers are graded like the bench
(TB_JUDGE: claude, jev, cascade or compare). With TB_LLM_PROVIDER=session, run it, answer the queued tasks
(scripts/session_tool.py) and run it again until nothing is pending.
"""
import argparse
import json
import math
import os
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("TB_LLM_PROVIDER", "session")

from manual_app import bench, retrieve  # noqa: E402
from manual_app.corpus import load_manifest, manifest_path  # noqa: E402
from manual_app.judge import Grader, Jev, JevError  # noqa: E402
from manual_app.llm import LLMRefusal, get_llm  # noqa: E402
from manual_app.metrics import contains_answer  # noqa: E402
from manual_app.parsers.base import ParseResult  # noqa: E402

K = 8


class CachedJev(Jev):
    """Jev's confidences vary slightly between calls, which would send a different few grades to Claude on each
    re-run. Cache each verdict by request so a re-run grades exactly as before (data/session_llm/jev_cache.json)."""

    PATH = ROOT / "data" / "session_llm" / "jev_cache.json"

    def __init__(self):
        super().__init__()
        self.cache = json.loads(self.PATH.read_text()) if self.PATH.exists() else {}

    def grade(self, question, gold, answer, title):
        key = json.dumps([self.model, title, question, gold, answer])
        if key not in self.cache:
            self.cache[key] = list(super().grade(question, gold, answer, title))
            self.PATH.parent.mkdir(parents=True, exist_ok=True)
            self.PATH.write_text(json.dumps(self.cache))
        return tuple(self.cache[key])
CORPORA = ("manuals", "techmanualqa", "hvac")
TOK = re.compile(r"[a-z0-9]+(?:[.%][0-9]+)?")


def short(title: str) -> str:
    return re.sub(r"\s*\(.*?\)\s*", " ", title).split(" - ")[0].strip()


class Index:
    """The app's in-browser BM25, ported line for line (same tokens, k1, b, IDF floor and tie order)."""

    def __init__(self, chunks: list[dict]):
        self.chunks = chunks
        self.docs = [TOK.findall(f"{c['title']} | {c['heading']} | {c['text']}".lower()) for c in chunks]
        df = Counter(t for d in self.docs for t in set(d))
        n = len(self.docs)
        self.avg = sum(len(d) for d in self.docs) / max(1, n)
        self.idf = {t: max(0.05, math.log((n - f + 0.5) / (f + 0.5))) for t, f in df.items()}
        self.tfs = [Counter(d) for d in self.docs]

    def search(self, q: str) -> list[dict]:
        qt = list(dict.fromkeys(TOK.findall(q.lower())))
        scored = []
        for i, f in enumerate(self.tfs):
            s = sum(self.idf.get(t, 0) * (f[t] * 2.5) / (f[t] + 1.5 * (0.25 + 0.75 * len(self.docs[i]) / self.avg))
                    for t in qt if f.get(t))
            if s > 0:
                scored.append((s, i))
        scored.sort(key=lambda x: -x[0])
        return [self.chunks[i] for _, i in scored[:K]]


def load() -> tuple[list[dict], dict, list[dict]]:
    chunks, titles, questions = [], {}, []
    for corpus in CORPORA:
        for doc in load_manifest(manifest_path(corpus)):
            if doc.id.endswith("_scan"):
                continue
            r = ParseResult.load(bench.output_path("docling", doc.id))
            titles[doc.id] = doc.title
            chunks += [{"doc": doc.id, "title": doc.title, "page": c.page, "heading": c.heading, "text": c.text}
                       for c in retrieve.chunk_pages(r.pages, r.page_map)]
            questions += [dict(q, doc=doc.id, corpus=corpus) for q in bench.load_gold(doc)["questions"]]
    return chunks, titles, questions


def prompt_for(mode: str, q: dict, top: list[dict], titles: dict) -> str:
    if mode == "all":
        title = "the equipment manuals named in each extract"
        ex = "\n\n".join(f"[{i + 1}] ({short(c['title'])}, page {c['page']}) {c['text']}" for i, c in enumerate(top))
        tmpl = retrieve.ANSWER_PROMPT.replace('the document "{title}"', title)
    else:
        title = titles[q["doc"]]
        ex = "\n\n".join(f"[{i + 1}] (page {c['page']}) {c['text']}" for i, c in enumerate(top))
        tmpl = retrieve.ANSWER_PROMPT
    return tmpl.replace("{title}", title).replace("{question}", q["question"]).replace("{extracts}", ex)


def run(mode: str, chunks, titles, questions, llm, grader) -> dict:
    by_doc = defaultdict(list)
    for c in chunks:
        by_doc[c["doc"]].append(c)
    indexes = {"all": Index(chunks)} if mode == "all" else {d: Index(cs) for d, cs in by_doc.items()}
    rows, pending = [], 0
    for q in questions:
        top = indexes["all" if mode == "all" else q["doc"]].search(q["question"])
        ev = {(q["doc"], e["page"]) for e in q.get("evidence", [])}
        row = {"id": q["id"], "doc": q["doc"], "corpus": q["corpus"], "answerable": q.get("answerable", True),
               "question": q["question"], "reference": q.get("answer", ""),
               "retrieved": [[c["doc"], c["page"]] for c in top],
               "evidence_retrieved": bool(ev & {(c["doc"], c["page"]) for c in top}) if ev else None}
        if not top:
            row.update(answer="", status="no_match")          # the app shows "No passage matches" without asking Claude
        else:
            try:
                ans = llm.complete(prompt_for(mode, q, top, titles), max_tokens=800).strip()
            except LLMRefusal:
                pending += 1
                row.update(answer=None, status="pending")
                rows.append(row)
                continue
            cited = [top[int(n) - 1] for n in re.findall(r"\[(\d+)\]", ans) if 0 < int(n) <= len(top)]
            row.update(answer=ans, status="answered", cited=sorted({(c["doc"], c["page"]) for c in cited}),
                       cited_evidence=bool(ev & {(c["doc"], c["page"]) for c in cited}) if ev else None)
        not_found = not row["answer"] or row["answer"].upper().startswith("NOT FOUND")
        row["not_found"] = not_found
        if row["answerable"]:
            row["strict"] = bool(row["answer"]) and contains_answer(row["answer"], q["answer"])
            try:
                row["grade"] = grader.grade(q["question"], q["answer"], row["answer"] or "", titles[q["doc"]])
            except (LLMRefusal, JevError) as e:
                pending += isinstance(e, LLMRefusal)
                row["grade"] = None
        rows.append(row)
    return {"mode": mode, "pending": pending, "rows": rows, "summary": summarise(rows)}


def summarise(rows: list[dict]) -> dict:
    def agg(rs):
        ans = [r for r in rs if r["answerable"]]
        graded = [r for r in ans if r.get("grade")]
        un = [r for r in rs if not r["answerable"] and r.get("answer") is not None]
        pct = lambda a, b: round(100 * a / b, 1) if b else None
        return {"answerable": len(ans), "graded": len(graded),
                "correct": sum(r["grade"]["final"] == "correct" for r in graded),
                "partial": sum(r["grade"]["final"] == "partial" for r in graded),
                "judged_accuracy": pct(sum(r["grade"]["final"] == "correct" for r in graded), len(graded)),
                "strict_accuracy": pct(sum(bool(r.get("strict")) for r in graded), len(graded)),
                "not_found": sum(bool(r.get("not_found")) for r in graded),
                "evidence_in_top8": pct(sum(bool(r["evidence_retrieved"]) for r in ans), len(ans)),
                "cited_evidence_page": pct(sum(bool(r.get("cited_evidence")) for r in graded), len(graded)),
                "unanswerable": len(un), "abstained": sum(bool(r.get("not_found")) for r in un),
                "escalated_to_claude": sum(r["grade"].get("by") == "claude" for r in graded)}
    out = {"overall": agg(rows)}
    for key in ("corpus", "doc"):
        groups = defaultdict(list)
        for r in rows:
            groups[r[key]].append(r)
        out["by_" + key] = {k: agg(v) for k, v in groups.items()}
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--mode", default="both", choices=["single", "all", "both"])
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    chunks, titles, questions = load()
    llm = get_llm()
    mode = os.environ.get("TB_JUDGE", "claude")
    grader = Grader(llm, jev=CachedJev() if mode != "claude" else None)
    for mode in (["single", "all"] if a.mode == "both" else [a.mode]):
        res = run(mode, chunks, titles, questions, llm, grader)
        res["grader"] = grader.label
        (out / f"app_eval_{mode}.json").write_text(json.dumps(res, indent=1, default=str))
        o = res["summary"]["overall"]
        print(f"{mode:6} pending {res['pending']:3} | graded {o['graded']}/{o['answerable']} correct {o['correct']} "
              f"({o['judged_accuracy']}%) partial {o['partial']} not-found {o['not_found']} | evidence in top 8 "
              f"{o['evidence_in_top8']}% | abstained {o['abstained']}/{o['unanswerable']}")
    if grader.jev:
        print("jev usage", grader.jev.usage)


if __name__ == "__main__":
    main()
