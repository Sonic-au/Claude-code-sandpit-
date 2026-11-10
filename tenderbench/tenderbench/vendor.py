"""Gold that does not come from our own annotators: vendor websites and an external benchmark.

`python -m tenderbench vendor` regenerates everything below from `corpus/vendor_sources.yaml`.

1. HTML manual (`kind: html_manual`): the vendor publishes the same manual as HTML. Code blocks, headings,
   admonitions and heading order become rules, each mapped to the bench page whose PDF text layer holds it.
   -> gold/<doc>/vendor_rules.jsonl
2. Product/spec page (`kind: spec_page`): the vendor's own parameter list. Each value is located in the manual;
   found values become a rule anchored to the manual's wording plus a technician question; values the manual
   does not contain are recorded as possible manual/website mismatches.
   -> gold/<doc>/vendor_rules.jsonl, vendor_questions.jsonl, vendor_mismatches.json
3. TechManualQA-700 (CC BY 4.0, Duricic et al.): its questions become Track D gold, and each answer snippet that
   is verified on its stated page becomes a `present` rule (the parser must keep the text the answer needs).
   -> gold/<doc>/questions.jsonl, vendor_rules.jsonl

Raw snapshots go to data/vendor/ with URL, date and SHA-256 (not committed); only derived gold is committed.
Fetches use a named client and only the listed pages.
"""
from __future__ import annotations

import hashlib
import json
import re
import time
import urllib.request
from pathlib import Path

import pypdf
import yaml
from lxml import html as LH
from rapidfuzz import fuzz

from .corpus import CORPORA, DATA, USER_AGENT, get_document
from .normalize import norm_text

GOLD = CORPORA.parent / "gold"
SNAP = DATA / "vendor"
SOURCES = CORPORA / "vendor_sources.yaml"


# ------------------------------------------------------------------ snapshots

def snapshot(url: str, name: str) -> tuple[bytes, dict]:
    """Fetch once and keep the bytes with their provenance; later runs reuse the snapshot."""
    SNAP.mkdir(parents=True, exist_ok=True)
    body_p, meta_p = SNAP / name, SNAP / (name + ".meta.json")
    if body_p.exists() and meta_p.exists():
        return body_p.read_bytes(), json.loads(meta_p.read_text())
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=120) as r:
        body = r.read()
    meta = {"url": url, "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "sha256": hashlib.sha256(body).hexdigest(), "bytes": len(body)}
    body_p.write_bytes(body)
    meta_p.write_text(json.dumps(meta, indent=1))
    return body, meta


def _slug(url: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", url.split("://", 1)[-1])[-120:]


def _layer(doc_id: str, full_source: bool = False) -> dict[int, str]:
    """Normalised text layer per original page (bench pages, or every page of the source PDF)."""
    d = get_document(doc_id)
    if full_source:
        r = pypdf.PdfReader(str(d.source_pdf))
        return {i + 1: norm_text(p.extract_text() or "") for i, p in enumerate(r.pages)}
    r = pypdf.PdfReader(str(d.bench_pdf))
    return {pg: norm_text(r.pages[i].extract_text() or "") for i, pg in enumerate(d.page_map())}


def _locate(text: str, layer: dict[int, str], thr: float = 92) -> int | None:
    t = norm_text(text)
    if len(t) < 6:
        return None
    best = max(layer, key=lambda p: fuzz.partial_ratio(t, layer[p]), default=None)
    return best if best is not None and fuzz.partial_ratio(t, layer[best]) >= thr else None


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))


# ------------------------------------------------------------------ 1. HTML manual

def html_manual_rules(doc_id: str, urls: list[str], prefix: str) -> dict:
    layer = _layer(doc_id)
    rules, provenance, n = [], [], 0

    def add(rule):
        nonlocal n
        n += 1
        rules.append({"id": f"{prefix}-v{n:03d}", **rule})

    for url in urls:
        body, meta = snapshot(url, _slug(url))
        provenance.append(meta)
        root = LH.fromstring(body.decode("utf-8", "replace"))
        main = (root.xpath('//div[@id="docContent"]') or [root])[0]
        for nav in main.xpath('.//div[contains(@class,"navheader") or contains(@class,"navfooter")]'):
            nav.getparent().remove(nav)
        last_heading = None
        for el in main.iter():
            tag = el.tag if isinstance(el.tag, str) else ""
            if tag in ("h1", "h2", "h3"):
                text = " ".join(el.text_content().replace(" ", " ").replace("#", "").split())
                pg = _locate(text, layer)
                in_notice = any("admon" in (a.get("class") or "") or
                                any(c in (a.get("class") or "").split() for c in ("important", "note", "warning", "tip", "caution"))
                                for a in el.iterancestors())
                if pg is None or in_notice:
                    continue
                add({"type": "heading", "page": pg, "category": "vendor_heading", "text": text, "source": url})
                if last_heading and last_heading[1] == pg:
                    add({"type": "order", "page": pg, "category": "vendor_order", "before": last_heading[0],
                         "after": text, "source": url})
                last_heading = (text, pg)
            elif tag == "pre":
                lines = [l.strip() for l in el.text_content().splitlines() if len(l.strip()) >= 8]
                for line in lines[:2]:
                    pg = _locate(line, layer, thr=95)
                    if pg is not None:
                        add({"type": "present", "page": pg, "category": "vendor_code", "text": line, "source": url})
            elif tag == "div" and any(c in (el.get("class") or "").split() for c in
                                       ("important", "note", "warning", "tip", "caution")):
                kind = next(c for c in ("important", "note", "warning", "tip", "caution") if c in el.get("class").split())
                paras = [" ".join(p.text_content().split()) for p in el.xpath(".//p")]
                body_txt = " ".join(paras) or " ".join(el.text_content().split())
                first = re.split(r"(?<=[.!?])\s", body_txt)[0][:220]
                pg = _locate(first, layer)
                if pg is not None:
                    add({"type": "present", "page": pg, "category": "vendor_notice", "text": first,
                         "notice": kind, "source": url})
    _write_jsonl(GOLD / doc_id / "vendor_rules.jsonl", rules)
    return {"doc": doc_id, "kind": "html_manual", "rules": len(rules), "sources": provenance}


# ------------------------------------------------------------------ 2. spec page

_PARAM = re.compile(r"([A-Z][A-Za-z0-9 ()/.,θ-]{1,60}?) \(([^()]{1,12})\) (-?\d+(?:\.\d+)?(?: to -?\d+(?:\.\d+)?)?)")
_UNIT_ALIASES = {"°C": ["°c", "c"], "µVrms": ["µvrms", "uvrms", "μvrms"], "°C/W": ["°c/w", "c/w"]}


def _value_patterns(value: str, unit: str) -> list[str]:
    units = [unit.lower()] + _UNIT_ALIASES.get(unit, [])
    vals = [value] + ([value[:-2]] if value.endswith(".0") else [])
    pats = []
    for v in vals:
        for u in units:
            pats += [f"{v} {u}", f"{v}{u}"]
    return [norm_text(p) for p in pats]


def spec_page_rules(doc_id: str, url: str, product: str, prefix: str) -> dict:
    body, meta = snapshot(url, _slug(url))
    txt = " ".join(LH.fromstring(body.decode("utf-8", "replace")).text_content().split())
    start = txt.find("Product details")
    block = txt[start:start + 1500] if start >= 0 else txt
    params, seen = [], set()
    for name, unit, value in _PARAM.findall(block):
        name = name.replace("Product details", "").replace("Rating Catalog", "").strip()
        name = re.sub(r"^.*Fixed Output ", "", name)   # "Output options Adjustable Output, Fixed Output" is not a spec
        # Package rows ("TO-263 (KTT) 3 ...") follow the parameter list and are not specs.
        if name in seen or unit == "#" or re.fullmatch(r"[A-Z]{3}", unit) or (" to " in value and unit != "°C"):
            continue
        seen.add(name)
        params.append((name, unit, value))
    bench, full = _layer(doc_id), _layer(doc_id, full_source=True)
    rules, questions, mismatches = [], [], []
    for k, (name, unit, value) in enumerate(params, 1):
        pats = _value_patterns(value, unit)
        hits = {p: [m.start() for pat in pats for m in re.finditer(r"(?<![0-9.])" + re.escape(pat) + r"(?![0-9])", t)]
                for p, t in bench.items()}
        hits = {p: v for p, v in hits.items() if v}
        if not hits:
            elsewhere = [p for p, t in full.items()
                         if any(re.search(r"(?<![0-9.])" + re.escape(pat) + r"(?![0-9])", t) for pat in pats)]
            mismatches.append({"parameter": name, "unit": unit, "website_value": value,
                               "status": "on non-bench pages" if elsewhere else "not stated in the manual in this form",
                               "pages": elsewhere[:10]})
            continue
        pg = min(hits)
        i = hits[pg][0]
        t = bench[pg]
        snippet = t[max(0, t.rfind(" ", 0, max(0, i - 45)) + 1): t.find(" ", min(len(t), i + 45)) if t.find(" ", min(len(t), i + 45)) > 0 else len(t)]
        rules.append({"id": f"{prefix}-v{k:03d}", "type": "present", "page": pg, "category": "vendor_spec",
                      "text": snippet.strip(), "parameter": name, "website_value": f"{value} {unit}", "source": url})
        questions.append({"id": f"{prefix}-vq{k:02d}", "doc": doc_id,
                          "question": f"What is the {name} of the {product}?",
                          "answer": f"{value} {unit}", "evidence": [{"page": p} for p in sorted(hits)],
                          "answerable": True, "type": "spec", "source": url})
    _write_jsonl(GOLD / doc_id / "vendor_rules.jsonl", rules)
    _write_jsonl(GOLD / doc_id / "vendor_questions.jsonl", questions)
    (GOLD / doc_id / "vendor_mismatches.json").write_text(json.dumps(
        {"source": meta, "parameters_on_page": len(params), "mismatches": mismatches}, indent=1, ensure_ascii=False))
    return {"doc": doc_id, "kind": "spec_page", "parameters": len(params), "rules": len(rules),
            "questions": len(questions), "mismatches": mismatches, "source": meta}


# ------------------------------------------------------------------ 3. TechManualQA-700

TMQA_URL = "https://zenodo.org/api/records/17410809/files/TechManualQA_700.zip/content"


def techmanualqa(doc_id: str, tmqa_doc: str, prefix: str) -> dict:
    import io
    import zipfile
    body, meta = snapshot(TMQA_URL, "TechManualQA_700.zip")
    z = zipfile.ZipFile(io.BytesIO(body))
    rows = [json.loads(l) for l in z.read("TechManualQA_700/TechManualQA_700.jsonl").decode().splitlines() if l.strip()]
    rows = [r for r in rows if r["doc_id"] == tmqa_doc]
    layer = _layer(doc_id)
    questions, rules, verified = [], [], 0
    for r in rows:
        unans = r["category"] == "Unanswerable"
        try:
            pg = int(r["gt_page_number"])
        except (TypeError, ValueError):
            pg = None
        snippet = r.get("gt_answer_snippet") or ""
        q = {"id": f"{prefix}-{r['question_id'].split('_Q')[-1]}", "doc": doc_id, "question": r["question_text"],
             "answer": "" if unans else snippet, "evidence": [] if unans or pg is None else [{"page": pg}],
             "answerable": not unans, "type": r["category"], "source": "TechManualQA-700 " + r["question_id"]}
        questions.append(q)
        if not unans and pg in layer and len(norm_text(snippet)) >= 6 and \
                fuzz.partial_ratio(norm_text(snippet), layer[pg]) >= 90:
            verified += 1
            rules.append({"id": q["id"] + "-snip", "type": "present", "page": pg, "category": "tmqa_snippet",
                          "text": snippet[:300], "source": q["source"]})
    _write_jsonl(GOLD / doc_id / "questions.jsonl", questions)
    _write_jsonl(GOLD / doc_id / "vendor_rules.jsonl", rules)
    return {"doc": doc_id, "kind": "techmanualqa", "questions": len(questions),
            "answerable": sum(q["answerable"] for q in questions), "snippets_verified_on_page": verified,
            "source": meta}


# ------------------------------------------------------------------ driver

def build_all() -> list[dict]:
    from .corpus import build
    cfg = yaml.safe_load(SOURCES.read_text())
    out = []
    for s in cfg["sources"]:
        d = get_document(s["doc"])
        if not d.bench_pdf.exists():
            build(d)
        if s["kind"] == "html_manual":
            out.append(html_manual_rules(s["doc"], s["urls"], s["prefix"]))
        elif s["kind"] == "spec_page":
            out.append(spec_page_rules(s["doc"], s["url"], s["product"], s["prefix"]))
        elif s["kind"] == "techmanualqa":
            out.append(techmanualqa(s["doc"], s["tmqa_doc"], s["prefix"]))
    (GOLD / "vendor_summary.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))
    return out
