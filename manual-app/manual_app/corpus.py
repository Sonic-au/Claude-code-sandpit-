"""Corpus handling: fetch source PDFs, verify them, and build the bench PDFs.

A bench PDF holds only the manifest's pages, in order. `page_map` records which original
page each bench page came from, so every score can be traced to the source document.
"""
from __future__ import annotations

import hashlib
import io
import json
import random
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
CORPORA = ROOT / "corpus"
DEFAULT_CORPUS = "manuals"
DATA = ROOT / "data"


def manifest_path(corpus: str | None = None) -> Path:
    """Corpus manifest: TB_CORPUS env var or argument (`manuals` by default; also `techmanualqa` and `hvac`)."""
    import os
    name = corpus or os.environ.get("TB_CORPUS") or DEFAULT_CORPUS
    p = CORPORA / f"{name}.yaml"
    if not p.exists():
        raise FileNotFoundError(f"no corpus manifest {p}; available: {[x.stem for x in CORPORA.glob('*.yaml')]}")
    return p
USER_AGENT = "ManualHandling/0.1 (document-parsing research; +https://github.com/Sonic-au/Claude-code-sandpit-)"


@dataclass
class Document:
    id: str
    title: str
    kind: str
    pages: list[int] | str
    url: str | None = None
    sha256: str | None = None
    derived_from: str | None = None
    transform: dict | None = None
    publisher: str = ""
    category: str = ""
    notes: str = ""
    extra: dict = field(default_factory=dict)

    @property
    def gold_id(self) -> str:
        """Gold annotations live under the source document for derived documents."""
        return self.derived_from or self.id

    @property
    def source_pdf(self) -> Path:
        return DATA / "source" / f"{self.derived_from or self.id}.pdf"

    @property
    def bench_pdf(self) -> Path:
        return DATA / "bench" / f"{self.id}.pdf"

    @property
    def page_map_path(self) -> Path:
        return DATA / "bench" / f"{self.id}.pages.json"

    def page_map(self) -> list[int]:
        return json.loads(self.page_map_path.read_text())


def load_manifest(path: Path | None = None) -> list[Document]:
    raw = yaml.safe_load((path or manifest_path()).read_text())
    docs = []
    if "documents" not in (raw or {}):      # e.g. vendor_sources.yaml lives beside the manifests
        return docs
    known = {"id", "title", "kind", "pages", "url", "sha256", "derived_from", "transform", "publisher", "category",
             "notes"}
    for d in raw["documents"]:
        docs.append(Document(**{k: v for k, v in d.items() if k in known},
                             extra={k: v for k, v in d.items() if k not in known}))
    return docs


def get_document(doc_id: str) -> Document:
    for p in sorted(CORPORA.glob("*.yaml")):
        for d in load_manifest(p):
            if d.id == doc_id:
                return d
    raise KeyError(f"unknown document id: {doc_id}")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def fetch(doc: Document, force: bool = False) -> Path:
    """Download a source document (once) and verify its checksum."""
    if doc.derived_from:
        return fetch(get_document(doc.derived_from), force)
    dest = doc.source_pdf
    dest.parent.mkdir(parents=True, exist_ok=True)
    if force or not dest.exists():
        req = urllib.request.Request(doc.url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=180) as resp:
            dest.write_bytes(resp.read())
    if doc.sha256:
        got = _sha256(dest)
        if got != doc.sha256:
            raise ValueError(
                f"{doc.id}: checksum mismatch (expected {doc.sha256}, got {got}). "
                "The publisher may have replaced the file; re-check the gold annotations before updating the manifest."
            )
    return dest


def _resolve_pages(doc: Document, n_pages: int) -> list[int]:
    if doc.pages == "all":
        return list(range(1, n_pages + 1))
    return [int(p) for p in doc.pages]


def build(doc: Document) -> Path:
    """Create the bench PDF (page subset, and the scan transform if any)."""
    import pypdf

    src = fetch(doc)
    reader = pypdf.PdfReader(str(src))
    pages = _resolve_pages(doc, len(reader.pages))
    doc.bench_pdf.parent.mkdir(parents=True, exist_ok=True)
    if doc.transform and doc.transform.get("type") == "scan":
        _build_scan(src, pages, doc.bench_pdf, doc.transform)
    else:
        try:
            writer = pypdf.PdfWriter()
            for p in pages:
                writer.add_page(reader.pages[p - 1])
            with doc.bench_pdf.open("wb") as f:
                writer.write(f)
        except RecursionError:
            # Very large manuals (e.g. PostgreSQL's 3,100 pages) have link annotations that point all over
            # the document; pypdf follows them while copying. pdfium imports the pages without that.
            import pypdfium2 as pdfium
            out = pdfium.PdfDocument.new()
            out.import_pages(pdfium.PdfDocument(str(src)), [p - 1 for p in pages])
            out.save(str(doc.bench_pdf))
    doc.page_map_path.write_text(json.dumps(pages))
    return doc.bench_pdf


def _build_scan(src: Path, pages: list[int], dest: Path, t: dict) -> None:
    """Render pages to images and degrade them like a photocopy/scan (deterministic)."""
    import img2pdf
    import numpy as np
    import pypdfium2 as pdfium
    from PIL import Image

    rng = random.Random(t.get("seed", 0))
    np_rng = np.random.default_rng(t.get("seed", 0))
    pdf = pdfium.PdfDocument(str(src))
    images = []
    for p in pages:
        img = pdf[p - 1].render(scale=t.get("dpi", 150) / 72).to_pil().convert("L")
        angle = t.get("rotate_deg", 0.5) * (1 if rng.random() > 0.5 else -1)
        img = img.rotate(angle, resample=Image.BICUBIC, expand=False, fillcolor=255)
        arr = np.asarray(img).astype(np.float32)
        arr += np_rng.normal(0, t.get("noise_sigma", 5), arr.shape)
        img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=t.get("jpeg_quality", 60))
        images.append(buf.getvalue())
    dest.write_bytes(img2pdf.convert(images))


def build_all() -> list[Path]:
    return [build(d) for d in load_manifest()]
