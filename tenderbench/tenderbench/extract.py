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


# ---------------------------------------------------------------- manuals: safety notices

SIGNAL = re.compile(r"^(DANGER|WARNING|CAUTION|NOTICE|NOTE|IMPORTANT|[A-Z][a-z]+ Hazard)\b\s*[:!.-]?\s*", re.I)
SIGNAL_KIND = {"danger": "danger", "warning": "warning", "caution": "caution", "notice": "caution",
               "note": "note", "important": "note"}
_LIST = re.compile(r"^\s*(?:[-*+\u2022\u25aa\uf0b7]|\(?[a-z0-9]{1,3}[.)])\s+", re.I)
_HEADING = re.compile(r"^\s{0,3}#{1,6}\s+")


def _clean(line: str) -> str:
    return " ".join(markdown_to_text(line).split())


def _signal(line: str):
    """(kind, rest-of-line) if the line opens a safety notice, else None."""
    txt = _clean(_HEADING.sub("", line))
    m = SIGNAL.match(txt)
    # A real notice uses the signal word in capitals ("WARNING") or as a label ("Note:", "Electrical Hazard:");
    # "Note that the pump..." in running text is not a notice.
    if not m or not (m.group(1).isupper() or m.group(0).rstrip().endswith(":")):
        return None
    word = m.group(1).lower()
    kind = SIGNAL_KIND.get(word, "warning" if word.endswith("hazard") else None)
    return (kind, txt[m.end():].strip()) if kind else None


def extract_safety(pages: list[str], page_map: list[int]) -> list[dict]:
    """Baseline: a signal word (WARNING, CAUTION, NOTE, 'Electrical Hazard:'...) opens a notice. Its body is the
    rest of the line, then either the bulleted items that follow (one notice per bullet, across blank lines)
    or the next paragraph. A heading or another signal word ends it. Works on Markdown lines so list and
    heading structure from the parser is used."""
    out = []
    for md, page in zip(pages, page_map):
        lines = (md or "").splitlines()
        i = 0
        while i < len(lines):
            sig = _signal(lines[i])
            if not sig:
                i += 1
                continue
            kind, first = sig
            items = [first] if first else []
            i += 1
            in_list = False
            while i < len(lines):
                raw = lines[i]
                if not raw.strip():
                    i += 1
                    continue
                if _signal(raw):
                    break
                if _HEADING.match(raw):
                    if not items:          # military style: WARNING / KEEP AWAY FROM LIVE CIRCUITS / body
                        i += 1
                        continue
                    break
                cleaned = _clean(raw)
                if items and not in_list and cleaned.isupper() and len(cleaned) > 12:
                    items.append(cleaned)  # follow-on capitalised warning lines ("THE BEST DEFENSE IS ...")
                    i += 1
                    continue
                if _LIST.match(raw):
                    in_list = True
                    items.append(_clean(_LIST.sub("", raw)))
                    i += 1
                    continue
                if in_list or items:      # a plain paragraph after the body ends the notice
                    break
                items.append(_clean(raw))  # signal word alone on its line: the next paragraph is the body
                i += 1
            for t in items:
                for part in [p.strip(" ;") for p in re.split(r"\s*[\u2022\u25aa\uf0b7]\s+", t) if p.strip(" ;")]:
                    if len(part) >= 12:
                        out.append({"page": page, "text": part, "kind": kind})
    return out
