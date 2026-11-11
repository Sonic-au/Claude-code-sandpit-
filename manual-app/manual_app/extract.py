"""Safety-notice extractors: a transparent rule-based baseline and an LLM extractor.

Both read a parser's per-page Markdown, so the same extractor run on different parsers shows
how much parsing quality changes which warnings, cautions and notes are found.
"""
from __future__ import annotations

import re

from .normalize import markdown_to_text


def _llm_pages(llm, pages, page_map, prompt, schema, system, title, label_key):
    from .llm import LLMRefusal
    out, skipped = [], []
    for md, page in zip(pages, page_map):
        if not md.strip():
            continue
        try:
            data = llm.complete_json(prompt.format(page=page, title=title, text=md[:60000]), schema, system)
        except LLMRefusal:
            skipped.append(page)
            continue
        for it in data.get("items", []):
            out.append({"page": page, "text": it["text"], label_key: it[label_key]})
    return out, skipped


SAFETY_SYSTEM = "You extract safety notices from technical manuals for a technician knowledge base."
SAFETY_PROMPT = """Page {page} of the manual "{title}" is below, as parsed text.

List every safety notice on this page: text introduced by a signal word or label such as DANGER, WARNING,
CAUTION, NOTICE, NOTE, IMPORTANT or "<something> Hazard:", including notices printed in boxes or as table cells.
One item per distinct statement: when a notice is a bulleted list, give one item per bullet. Copy the notice
text VERBATIM without the signal word. Do not include definitions of what the signal words mean.

kind: "danger", "warning" (also "... Hazard:" labels), "caution" (also NOTICE), or "note" (also IMPORTANT, TIP),
following the signal word printed with the notice.

Return an empty list if the page has none.

PAGE TEXT:
<<<
{text}
>>>"""

SAFETY_SCHEMA = {
    "type": "object",
    "properties": {"items": {"type": "array", "items": {
        "type": "object",
        "properties": {"text": {"type": "string"},
                       "kind": {"type": "string", "enum": ["danger", "warning", "caution", "note"]}},
        "required": ["text", "kind"], "additionalProperties": False}}},
    "required": ["items"], "additionalProperties": False,
}


def extract_safety_llm(llm, pages: list[str], page_map: list[int], title: str) -> list[dict]:
    out, _ = _llm_pages(llm, pages, page_map, SAFETY_PROMPT, SAFETY_SCHEMA, SAFETY_SYSTEM, title, "kind")
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
