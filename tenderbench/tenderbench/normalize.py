"""Text and table normalisation shared by all metrics.

Parsers emit Markdown, HTML fragments or plain text. Metrics compare *content*, so this
module strips presentation (markup, quote styles, hyphenation, whitespace) before scoring,
and pulls tables out into one HTML form that TEDS can compare.
"""
from __future__ import annotations

import html
import re
import unicodedata

from lxml import html as lxml_html

_QUOTES = {"‘": "'", "’": "'", "‚": "'", "‛": "'", "“": '"', "”": '"',
           "„": '"', "′": "'", "″": '"'}
_DASHES = {"‐": "-", "‑": "-", "‒": "-", "–": "-", "—": "-", "―": "-", "−": "-"}
_BULLETS = re.compile(r"^\s*(?:[-*+•▪●‣◦]|\d+[.)])\s+", re.M)


def norm_text(s: str, lower: bool = True) -> str:
    """Canonical form for comparing extracted text with gold text."""
    if not s:
        return ""
    s = unicodedata.normalize("NFKC", s)
    s = "".join(_QUOTES.get(c, _DASHES.get(c, c)) for c in s)
    s = s.replace("­", "")                      # soft hyphen
    s = re.sub(r"(\w)-\n(\w)", r"\1\2", s)            # end-of-line hyphenation
    s = s.replace("…", "...")
    s = re.sub(r"[.…]{4,}", " ", s)              # dot leaders (forms, TOCs)
    s = re.sub(r"_{3,}", " ", s)                      # fill-in lines
    s = re.sub(r"[\u2610\u2611\u2612\u25a1\u25a2\u25fb\u274f\u53e3\uf06f\uf0a8]", " ", s)  # checkbox glyphs
    s = re.sub(r"\s+", " ", s).strip()
    return s.lower() if lower else s


def markdown_to_text(md: str) -> str:
    """Strip Markdown/HTML markup, keep the words in reading order (tables row by row)."""
    if not md:
        return ""
    s = md
    s = re.sub(r"<!--.*?-->", " ", s, flags=re.S)                   # comments / page-break markers
    s = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", s)                      # images
    s = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", s)                   # links -> anchor text
    s = re.sub(r"<(td|th)[^>]*>", " ", s, flags=re.I)
    s = re.sub(r"</(tr|p|div|h\d|li)>", "\n", s, flags=re.I)
    s = re.sub(r"<br\s*/?>", "\n", s, flags=re.I)
    s = re.sub(r"<[^>]+>", " ", s)                                  # any other tag
    s = html.unescape(s)
    s = re.sub(r"^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?\s*$", " ", s, flags=re.M)  # table rules
    s = s.replace("|", " ")
    s = re.sub(r"^\s{0,3}#{1,6}\s*", "", s, flags=re.M)              # headings
    s = re.sub(r"\\([\\`*_{}\[\]()#+\-.!|<>])", r"\1", s)           # Markdown escapes (Docling writes pg\_wal)
    s = re.sub(r"(\*\*|\*|`|~~)", "", s)                             # emphasis / code / strike marks
    # Underscores: strip only emphasis (_word_, __word__), keep identifiers such as pg_wal or archive_command.
    s = re.sub(r"(?<![A-Za-z0-9])_+|_+(?![A-Za-z0-9])", "", s)
    s = _BULLETS.sub("", s)
    return s


def content_text(md: str, lower: bool = True) -> str:
    return norm_text(markdown_to_text(md), lower=lower)


# ---------------------------------------------------------------- tables

def _cell_text(s: str) -> str:
    return norm_text(markdown_to_text(s), lower=False)


def _md_table_blocks(md: str) -> list[list[str]]:
    """Find GitHub-style pipe tables; return each as its list of lines."""
    lines = md.splitlines()
    blocks, cur = [], []
    for ln in lines:
        if ln.strip().startswith("|") or (ln.count("|") >= 2 and cur):
            cur.append(ln)
        else:
            if len(cur) >= 2:
                blocks.append(cur)
            cur = []
    if len(cur) >= 2:
        blocks.append(cur)
    return [b for b in blocks if any(re.match(r"^\s*\|?\s*:?-{2,}", x) for x in b)]


def _md_block_to_rows(block: list[str]) -> tuple[list[list[str]], int]:
    rows, header_rows = [], 0
    for i, ln in enumerate(block):
        if re.match(r"^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?\s*$", ln):
            header_rows = len(rows)
            continue
        ln = ln.strip()
        if ln.startswith("|"):
            ln = ln[1:]
        if ln.endswith("|"):
            ln = ln[:-1]
        rows.append([_cell_text(c) for c in ln.split("|")])
    return rows, header_rows


def rows_to_html(rows: list[list[str]], header_rows: int = 1) -> str:
    out = ["<table>"]
    for i, r in enumerate(rows):
        tag = "th" if i < header_rows else "td"
        out.append("<tr>" + "".join(f"<{tag}>{html.escape(c)}</{tag}>" for c in r) + "</tr>")
    out.append("</table>")
    return "".join(out)


def extract_tables(md: str) -> list[str]:
    """All tables in a parser's output, as canonical HTML (spans kept, cell text normalised)."""
    tables = []
    for m in re.finditer(r"<table.*?</table>", md or "", flags=re.S | re.I):
        tables.append(canonical_html_table(m.group(0)))
    stripped = re.sub(r"<table.*?</table>", " ", md or "", flags=re.S | re.I)
    for block in _md_table_blocks(stripped):
        rows, h = _md_block_to_rows(block)
        if rows:
            tables.append(rows_to_html(rows, max(h, 1)))
    return [t for t in tables if t]


def canonical_html_table(fragment: str) -> str:
    try:
        tree = lxml_html.fromstring(fragment)
    except Exception:
        return ""
    table = tree if tree.tag == "table" else tree.find(".//table")
    if table is None:
        return ""
    out = ["<table>"]
    for tr in table.iter("tr"):
        cells = []
        for c in tr:
            if c.tag not in ("td", "th"):
                continue
            attrs = ""
            for a in ("colspan", "rowspan"):
                v = c.get(a)
                if v and v != "1":
                    attrs += f' {a}="{v}"'
            cells.append(f"<{c.tag}{attrs}>{html.escape(_cell_text(c.text_content()))}</{c.tag}>")
        if cells:
            out.append("<tr>" + "".join(cells) + "</tr>")
    out.append("</table>")
    return "".join(out)


def table_grid(table_html: str) -> list[list[str]]:
    """Expand a canonical HTML table into a rectangular grid (spans repeated)."""
    tree = lxml_html.fromstring(table_html)
    grid: list[list[str | None]] = []
    for r_idx, tr in enumerate(tree.iter("tr")):
        while len(grid) <= r_idx:
            grid.append([])
        row = grid[r_idx]
        c_idx = 0
        for cell in tr:
            if cell.tag not in ("td", "th"):
                continue
            while c_idx < len(row) and row[c_idx] is not None:
                c_idx += 1
            cs, rs = int(cell.get("colspan", 1)), int(cell.get("rowspan", 1))
            text = cell.text_content()
            for dr in range(rs):
                while len(grid) <= r_idx + dr:
                    grid.append([])
                target = grid[r_idx + dr]
                while len(target) < c_idx + cs:
                    target.append(None)
                for dc in range(cs):
                    target[c_idx + dc] = text
            c_idx += cs
    width = max((len(r) for r in grid), default=0)
    return [[(c or "") for c in r] + [""] * (width - len(r)) for r in grid]
