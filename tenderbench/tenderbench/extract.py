"""Requirement extractors: a transparent rule-based baseline and an LLM extractor.

Both read a parser's per-page Markdown, so the same extractor run on different parsers shows
how much parsing quality changes the compliance matrix.
"""
from __future__ import annotations

import re

from .normalize import markdown_to_text

# Obligation cues on the respondent/contractor. "will" is deliberately excluded: in tenders it
# usually states the buyer's own intent ("Council will assess...").
CUES = re.compile(
    r"\b(must|shall|are to|is to|required to|is required|are required|mandatory|need to|needs to|"
    r"should|provide|submit|include|demonstrate|describe|attach|complete|sign|nominate|list|detail)\b", re.I)
MANDATORY = re.compile(r"\b(must|shall|are to|is to|required|mandatory|need to|needs to)\b", re.I)
EVALUATED = re.compile(r"\b(demonstrate|describe|detail|explain|outline|weighting|criteri|experience|methodology|"
                       r"approach|capabilit|resources|references?)\b", re.I)
ADMIN = re.compile(r"\b(submi|lodge|deadline|signed|sign|format|copies|page limit|pages|font|e-?mail|address|"
                   r"envelope|portal|label|attach|complete and return|form)\w*", re.I)
BUYER = re.compile(r"^\s*(the\s+)?(council|cn|principal|shire|centralina|city|evaluation panel|panel|"
                   r"superintendent|owner|purchaser|we|son)\b[^.]{0,40}\b(will|may|reserves|is not|does not|shall not be)\b",
                   re.I)


def _units(page_md: str) -> list[str]:
    """Split a page into requirement-sized units: list items, table rows/cells, sentences."""
    text = markdown_to_text(page_md)
    units = []
    for block in re.split(r"\n\s*\n|\n(?=\s*(?:\(?[a-z0-9]{1,3}[.)]|[-*•])\s)", text):
        block = " ".join(block.split())
        if not block:
            continue
        for sent in re.split(r"(?<=[.;:])\s+(?=[A-Z(])", block):
            sent = sent.strip()
            if 25 <= len(sent) <= 600:
                units.append(sent)
    return units


def classify(sentence: str) -> str:
    if ADMIN.search(sentence) and not EVALUATED.search(sentence):
        return "administrative"
    if EVALUATED.search(sentence) and not re.search(r"\b(must|shall)\b", sentence, re.I):
        return "evaluated"
    if MANDATORY.search(sentence):
        return "mandatory"
    return "informational"


def extract_rules(pages: list[str], page_map: list[int]) -> list[dict]:
    """Baseline: every sentence/list item with an obligation cue that is not a buyer statement."""
    out = []
    lead = None   # obligation inherited from a lead-in such as "The Respondent must:"
    for md, page in zip(pages, page_map):
        for u in _units(md):
            is_item = bool(re.match(r"^\(?([a-z]{1,3}|[ivx]+|\d{1,2})[.)]\s", u, re.I))
            if lead and is_item and not BUYER.search(u):
                out.append({"page": page, "text": u, "obligation": classify(u) if CUES.search(u) else lead})
                continue
            lead = None
            if not CUES.search(u) or BUYER.search(u):
                continue
            if u.rstrip().endswith((":", ":-", "-")) or re.search(r"\b(following|as follows)\b", u, re.I):
                lead = classify(u)
            out.append({"page": page, "text": u, "obligation": classify(u)})
    return out


LLM_SYSTEM = (
    "You extract requirements from tender (RFT/RFP) documents for a bid team's compliance matrix. "
    "Return only JSON."
)
LLM_PROMPT = """Page {page} of the tender "{title}" is below, as parsed text.

List every requirement this page places on the tenderer/respondent/contractor - things they must or
should do, provide, submit, comply with, or address for evaluation. One item per distinct requirement:
split compound requirements ("X and Y") into separate items. Copy the requirement text VERBATIM from
the page (no paraphrasing). Skip statements of what the buyer will do, definitions, and background.

For each item give:
  "text": verbatim requirement text,
  "obligation": one of "mandatory" (must/shall/required - non-compliance can exclude the bid),
                "evaluated" (scored against criteria, e.g. describe/demonstrate experience),
                "administrative" (submission format, forms, signatures, deadlines),
                "informational" (should/may, guidance with no hard obligation).

Return a JSON array of objects. Return [] if there are none.

PAGE TEXT:
<<<
{text}
>>>"""


def extract_llm(llm, pages: list[str], page_map: list[int], title: str) -> list[dict]:
    out = []
    for md, page in zip(pages, page_map):
        if not md.strip():
            continue
        items = llm.complete_json(LLM_PROMPT.format(page=page, title=title, text=md[:30000]), LLM_SYSTEM)
        for it in items or []:
            if isinstance(it, dict) and it.get("text"):
                out.append({"page": page, "text": it["text"], "obligation": it.get("obligation", "mandatory")})
    return out
