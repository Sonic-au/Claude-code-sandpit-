"""Parsers that run on this machine (open source, nothing leaves the environment)."""
from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
from pathlib import Path

from .base import Parser, which


class PypdfText(Parser):
    """Lower bound: the PDF text layer, no layout or OCR. Shows what parsing adds."""
    name = "pypdf-text"
    licence = "BSD-3-Clause"
    notes = "Raw text layer only; no tables, no OCR."

    def _parse(self, pdf, n_pages):
        import pypdf
        return [(p.extract_text() or "") for p in pypdf.PdfReader(str(pdf)).pages]


class PyMuPDF4LLM(Parser):
    name = "pymupdf4llm"
    licence = "AGPL-3.0 (commercial licence from Artifex)"
    notes = "Fast rule-based Markdown with table detection; layout model when pymupdf-layout is installed."

    def available(self):
        try:
            import pymupdf4llm  # noqa: F401
            return True, ""
        except ImportError:
            return False, "pip install pymupdf4llm"

    def _parse(self, pdf, n_pages):
        import pymupdf4llm
        chunks = pymupdf4llm.to_markdown(str(pdf), page_chunks=True, show_progress=False)
        return [c.get("text", "") for c in chunks]


class Docling(Parser):
    """IBM Docling: layout model + TableFormer, optional OCR (RapidOCR on CPU)."""
    name = "docling"
    licence = "MIT (models: Apache-2.0 / CDLA)"
    notes = "Layout analysis (DocLayNet-trained) + TableFormer; RapidOCR for bitmap content."

    def __init__(self, ocr: str = "auto", table_mode: str = "accurate", force_ocr: bool = False):
        self.ocr, self.table_mode, self.force_ocr = ocr, table_mode, force_ocr
        if force_ocr:
            self.name = "docling-forceocr"
        self._converter = None

    def available(self):
        try:
            import docling  # noqa: F401
            return True, ""
        except ImportError:
            return False, "pip install docling"

    def _conv(self):
        # Hugging Face's Xet CDN is often blocked by corporate proxies; plain HTTPS works.
        os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
        if self._converter is None:
            from docling.datamodel.base_models import InputFormat
            from docling.datamodel.pipeline_options import PdfPipelineOptions, RapidOcrOptions, TableFormerMode
            from docling.document_converter import DocumentConverter, PdfFormatOption

            opts = PdfPipelineOptions()
            opts.do_ocr = self.ocr != "off"
            if opts.do_ocr:
                opts.ocr_options = RapidOcrOptions(force_full_page_ocr=self.force_ocr)
            opts.do_table_structure = True
            opts.table_structure_options.mode = (TableFormerMode.ACCURATE if self.table_mode == "accurate"
                                                 else TableFormerMode.FAST)
            self._converter = DocumentConverter(format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=opts)})
        return self._converter

    def _parse(self, pdf, n_pages):
        res = self._conv().convert(str(pdf))
        doc = res.document
        out = []
        for i in range(1, n_pages + 1):
            # HTML tables keep merged cells; Markdown tables cannot express them.
            out.append(_docling_page_markdown(doc, i))
        return out


def _docling_page_markdown(doc, page_no: int) -> str:
    """Serialise one page: headings as #, list items as -, tables as HTML (keeps merged cells)."""
    from docling_core.types.doc import ListItem, PictureItem, SectionHeaderItem, TableItem, TextItem, TitleItem

    parts = []
    for item, level in doc.iterate_items(page_no=page_no):
        if isinstance(item, TableItem):
            parts.append(item.export_to_html(doc=doc, add_caption=True))
        elif isinstance(item, TitleItem):
            parts.append("# " + item.text)
        elif isinstance(item, SectionHeaderItem):
            parts.append("#" * min(6, (getattr(item, "level", 1) or 1) + 1) + " " + item.text)
        elif isinstance(item, ListItem):
            parts.append("- " + item.text)
        elif isinstance(item, PictureItem):
            continue
        elif isinstance(item, TextItem):
            parts.append(item.text)
    return "\n\n".join(p for p in parts if p and p.strip())


def _lp_config() -> list[str]:
    """LITEPARSE_CONFIG points at a JSON config, e.g. {"tessdataPath": "/opt/tessdata"} so OCR
    uses a local language model instead of downloading one from GitHub."""
    cfg = os.environ.get("LITEPARSE_CONFIG")
    return ["--config", cfg] if cfg else []


class LiteParse(Parser):
    """LlamaIndex LiteParse (open source, local): spatial text extraction, optional OCR."""
    name = "liteparse"
    licence = "Apache-2.0"
    notes = "Open-source local cousin of LlamaParse; Tesseract.js OCR for image pages."

    def __init__(self, binary: str | None = None, ocr: bool = True):
        self.binary = binary or os.environ.get("LITEPARSE_BIN") or which("lit") or which("liteparse")
        self.ocr = ocr
        if not ocr:
            self.name = "liteparse-noocr"

    def available(self):
        return (True, "") if self.binary else (False, "npm install @llamaindex/liteparse (set LITEPARSE_BIN)")

    def _parse(self, pdf, n_pages):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "out.json"
            cmd = [self.binary, "parse", str(pdf), "--format", "json", "-o", str(out), "-q"] + _lp_config()
            if not self.ocr:
                cmd.append("--no-ocr")
            subprocess.run(cmd, check=True, capture_output=True, timeout=1800)
            data = json.loads(out.read_text())
        pages = data.get("pages", data if isinstance(data, list) else [])
        texts = []
        for p in pages:
            texts.append(p.get("markdown") or p.get("md") or p.get("text") or "")
        return texts


class LiteParseMarkdown(LiteParse):
    """LiteParse Markdown output (headings/tables) split on its page markers."""
    name = "liteparse-md"

    def _parse(self, pdf, n_pages):
        out = []
        for i in range(1, n_pages + 1):
            with tempfile.TemporaryDirectory() as td:
                dest = Path(td) / "out.md"
                cmd = [self.binary, "parse", str(pdf), "--format", "markdown", "--target-pages", str(i),
                       "-o", str(dest), "-q"] + _lp_config()
                if not self.ocr:
                    cmd.append("--no-ocr")
                subprocess.run(cmd, check=True, capture_output=True, timeout=600)
                out.append(dest.read_text())
        return out


class MinerU(Parser):
    """OpenDataLab MinerU, run locally (never `--remote`). Best pipeline tool in OmniDocBench.

    Uses the `mineru-kit parse` CLI (MinerU 3.x) with middle-JSON output, converted per page.
    Set MINERU_BIN to the mineru-kit binary if it lives in another virtualenv.
    """
    name = "mineru"
    licence = "AGPL-3.0"
    notes = "Layout + OCR + table models (ONNX on CPU); local mode only."

    def __init__(self, tier: str = "basic"):
        self.tier = tier
        self.binary = os.environ.get("MINERU_BIN") or which("mineru-kit")

    def available(self):
        return (True, "") if self.binary else (False, "pip install -U 'mineru[core]' and set MINERU_BIN to mineru-kit")

    def _parse(self, pdf, n_pages):
        env = {**os.environ, "MINERU_MODEL_SOURCE": os.environ.get("MINERU_MODEL_SOURCE", "huggingface"),
               "HF_HUB_DISABLE_XET": "1"}
        with tempfile.TemporaryDirectory() as td:
            subprocess.run([self.binary, "parse", str(pdf), "-o", td, "-f", "middle_json", "--tier", self.tier],
                           check=True, capture_output=True, timeout=7200, env=env)
            data = json.loads(next(Path(td).rglob("*.json")).read_text())
        pages = [""] * n_pages
        for pg in data.get("pages", []):
            i = pg.get("page_idx", 0)
            if 0 <= i < n_pages:
                pages[i] = _mineru_page_md(pg.get("blocks", []))
        return pages


_MINERU_SKIP = {"header", "footer", "page_number", "page_footnote", "image", "image_body", "discarded"}


def _mineru_text(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(_mineru_text(c.get("content", "")) if isinstance(c, dict) else str(c) for c in content)
    return ""


def _mineru_page_md(blocks: list[dict]) -> str:
    parts = []
    for b in blocks:
        t = b.get("type", "")
        if t in _MINERU_SKIP:
            continue
        if t == "table":
            for c in b.get("content", []):
                if isinstance(c, dict) and c.get("type") == "table_body":
                    parts.append(_mineru_text(c.get("content", "")))
                elif isinstance(c, dict) and c.get("type") in ("table_caption", "table_footnote"):
                    parts.append(_mineru_text(c.get("content", "")))
        elif t in ("title", "doc_title", "paragraph_title"):
            parts.append("#" * min(6, int(b.get("level", 1) or 1)) + " " + _mineru_text(b.get("content", "")))
        elif t == "list":
            for c in b.get("content", []):
                parts.append("- " + _mineru_text(c.get("content", "") if isinstance(c, dict) else c))
        else:
            parts.append(_mineru_text(b.get("content", "")))
    return "\n\n".join(p for p in parts if p and p.strip())


class Marker(Parser):
    name = "marker"
    licence = "GPL-3.0 (commercial licence via Datalab)"
    notes = "Surya OCR/layout models; best on GPU."

    def available(self):
        return (True, "") if which("marker_single") else (False, "pip install marker-pdf")

    def _parse(self, pdf, n_pages):
        with tempfile.TemporaryDirectory() as td:
            subprocess.run(["marker_single", str(pdf), "--output_dir", td, "--paginate_output",
                            "--output_format", "markdown"], check=True, capture_output=True, timeout=7200)
            md = next(Path(td).rglob("*.md")).read_text()
        # paginate_output inserts "{N}------" separators before each page.
        parts = re.split(r"\n?\{\d+\}-{10,}\n", md)
        parts = [p for p in parts if p.strip() or len(parts) <= n_pages]
        return (parts + [""] * n_pages)[:n_pages]


class UnstructuredOSS(Parser):
    name = "unstructured"
    licence = "Apache-2.0"

    def __init__(self, strategy: str = "fast"):
        self.strategy = strategy
        self.name = f"unstructured-{strategy}"

    def available(self):
        try:
            import unstructured  # noqa: F401
            return True, ""
        except ImportError:
            return False, "pip install 'unstructured[pdf]'"

    def _parse(self, pdf, n_pages):
        from unstructured.partition.pdf import partition_pdf
        els = partition_pdf(filename=str(pdf), strategy=self.strategy, infer_table_structure=True)
        pages = [[] for _ in range(n_pages)]
        for e in els:
            pn = (e.metadata.page_number or 1) - 1
            if pn >= n_pages:
                continue
            html_t = getattr(e.metadata, "text_as_html", None)
            if e.category == "Table" and html_t:
                pages[pn].append(html_t)
            elif e.category == "Title":
                pages[pn].append("## " + e.text)
            else:
                pages[pn].append(e.text)
        return ["\n\n".join(p) for p in pages]
