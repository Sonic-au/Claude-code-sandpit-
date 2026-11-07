"""Page-level text fidelity (OmniDocBench-style normalised edit distance)."""
from __future__ import annotations

from rapidfuzz.distance import Levenshtein

from ..normalize import content_text


def text_similarity(pred_md: str, gold_md: str) -> float:
    """1 - normalised Levenshtein distance between content-only text (1.0 = identical).

    Order matters: a parser that interleaves two columns or moves a table scores lower.
    """
    p, g = content_text(pred_md), content_text(gold_md)
    if not g and not p:
        return 1.0
    return 1.0 - Levenshtein.normalized_distance(p, g)
