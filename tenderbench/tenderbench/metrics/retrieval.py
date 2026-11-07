"""Retrieval and answer metrics for the question track."""
from __future__ import annotations

import re

from ..normalize import norm_text


def recall_at_k(ranked_pages: list[int], evidence_pages: list[int], k: int) -> float:
    """1.0 if any gold evidence page is among the pages of the top-k chunks."""
    return 1.0 if set(ranked_pages[:k]) & set(evidence_pages) else 0.0


def reciprocal_rank(ranked_pages: list[int], evidence_pages: list[int]) -> float:
    ev = set(evidence_pages)
    for i, p in enumerate(ranked_pages, 1):
        if p in ev:
            return 1.0 / i
    return 0.0


def token_f1(pred: str, gold: str) -> float:
    """SQuAD-style token F1 between an answer and the gold short answer."""
    pt = re.findall(r"\w+", norm_text(pred))
    gt = re.findall(r"\w+", norm_text(gold))
    if not pt or not gt:
        return float(pt == gt)
    common = {}
    for t in pt:
        if t in gt:
            common[t] = min(pt.count(t), gt.count(t))
    same = sum(common.values())
    if same == 0:
        return 0.0
    p, r = same / len(pt), same / len(gt)
    return 2 * p * r / (p + r)


def contains_answer(pred: str, gold: str) -> bool:
    """Lenient check: every number and key word of a short gold answer appears in the prediction."""
    p = norm_text(pred)
    toks = [t for t in re.findall(r"[\w%$.]+", norm_text(gold)) if len(t) > 2 or any(c.isdigit() for c in t)]
    return bool(toks) and all(t in p for t in toks)
