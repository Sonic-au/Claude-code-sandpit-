#!/usr/bin/env python3
"""Cut the diagrams out of each manual's pages for the technician app.

  python scripts/export_figures.py <app_dir>

Finds figures on each bench page from the PDF itself (embedded images and clusters of vector drawing), skips page
backgrounds, rules and tables, and writes <app_dir>/figures/<doc>/<page>_<n>.jpg plus <app_dir>/figures.json
({doc: {page: [{file, w, h}]}}). No model is used.
"""
import json
import sys
from pathlib import Path

import fitz  # PyMuPDF

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from manual_app.corpus import load_manifest, manifest_path  # noqa: E402

CORPORA = ("manuals", "techmanualqa", "hvac")
MAX_PER_PAGE = 4


def _merge(rects: list) -> list:
    rects = [fitz.Rect(r) for r in rects]
    merged = True
    while merged:
        merged = False
        for i in range(len(rects)):
            for j in range(i + 1, len(rects)):
                if (rects[i] + (-8, -8, 8, 8)).intersects(rects[j]):
                    rects[i] |= rects[j]
                    rects.pop(j)
                    merged = True
                    break
            if merged:
                break
    return rects


def page_figures(page) -> list:
    pr = page.rect
    cands = []
    for img in page.get_images(full=True):
        cands += [r for r in page.get_image_rects(img[0]) if not r.is_empty]
    try:
        cands += page.cluster_drawings(x_tolerance=6, y_tolerance=6)
    except Exception:
        pass
    words = page.get_text("words")
    out = []
    for r in _merge([r & pr for r in cands]):
        if r.width < 0.2 * pr.width or r.height < 0.09 * pr.height:
            continue                                   # logos, icons, rules
        if r.get_area() > 0.8 * pr.get_area():
            continue                                   # page background or a scanned page
        inside = [w for w in words if fitz.Rect(w[:4]).intersects(r)]
        if len(inside) > 45 and len(inside) / max(1.0, r.get_area()) > 0.0009:
            continue                                   # a ruled table or text box, already in the parsed text
        out.append(r)
    out.sort(key=lambda r: -r.get_area())
    return sorted(out[:MAX_PER_PAGE], key=lambda r: (r.y0, r.x0))


def main() -> None:
    out = Path(sys.argv[1])
    index, total = {}, 0
    for corpus in CORPORA:
        for doc in load_manifest(manifest_path(corpus)):
            if doc.id.endswith("_scan"):
                continue
            pdf, pages = fitz.open(doc.bench_pdf), doc.page_map()
            d = out / "figures" / doc.id
            d.mkdir(parents=True, exist_ok=True)
            for old in d.glob("*.jpg"):
                old.unlink()
            per = {}
            for page, src in zip(pdf, pages):
                figs = []
                for n, r in enumerate(page_figures(page)):
                    pix = page.get_pixmap(clip=(r + (-6, -6, 6, 6)) & page.rect, dpi=120, alpha=False)
                    name = f"{src}_{n}.jpg"
                    pix.pil_save(d / name, format="JPEG", quality=72, optimize=True)
                    figs.append({"file": name, "w": pix.width, "h": pix.height})
                if figs:
                    per[str(src)] = figs
                    total += len(figs)
            index[doc.id] = per
            print(f"{doc.id}: {sum(len(v) for v in per.values())} figures on {len(per)} of {len(pages)} pages")
    (out / "figures.json").write_text(json.dumps(index, separators=(",", ":")))
    print(f"wrote {total} figures")


if __name__ == "__main__":
    main()
