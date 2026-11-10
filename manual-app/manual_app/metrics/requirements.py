"""Requirement-extraction scoring against a hand-built compliance matrix (RealDocBench-style).

Each gold requirement: {id, page, text, obligation, category}. Predictions have the same
shape. A prediction matches a gold item when their normalised texts are similar enough
(one-to-one, best pairs first). Recall on mandatory items is reported separately, and
`all_mandatory_found` is the strict per-document check a bid manager cares about: one
missed mandatory requirement can make a bid non-compliant.
"""
from __future__ import annotations

from rapidfuzz import fuzz

from ..normalize import norm_text

MATCH_THRESHOLD = 80.0
OBLIGATIONS = ("mandatory", "evaluated", "administrative", "informational")


def _sim(a: str, b: str) -> float:
    a, b = norm_text(a), norm_text(b)
    if not a or not b:
        return 0.0
    # token_set handles a prediction that wraps the gold text with extra words; the length
    # penalty stops one long paragraph from "matching" every requirement inside it.
    ts = fuzz.token_set_ratio(a, b)
    ratio = min(len(a), len(b)) / max(len(a), len(b))
    return ts * (0.6 + 0.4 * ratio)


def match(preds: list[dict], gold: list[dict], threshold: float = MATCH_THRESHOLD) -> list[tuple[int, int, float]]:
    pairs = []
    for i, p in enumerate(preds):
        for j, g in enumerate(gold):
            s = _sim(p["text"], g["text"])
            if s >= threshold:
                pairs.append((s, i, j))
    pairs.sort(reverse=True)
    used_p, used_g, out = set(), set(), []
    for s, i, j in pairs:
        if i in used_p or j in used_g:
            continue
        used_p.add(i)
        used_g.add(j)
        out.append((i, j, s))
    return out


def score_requirements(preds: list[dict], gold: list[dict], label: str = "obligation",
                       critical: tuple[str, ...] = ("mandatory",)) -> dict:
    """Score extracted items against gold. `label` is the class field (obligation for tender
    requirements, kind for manual safety notices); `critical` classes get their own recall and the
    strict all-found check (mandatory requirements; warnings and dangers)."""
    m = match(preds, gold)
    tp = len(m)
    prec = tp / len(preds) if preds else 0.0
    rec = tp / len(gold) if gold else None
    f1 = (2 * prec * rec / (prec + rec)) if (rec and prec + rec) else 0.0
    mand = [j for j, g in enumerate(gold) if g.get(label) in critical]
    matched_g = {j for _, j, _ in m}
    mand_found = sum(1 for j in mand if j in matched_g)
    obl_ok = sum(1 for i, j, _ in m if preds[i].get(label) == gold[j].get(label))
    page_ok = sum(1 for i, j, _ in m if preds[i].get("page") == gold[j].get("page"))
    return {
        "n_gold": len(gold), "n_pred": len(preds), "matched": tp,
        "precision": prec, "recall": rec, "f1": f1,
        "recall_critical": (mand_found / len(mand)) if mand else None,
        "all_critical_found": (mand_found == len(mand)) if mand else None,
        "label_accuracy": (obl_ok / tp) if tp else None,
        # tender-era names kept for existing results
        "recall_mandatory": (mand_found / len(mand)) if mand else None,
        "all_mandatory_found": (mand_found == len(mand)) if mand else None,
        "obligation_accuracy": (obl_ok / tp) if tp else None,
        "page_accuracy": (page_ok / tp) if tp else None,
        "missed": [gold[j]["id"] for j in range(len(gold)) if j not in matched_g],
    }
