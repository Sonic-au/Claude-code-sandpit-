#!/usr/bin/env python3
"""Add one downloaded manual to the technician app's library.

  python scripts/add_manual.py --pdf <file.pdf> --id <doc_id> --title "<title>" --source <url> --app-dir <dir>

<dir>/data.json must be the app's current data file. The script parses the PDF with PyMuPDF4LLM, cuts it into
search passages, finds the figures on each page, and then:
  - writes <dir>/pdf/<doc_id>.pdf (trimmed to --max-pages; the app's reader draws pages straight from it)
  - adds or replaces the manual in <dir>/data.json under the "requested" group

Before anything is written the text is scanned for prompt-injection wording (instructions aimed at an AI rather than
a technician), in visible and in hidden text. A hit stops the script with exit code 3 and nothing is added. Pages that
carry a lot of invisible text are recorded on the manual so a person can look.

Needs only pymupdf4llm, pyyaml and lxml (no PyTorch); the bundled single-file copy needs only the first two. No model is used and nothing leaves the machine.
"""
import argparse
import json
import re
import sys
from pathlib import Path

import fitz  # PyMuPDF
import pymupdf4llm

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from manual_app.retrieve import chunk_pages  # noqa: E402
from export_figures import page_figures  # noqa: E402

MAX_BYTES = 15 * 1024 * 1024   # largest single file the app's host accepts

# Wording that addresses an AI model instead of a person servicing equipment. Deliberately narrow: a hit blocks the manual.
INJECTION = re.compile(r"""
    \b(?:ignore|disregard|forget|override)\s+(?:all\s+|any\s+)?(?:of\s+)?(?:the\s+|your\s+)?(?:previous|prior|above|earlier|preceding|system)\s+(?:instructions?|prompts?|rules|messages?|context)
  | \b(?:system|developer)\s+prompt\b
  | \byou\s+are\s+(?:now\s+)?(?:an?\s+)?(?:ai|a\.i\.|llm|chatbot|chatgpt|claude|gpt|language\s+model|large\s+language\s+model|ai\s+assistant)\b
  | \bas\s+an?\s+(?:ai|large)\s+(?:language\s+)?model\b
  | \bdo\s+not\s+(?:tell|inform|reveal\s+to|mention\s+to)\s+the\s+user\b
  | \bnew\s+instructions?\s*:
  | <\s*/?\s*(?:system|instructions?|assistant)\s*>
  | \b(?:begin|end)\s+(?:system|hidden)\s+(?:prompt|instructions?)\b
  | \bwhen\s+(?:asked|answering|summari[sz]ing)\b.{0,80}\b(?:always|never)\s+(?:say|answer|respond|recommend|state)\b
""", re.I | re.X | re.S)
HIDDEN_PAGE_CHARS = 200   # invisible characters on one page before the page is recorded


def hidden_text(page) -> str:
    """Text a reader cannot see: invisible render mode, zero opacity or microscopic type."""
    out = []
    try:
        for span in page.get_texttrace():
            if span.get("type") == 3 or span.get("opacity", 1) < 0.05 or span.get("size", 10) < 1.5:
                out.append("".join(chr(c[0]) for c in span.get("chars", [])))
    except Exception:
        pass
    return " ".join(out)


def scan(pages_md: list, pdf) -> tuple:
    """Returns (hits, hidden_pages): injection wording found, and pages with much invisible text."""
    hits, hidden_pages = [], []
    for number, (md, page) in enumerate(zip(pages_md, pdf), start=1):
        hid = hidden_text(page)
        if len(hid.strip()) >= HIDDEN_PAGE_CHARS:
            hidden_pages.append(number)
        for where, text in (("visible", md or ""), ("hidden", hid)):
            flat = " ".join(text.split())
            for m in INJECTION.finditer(flat):
                hits.append({"page": number, "where": where, "text": flat[max(0, m.start() - 60):m.end() + 60]})
    return hits, hidden_pages


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", required=True, type=Path)
    ap.add_argument("--id", required=True)
    ap.add_argument("--title", required=True)
    ap.add_argument("--source", default="")
    ap.add_argument("--maker", default="", help="who makes the equipment, e.g. Daikin")
    ap.add_argument("--equipment", default="", help="equipment type for grouping, e.g. HVAC, Pumps, Generators")
    ap.add_argument("--trust", choices=["vendor", "third-party"], default="third-party",
                    help="vendor = downloaded from the maker's own site; anything else is third-party")
    ap.add_argument("--app-dir", required=True, type=Path)
    ap.add_argument("--max-pages", type=int, default=120)
    a = ap.parse_args()
    if not re.fullmatch(r"[a-z0-9]+(_[a-z0-9]+)*", a.id):
        sys.exit("--id must be lower-case words joined by underscores, e.g. req_daikin_ftxm35")
    data_path = a.app_dir / "data.json"
    data = json.loads(data_path.read_text())

    src = fitz.open(a.pdf)
    if not src.is_pdf or src.needs_pass:
        sys.exit("not a readable PDF")
    n = min(len(src), a.max_pages)
    out_pdf = a.app_dir / "pdf" / f"{a.id}.pdf"
    out_pdf.parent.mkdir(parents=True, exist_ok=True)
    trimmed = fitz.open()
    trimmed.insert_pdf(src, from_page=0, to_page=n - 1)
    trimmed.save(out_pdf, garbage=4, deflate=True)
    if out_pdf.stat().st_size > MAX_BYTES:
        out_pdf.unlink()
        sys.exit(f"the trimmed PDF is over {MAX_BYTES // 2**20} MB; lower --max-pages")

    pages = list(range(1, n + 1))
    md = [c.get("text", "") for c in pymupdf4llm.to_markdown(str(out_pdf), page_chunks=True, show_progress=False)]
    md = (md + [""] * n)[:n]
    if sum(len(t.strip()) for t in md) < 40 * n:
        out_pdf.unlink()
        sys.exit("almost no text was read; this looks like a scan and needs OCR, which this script does not do")
    hits, hidden_pages = scan(md, fitz.open(out_pdf))
    if hits:
        out_pdf.unlink()
        print(json.dumps({"blocked": "prompt-injection wording found", "hits": hits[:10]}, ensure_ascii=False, indent=1))
        sys.exit(3)
    chunks = chunk_pages(md, pages)
    figs = {}
    for number, page in zip(pages, fitz.open(out_pdf)):
        rects = [[round(v, 1) for v in ((r + (-6, -6, 6, 6)) & page.rect)] for r in page_figures(page)]
        if rects:
            figs[str(number)] = rects

    entry = {"id": a.id, "corpus": "requested", "title": a.title, "pages": pages,
             "page_text": {str(p): t for p, t in zip(pages, md)},
             "chunks": [{"page": c.page, "heading": c.heading, "text": c.text} for c in chunks],
             "examples": [], "pdf": f"pdf/{a.id}.pdf", "figs": figs, "source": a.source, "maker": a.maker[:40], "equipment": a.equipment[:40], "trust": a.trust, "parser": "pymupdf4llm",
             "security": {"scanned": True, "hidden_text_pages": hidden_pages},
             "total_pages": len(src)}
    data["manuals"] = [m for m in data["manuals"] if m["id"] != a.id] + [entry]
    data_path.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")))
    print(f"{a.id}: {n} of {len(src)} pages, {len(chunks)} passages, {sum(len(v) for v in figs.values())} figures, "
          f"pdf {out_pdf.stat().st_size // 1024} KB, data.json {data_path.stat().st_size // 1024} KB, "
          f"{len(data['manuals'])} manuals, trust {a.trust}, hidden-text pages {hidden_pages or 'none'}")


if __name__ == "__main__":
    main()
