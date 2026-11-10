"""Tree-Edit-Distance-based Similarity (TEDS) for tables.

Follows Zhong et al., "Image-based table recognition: data, model, and evaluation"
(arXiv 1911.10683): a table is a tree (table > tr > td); renaming a cell costs 1 if its
tag or spans differ, else the normalised edit distance of its text. TEDS = 1 - distance /
max(nodes). `structure_only=True` gives TEDS-S, which ignores cell text.
"""
from __future__ import annotations

from apted import APTED, Config
from lxml import html as lxml_html
from rapidfuzz.distance import Levenshtein


class _Node:
    __slots__ = ("tag", "colspan", "rowspan", "content", "children")

    def __init__(self, tag, colspan=1, rowspan=1, content="", children=None):
        self.tag, self.colspan, self.rowspan, self.content = tag, colspan, rowspan, content
        self.children = children or []


class _Cfg(Config):
    def __init__(self, structure_only: bool):
        self.structure_only = structure_only

    def rename(self, a, b):
        if a.tag != b.tag or a.colspan != b.colspan or a.rowspan != b.rowspan:
            return 1.0
        if a.tag in ("td", "th") and not self.structure_only:
            if not a.content and not b.content:
                return 0.0
            return Levenshtein.normalized_distance(a.content, b.content)
        return 0.0

    def children(self, n):
        return n.children


def _tree(table_html: str) -> _Node | None:
    try:
        root = lxml_html.fromstring(table_html)
    except Exception:
        return None
    table = root if root.tag == "table" else root.find(".//table")
    if table is None:
        return None
    rows = []
    for tr in table.iter("tr"):
        cells = []
        for c in tr:
            if c.tag in ("td", "th"):
                # th vs td is presentation; score both as td so header styling is not penalised twice.
                cells.append(_Node("td", int(c.get("colspan", 1)), int(c.get("rowspan", 1)),
                                   " ".join(c.text_content().lower().split())))
        rows.append(_Node("tr", children=cells))
    return _Node("table", children=rows)


def _count(n: _Node) -> int:
    return 1 + sum(_count(c) for c in n.children)


def teds(pred_html: str, gold_html: str, structure_only: bool = False) -> float:
    g = _tree(gold_html)
    p = _tree(pred_html) if pred_html else None
    if g is None:
        raise ValueError("gold table could not be parsed")
    if p is None:
        return 0.0
    dist = APTED(p, g, _Cfg(structure_only)).compute_edit_distance()
    return max(0.0, 1.0 - dist / max(_count(p), _count(g)))


def best_teds(pred_tables: list[str], gold_html: str, structure_only: bool = False) -> float:
    """Score a gold table against its best-matching predicted table on the same page."""
    return max((teds(p, gold_html, structure_only) for p in pred_tables), default=0.0)
