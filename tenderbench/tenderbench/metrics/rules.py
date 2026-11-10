"""Deterministic pass/fail checks on parser output (ParseBench / olmOCR-Bench style).

Rule types (fields in gold/<doc>/rules.jsonl):
  present     text must appear (fuzzy)                       {text, page?, threshold?}
  absent      text must not appear                           {text, page?}
  order       `before` must appear earlier than `after`      {before, after, page?}
  table_value cell at (row containing `row`, column headed   {page, row, col, value}
              `col`) must equal `value`
  heading     text must be marked up as a heading            {text, page?}
  steps       procedure steps all present, in this order     {steps: [..], page?}
  near        `a` and `b` both present within `window` chars  {a, b, window?, page?}
              (a parameter and its value/unit, a warning and the step it governs)
Each rule also has `id`, `type`, `category` (e.g. clause, table, form, order, ocr, header).
"""
from __future__ import annotations

import re

from rapidfuzz import fuzz

from ..normalize import content_text, extract_tables, norm_text, table_grid

DEFAULT_THRESHOLD = 90.0


def _needle(text: str) -> str:
    """Normalise rule text exactly as parser output is normalised (content_text), so characters that
    the Markdown cleanup removes from output (table pipes, emphasis stars) cannot make a rule unpassable,
    e.g. the shell pipe in `cat filename.gz | gunzip | psql dbname`."""
    return content_text(text)


def _scope(result, rule) -> str:
    return result.page(rule["page"]) if rule.get("page") else result.full_markdown


def _find(needle: str, hay: str, threshold: float):
    """Fuzzy-locate `needle` in `hay` (both normalised). Returns start index or None."""
    if not needle:
        return None
    i = hay.find(needle)
    if i >= 0:
        return i
    if len(needle) > len(hay) * 1.2:
        return None
    al = fuzz.partial_ratio_alignment(needle, hay, score_cutoff=threshold)
    return al.dest_start if al else None


def check_rule(rule: dict, result) -> bool:
    t = rule["type"]
    thr = float(rule.get("threshold", DEFAULT_THRESHOLD))
    scope_md = _scope(result, rule)
    if t in ("present", "absent"):
        found = _find(_needle(rule["text"]), content_text(scope_md), thr) is not None
        return found if t == "present" else not found
    if t == "order":
        hay = content_text(scope_md)
        a = _find(_needle(rule["before"]), hay, thr)
        b = _find(_needle(rule["after"]), hay, thr)
        return a is not None and b is not None and a < b
    if t == "heading":
        target = norm_text(rule["text"])
        for line in scope_md.splitlines():
            m = re.match(r"^\s{0,3}#{1,6}\s+(.*)$", line) or re.match(r"^\s*<h\d[^>]*>(.*?)</h\d>", line, re.I)
            if m and fuzz.ratio(norm_text(re.sub(r"[*_`]", "", m.group(1))), target) >= thr:
                return True
        return False
    if t == "table_value":
        return _table_value(rule, scope_md, thr)
    if t == "steps":
        hay = content_text(scope_md)
        pos = -1
        for step in rule["steps"]:
            i = _find(_needle(step), hay[pos + 1:], thr)
            if i is None:
                return False
            pos = pos + 1 + i
        return True
    if t == "near":
        hay = content_text(scope_md)
        a, b = _needle(rule["a"]), _needle(rule["b"])
        win = int(rule.get("window", 200))
        starts_a = _all_starts(a, hay, thr)
        starts_b = _all_starts(b, hay, thr)
        return any(abs(i - j) <= win for i in starts_a for j in starts_b)
    raise ValueError(f"unknown rule type {t}")


def _all_starts(needle: str, hay: str, thr: float) -> list[int]:
    """Every place `needle` occurs (exact), or the best fuzzy place if it never occurs exactly."""
    out, i = [], hay.find(needle)
    while i >= 0:
        out.append(i)
        i = hay.find(needle, i + 1)
    if not out:
        j = _find(needle, hay, thr)
        if j is not None:
            out.append(j)
    return out


def _table_value(rule: dict, md: str, thr: float) -> bool:
    row_key, col_key, want = norm_text(rule["row"]), norm_text(rule["col"]), norm_text(rule["value"])
    for tab in extract_tables(md):
        grid = [[norm_text(c) for c in r] for r in table_grid(tab)]
        if not grid:
            continue
        cols = [j for j in range(len(grid[0]))
                if any(col_key and fuzz.partial_ratio(col_key, grid[i][j]) >= thr for i in range(min(3, len(grid))))]
        for r in grid:
            if not any(row_key and fuzz.partial_ratio(row_key, c) >= thr for c in r):
                continue
            for j in cols:
                if j < len(r) and want and (r[j] == want or fuzz.partial_ratio(want, r[j]) >= thr):
                    return True
    return False


def score_rules(rules: list[dict], result) -> dict:
    outcomes = {r["id"]: check_rule(r, result) for r in rules}
    by_cat: dict[str, list[bool]] = {}
    for r in rules:
        by_cat.setdefault(r.get("category", r["type"]), []).append(outcomes[r["id"]])
    n = len(outcomes)
    return {
        "pass_rate": (sum(outcomes.values()) / n) if n else None,
        "n": n,
        "by_category": {k: sum(v) / len(v) for k, v in by_cat.items()},
        "failed": [k for k, v in outcomes.items() if not v],
    }
