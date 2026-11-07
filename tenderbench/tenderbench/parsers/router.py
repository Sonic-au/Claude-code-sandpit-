"""The combined pipeline under test: route each page to the parser that suits it.

What the papers found, applied per page:
- Pipeline parsers (layout model + table model) are strongest on born-digital pages
  (OmniDocBench), and keep tables with merged cells as HTML.
- Vision-language models and OCR generalise better to scans, forms and degraded pages
  (OmniDocBench, RealDocBench), so image-only pages go there.
- A cheap rule-based parser is a safety net when the main parser returns an empty page.

Routing:
  page has a text layer      -> `digital` parser (default Docling)
  page is image-only (scan)  -> `scan` parser: a self-hosted/onshore VLM when configured,
                                otherwise Docling with full-page OCR
  primary returned ~nothing  -> `fallback` parser (default PyMuPDF4LLM)
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

from .base import Parser

MIN_TEXT_CHARS = 40


def _text_layer_chars(pdf: Path) -> list[int]:
    import pypdf
    return [len((p.extract_text() or "").strip()) for p in pypdf.PdfReader(str(pdf)).pages]


def _subset(pdf: Path, idx: list[int], dest: Path) -> Path:
    import pypdf
    r, w = pypdf.PdfReader(str(pdf)), pypdf.PdfWriter()
    for i in idx:
        w.add_page(r.pages[i])
    with dest.open("wb") as f:
        w.write(f)
    return dest


class TenderRouter(Parser):
    name = "router"
    licence = "mix (see component parsers)"
    notes = "Digital pages -> Docling; image-only pages -> VLM (if configured) or Docling full-page OCR; empty -> PyMuPDF4LLM."

    def __init__(self, digital: str = "docling", scan: str | None = None, fallback: str = "pymupdf4llm"):
        from . import get_parser
        self.digital = get_parser(digital)
        scan = scan or os.environ.get("TB_ROUTER_SCAN") or ("vlm" if os.environ.get("TB_VLM_BASE_URL") else "docling-forceocr")
        self.scan = get_parser(scan)
        self.fallback = get_parser(fallback)
        # The pipeline is only as onshore as its least onshore component.
        rank = {"local": 0, "self-hosted": 1, "cloud-au": 2, "offshore": 3}
        self.residency = max((self.digital.residency, self.scan.residency, self.fallback.residency), key=rank.get)
        self.name = f"router[{self.digital.name}|{self.scan.name}]"

    def available(self):
        for p in (self.digital, self.scan, self.fallback):
            ok, why = p.available()
            if not ok:
                return False, f"{p.name}: {why}"
        return True, ""

    def _parse(self, pdf, n_pages):
        chars = _text_layer_chars(pdf)
        digital_idx = [i for i, c in enumerate(chars) if c >= MIN_TEXT_CHARS]
        scan_idx = [i for i, c in enumerate(chars) if c < MIN_TEXT_CHARS]
        out = [""] * n_pages
        with tempfile.TemporaryDirectory() as td:
            for idx, parser in ((digital_idx, self.digital), (scan_idx, self.scan)):
                if not idx:
                    continue
                sub = pdf if len(idx) == n_pages else _subset(pdf, idx, Path(td) / f"{parser.name}.pdf")
                pages = parser._parse(sub, len(idx))
                for i, md in zip(idx, pages):
                    out[i] = md
            empty = [i for i, md in enumerate(out) if len(md.strip()) < MIN_TEXT_CHARS and chars[i] >= MIN_TEXT_CHARS]
            if empty:
                pages = self.fallback._parse(_subset(pdf, empty, Path(td) / "fallback.pdf"), len(empty))
                for i, md in zip(empty, pages):
                    out[i] = md
        return out
