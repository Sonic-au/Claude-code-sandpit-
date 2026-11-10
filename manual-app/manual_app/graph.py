"""Knowledge graph over a corpus of manuals, and graph-narrowed search across manuals.

Nodes   manual, model, component, refrigerant, tool (shared across manuals, so they link manuals together);
        spec, procedure, fault, safety (belong to one manual).
Edges   manual -covers_model-> model, manual -uses_refrigerant-> refrigerant, manual -has_component-> component,
        manual -has_procedure-> procedure -involves-> component / -uses_tool-> tool,
        manual -has_fault-> fault -involves-> component, component|manual -has_spec-> spec,
        manual -has_warning-> safety -warns_about-> component.
Every node and edge keeps its sources (manual, page, short quote), who proposed it (rules or llm) and a review
status (proposed / accepted / rejected), so a person can check it against the printed page.

Extraction: rules find refrigerants and safety notices; an LLM reads each parsed page for models, components, specs,
procedures and faults, then one more call groups different names for the same component. With
TB_LLM_PROVIDER=session the LLM tasks are queued and answered in a Claude Code session (see scripts/session_tool.py).

Search: `corpus_search` looks for the question's entities in the graph, keeps only the manuals they occur in, and
boosts the pages they were found on, before the usual hybrid text search.
"""
from __future__ import annotations

import json
import re
import time
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from . import bench, extract, retrieve
from .corpus import ROOT, load_manifest, manifest_path
from .llm import LLMRefusal
from .parsers.base import ParseResult

GRAPH_DIR = ROOT / "graph"
SHARED = ("model", "component", "refrigerant", "tool")
REFRIGERANT = re.compile(r"\bR[- ]?(410A|32|22|134a|407C|404A|290|454B)\b", re.I)

PAGE_PROMPT = """Page {page} of the manual "{title}" is below, as parsed text.

List what a service technician would look up on this page. Use names as printed. Skip text that is not English.
- models: model or series numbers this page says the manual covers.
- refrigerants: refrigerant names (e.g. R-410A).
- components: physical parts of the equipment (e.g. compressor, drain hose, reversing valve).
- specs: values a technician needs, each with its parameter, value, unit (omit unit if there is none) and
  applies_to (the component or model it is for).
- procedures: named tasks (e.g. "Air purging with a vacuum pump"), with the components and tools they involve.
- faults: symptoms or error codes, with their causes, remedies and the components involved.
Every item needs a quote: a short phrase (at most 15 words) copied verbatim from the page that supports it.
Return empty lists for anything the page does not have.

PAGE TEXT:
<<<
{text}
>>>"""

_S = {"type": "string"}
_SL = {"type": "array", "items": _S}


def _obj(req: list[str], **props) -> dict:
    return {"type": "object", "additionalProperties": False, "required": req, "properties": props}


PAGE_SCHEMA = _obj(
    ["models", "refrigerants", "components", "specs", "procedures", "faults"],
    models=_SL, refrigerants=_SL,
    components={"type": "array", "items": _obj(["name", "quote"], name=_S, quote=_S)},
    specs={"type": "array", "items": _obj(["parameter", "value", "applies_to", "quote"], parameter=_S, value=_S, unit=_S,
                                          applies_to=_S, quote=_S)},
    procedures={"type": "array", "items": _obj(["name", "components", "tools", "quote"], name=_S, components=_SL,
                                               tools=_SL, quote=_S)},
    faults={"type": "array", "items": _obj(["symptom", "causes", "remedies", "components", "quote"], symptom=_S,
                                           causes=_SL, remedies=_SL, components=_SL, quote=_S)})

ALIAS_PROMPT = """These {kind} names were extracted from several equipment manuals. Group the names that mean the
same thing (spelling, plural, abbreviation or maker-specific wording for the same part), and give each group one
plain canonical name. Names that stand alone need no group. Do not merge parts that are different (for example an
indoor fan and an outdoor fan).

NAMES:
{names}"""
ALIAS_SCHEMA = _obj(["groups"], groups={"type": "array", "items": _obj(["canonical", "aliases"], canonical=_S,
                                                                        aliases=_SL)})


def slug(s: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")
    return re.sub(r"(?<=[a-z]{3})s$", "", s)[:60] or "x"     # crude singular so "drain hoses" meets "drain hose"


@dataclass
class Graph:
    corpus: str
    nodes: dict = field(default_factory=dict)
    edges: dict = field(default_factory=dict)
    meta: dict = field(default_factory=dict)

    def node(self, ntype: str, label: str, doc: str | None = None, page: int | None = None, quote: str = "",
             by: str = "llm", key: str | None = None, **props) -> str:
        nid = f"{ntype}:{key or slug(label)}" if ntype in SHARED or ntype == "manual" else f"{ntype}:{doc}:{key or slug(label)}"
        n = self.nodes.setdefault(nid, {"id": nid, "type": ntype, "label": label.strip(), "aliases": [], "props": {},
                                        "sources": [], "by": by, "status": "proposed"})
        n["props"].update({k: v for k, v in props.items() if v not in (None, "", [])})
        if label.strip().lower() != n["label"].lower() and label.strip() not in n["aliases"]:
            n["aliases"].append(label.strip())
        self._source(n, doc, page, quote)
        return nid

    def edge(self, src: str, etype: str, dst: str, doc: str | None = None, page: int | None = None, quote: str = "",
             by: str = "llm") -> None:
        eid = f"{src}|{etype}|{dst}"
        e = self.edges.setdefault(eid, {"id": eid, "src": src, "type": etype, "dst": dst, "sources": [], "by": by,
                                        "status": "proposed"})
        self._source(e, doc, page, quote)

    @staticmethod
    def _source(item: dict, doc, page, quote) -> None:
        if doc and page is not None and not any(s["doc"] == doc and s["page"] == page for s in item["sources"]):
            item["sources"].append({"doc": doc, "page": page, "quote": (quote or "")[:160]})

    def merge(self, keep: str, drop: str) -> None:
        """Fold node `drop` into `keep` (same thing under another name)."""
        if keep == drop or drop not in self.nodes or keep not in self.nodes:
            return
        k, d = self.nodes[keep], self.nodes.pop(drop)
        k["aliases"] = sorted({*k["aliases"], d["label"], *d["aliases"]} - {k["label"]})
        for s in d["sources"]:
            self._source(k, s["doc"], s["page"], s["quote"])
        for eid in [e for e in self.edges if drop in (self.edges[e]["src"], self.edges[e]["dst"])]:
            e = self.edges.pop(eid)
            src, dst = (keep if e["src"] == drop else e["src"]), (keep if e["dst"] == drop else e["dst"])
            for s in e["sources"] or [{"doc": None, "page": None, "quote": ""}]:
                self.edge(src, e["type"], dst, s["doc"], s["page"], s["quote"], e["by"])

    def stats(self) -> dict:
        by_type = defaultdict(int)
        for n in self.nodes.values():
            by_type[n["type"]] += 1
        manuals_of = lambda n: {s["doc"] for s in n["sources"]}
        shared = [n for n in self.nodes.values() if n["type"] in SHARED and len(manuals_of(n)) > 1]
        return {"nodes": len(self.nodes), "edges": len(self.edges), "by_type": dict(sorted(by_type.items())),
                "shared_across_manuals": len(shared)}

    def to_json(self) -> dict:
        return {"corpus": self.corpus, "meta": {**self.meta, **self.stats()},
                "nodes": sorted(self.nodes.values(), key=lambda n: n["id"]),
                "edges": sorted(self.edges.values(), key=lambda e: e["id"])}

    def save(self, path: Path | None = None) -> Path:
        path = path or GRAPH_DIR / f"{self.corpus}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_json(), indent=1, ensure_ascii=False))
        return path

    @classmethod
    def load(cls, path: Path) -> "Graph":
        d = json.loads(Path(path).read_text())
        return cls(d["corpus"], {n["id"]: n for n in d["nodes"]}, {e["id"]: e for e in d["edges"]}, d.get("meta", {}))


# ------------------------------------------------------------------ build

def _add_page(g: Graph, doc_id: str, manual: str, page: int, data: dict) -> None:
    comp = lambda name, q="": g.node("component", name, doc_id, page, q)
    for m in data.get("models", []):
        g.edge(manual, "covers_model", g.node("model", m, doc_id, page, key=re.sub(r"[^a-z0-9]", "", m.lower())), doc_id, page)
    for r in data.get("refrigerants", []):
        _refrigerant(g, doc_id, manual, page, r, "llm")
    for c in data.get("components", []):
        g.edge(manual, "has_component", comp(c["name"], c.get("quote", "")), doc_id, page, c.get("quote", ""))
    for s in data.get("specs", []):
        label = f"{s['parameter']}: {s['value']}" + (f" {s['unit']}" if s.get("unit") else "")
        sid = g.node("spec", label, doc_id, page, s.get("quote", ""), key=slug(f"{s['parameter']} {s.get('applies_to', '')} {s['value']}"),
                     parameter=s["parameter"], value=s["value"], unit=s.get("unit", ""), applies_to=s.get("applies_to", ""))
        owner = f"component:{slug(s.get('applies_to', ''))}"
        g.edge(owner if owner in g.nodes else manual, "has_spec", sid, doc_id, page, s.get("quote", ""))
    for p in data.get("procedures", []):
        pid = g.node("procedure", p["name"], doc_id, page, p.get("quote", ""))
        g.edge(manual, "has_procedure", pid, doc_id, page, p.get("quote", ""))
        for c in p.get("components", []):
            g.edge(pid, "involves", comp(c), doc_id, page)
            g.edge(manual, "has_component", comp(c), doc_id, page)
        for t in p.get("tools", []):
            g.edge(pid, "uses_tool", g.node("tool", t, doc_id, page), doc_id, page)
    for f in data.get("faults", []):
        fid = g.node("fault", f["symptom"], doc_id, page, f.get("quote", ""), causes=f.get("causes", []),
                     remedies=f.get("remedies", []))
        g.edge(manual, "has_fault", fid, doc_id, page, f.get("quote", ""))
        for c in f.get("components", []):
            g.edge(fid, "involves", comp(c), doc_id, page)
            g.edge(manual, "has_component", comp(c), doc_id, page)


def _refrigerant(g: Graph, doc_id: str, manual: str, page: int, name: str, by: str) -> None:
    m = REFRIGERANT.search(name)
    label = f"R-{m.group(1).upper()}" if m else name.strip()
    g.edge(manual, "uses_refrigerant", g.node("refrigerant", label, doc_id, page, by=by, key=slug(label)), doc_id, page, by=by)


def build(corpus: str, parser: str = "docling", llm=None, log=print) -> Graph:
    g = Graph(corpus, meta={"parser": parser, "built": time.strftime("%Y-%m-%d"), "llm": getattr(llm, "label", None)})
    pending = 0
    for doc in load_manifest(manifest_path(corpus)):
        r = ParseResult.load(bench.output_path(parser, doc.id))
        manual = g.node("manual", doc.title, key=doc.id, by="rules", publisher=doc.publisher if hasattr(doc, "publisher") else None,
                        pages=len(r.page_map), doc=doc.id)
        for md, page in zip(r.pages, r.page_map):
            for m in REFRIGERANT.finditer(md or ""):
                _refrigerant(g, doc.id, manual, page, m.group(0), "rules")
        for i, s in enumerate(extract.extract_safety(r.pages, r.page_map)):
            sid = g.node("safety", s["text"][:90], doc.id, s["page"], s["text"], by="rules", key=f"{i:03d}", kind=s.get("kind"),
                         text=s["text"])
            g.edge(manual, "has_warning", sid, doc.id, s["page"], by="rules")
        if llm is None:
            continue
        for md, page in zip(r.pages, r.page_map):
            if not (md or "").strip():
                continue
            try:
                data = llm.complete_json(PAGE_PROMPT.format(page=page, title=doc.title, text=md), PAGE_SCHEMA, max_tokens=8000)
            except LLMRefusal:
                pending += 1
                continue
            _add_page(g, doc.id, manual, page, data)
        log(f"{doc.id}: graph has {len(g.nodes)} nodes")
    if llm is not None and not pending:
        for kind in ("component", "tool"):
            names = sorted({n["label"] for n in g.nodes.values() if n["type"] == kind})
            if len(names) < 2:
                continue
            try:
                groups = llm.complete_json(ALIAS_PROMPT.format(kind=kind, names="\n".join(names)), ALIAS_SCHEMA, max_tokens=8000)
            except LLMRefusal:
                pending += 1
                continue
            for grp in groups["groups"]:
                keep = g.node(kind, grp["canonical"])
                for a in grp["aliases"]:
                    g.merge(keep, f"{kind}:{slug(a)}")
    # safety notices warn about the components they name
    comps = [(n["id"], [n["label"], *n["aliases"]]) for n in g.nodes.values() if n["type"] == "component"]
    for n in [n for n in g.nodes.values() if n["type"] == "safety"]:
        text = " " + re.sub(r"\W+", " ", n["props"].get("text", "").lower()) + " "
        for cid, names in comps:
            if any(len(x) > 3 and f" {re.sub(r'[^a-z0-9]+', ' ', x.lower()).strip()} " in text for x in names):
                s = n["sources"][0]
                g.edge(n["id"], "warns_about", cid, s["doc"], s["page"], by="rules")
    g.meta["pending_llm_tasks"] = pending
    return g


# ------------------------------------------------------------------ search across manuals

class GraphIndex:
    """Find the graph's entities in a question; return the manuals and pages they point to."""

    def __init__(self, g: Graph):
        self.terms = []
        for n in g.nodes.values():
            if n["type"] not in ("component", "refrigerant", "model", "tool", "fault", "procedure"):
                continue
            for name in [n["label"], *n["aliases"]]:
                t = " ".join(re.findall(r"[a-z0-9]+", name.lower()))
                if len(t) >= 4 and (n["type"] in SHARED or len(t.split()) <= 6):
                    self.terms.append((f" {t} ", n))

    def match(self, question: str) -> tuple[dict, dict, list]:
        q = " " + " ".join(re.findall(r"[a-z0-9]+", question.lower())) + " "
        q2 = re.sub(r"s ", " ", q)                                   # plural-insensitive
        docs, pages, hits = defaultdict(float), defaultdict(float), []
        for t, n in self.terms:
            if t in q or t in q2:
                w = len(t.split())                                    # longer names are more specific
                hits.append(n["id"])
                for s in n["sources"]:
                    docs[s["doc"]] += w
                    pages[(s["doc"], s["page"])] += w
        return dict(docs), dict(pages), sorted(set(hits))


@dataclass
class DocChunk:
    doc: str
    page: int
    text: str
    heading: str
    title: str


def corpus_chunks(corpus: str, parser: str = "docling") -> list[DocChunk]:
    out = []
    for doc in load_manifest(manifest_path(corpus)):
        r = ParseResult.load(bench.output_path(parser, doc.id))
        out += [DocChunk(doc.id, c.page, c.text, c.heading, doc.title) for c in retrieve.chunk_pages(r.pages, r.page_map)]
    return out


def _hybrid(question: str, chunks: list[DocChunk]) -> list[int]:
    texts = [f"{c.title} | {c.heading} | {c.text}" for c in chunks]
    return retrieve._rrf([retrieve._rank_bm25(question, texts), retrieve._rank_dense(question, texts)])


def corpus_search(question: str, chunks: list[DocChunk], index: GraphIndex | None = None) -> tuple[list[DocChunk], dict]:
    """Rank chunks from every manual. With a graph index: keep the manuals the question's entities occur in
    (all manuals if none match), then fuse the text ranking with a ranking of graph-matched pages."""
    if index is None:
        return [chunks[i] for i in _hybrid(question, chunks)], {"manuals_searched": len({c.doc for c in chunks})}
    docs, pages, hits = index.match(question)
    pool = [c for c in chunks if c.doc in docs] if docs else chunks
    order = _hybrid(question, pool)
    if pages:
        by_graph = sorted(range(len(pool)), key=lambda i: -pages.get((pool[i].doc, pool[i].page), 0.0))
        by_graph = [i for i in by_graph if pages.get((pool[i].doc, pool[i].page), 0.0) > 0]
        order = retrieve._rrf([order, order, by_graph + [i for i in order if i not in set(by_graph)]])
    return [pool[i] for i in order], {"manuals_searched": len({c.doc for c in pool}), "entities": hits}


def evaluate(corpus: str, questions: list[dict], g: Graph, parser: str = "docling", k: int = 5) -> dict:
    """Corpus-level retrieval: the question does not say which manual. Hit = an evidence (manual, page) in the top k."""
    chunks, index = corpus_chunks(corpus, parser), GraphIndex(g)
    corpus_search("warm up", chunks)                                  # load the embedding model before timing
    out = {}
    for name, ix in (("text_only", None), ("graph_narrowed", index)):
        hit, doc_hit, secs, searched, rows = 0, 0, 0.0, 0, []
        for q in questions:
            t = time.perf_counter()
            top, info = corpus_search(q["question"], chunks, ix)
            secs += time.perf_counter() - t
            ev = {(e.get("doc", q.get("doc")), e["page"]) for e in q["evidence"]}
            ok = any((c.doc, c.page) in ev for c in top[:k])
            hit += ok
            doc_hit += any(c.doc in {d for d, _ in ev} for c in top[:k])
            searched += info["manuals_searched"]
            rows.append({"id": q.get("id"), "hit": ok, "manuals_searched": info["manuals_searched"],
                         "entities": info.get("entities", [])})
        n = max(1, len(questions))
        out[name] = {"recall_at_5": hit / n, "right_manual_in_top5": doc_hit / n, "ms_per_question": 1000 * secs / n,
                     "manuals_searched_mean": searched / n, "n": len(questions), "questions": rows}
    return out
