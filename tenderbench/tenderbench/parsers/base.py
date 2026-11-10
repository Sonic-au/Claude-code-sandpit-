"""Parser adapter interface.

Every adapter turns a bench PDF into one Markdown string per page. Per-page output is what
lets the bench score each page and cite a page in answers. Adapters declare where they
process data, so a run can exclude anything that sends documents offshore.
"""
from __future__ import annotations

import json
import shutil
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass
class ParseResult:
    parser: str
    doc_id: str
    pages: list[str]                 # Markdown per bench page, same order as the page map
    page_map: list[int]              # original page number of each bench page
    seconds: float
    cost_usd: float | None = None
    error: str | None = None
    meta: dict = field(default_factory=dict)

    def page(self, source_page: int) -> str:
        try:
            return self.pages[self.page_map.index(source_page)]
        except (ValueError, IndexError):
            return ""

    @property
    def full_markdown(self) -> str:
        return "\n\n".join(self.pages)

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(self), ensure_ascii=False, indent=1))

    @classmethod
    def load(cls, path: Path) -> "ParseResult":
        return cls(**json.loads(path.read_text()))


class Parser:
    """Subclass and implement `_parse`. Class attributes describe the tool for the report."""

    name: str = "base"
    licence: str = ""
    # Where documents are processed: "local" (this machine), "self-hosted", "cloud-au",
    # or "offshore" (e.g. a US/EU API). Offshore parsers are skipped unless explicitly allowed.
    residency: str = "local"
    cost_per_page_usd: float | None = 0.0
    notes: str = ""

    def available(self) -> tuple[bool, str]:
        """(True, "") if it can run here, else (False, reason)."""
        return True, ""

    def parse(self, pdf: Path, doc_id: str, page_map: list[int]) -> ParseResult:
        t0 = time.perf_counter()
        try:
            pages = self._parse(pdf, len(page_map))
            err = None
        except Exception as e:  # keep the run going; the report shows the failure
            pages, err = [""] * len(page_map), f"{type(e).__name__}: {e}"
        secs = time.perf_counter() - t0
        if len(pages) != len(page_map):
            err = (err or "") + f" | page count mismatch: got {len(pages)}, expected {len(page_map)}"
            pages = (pages + [""] * len(page_map))[: len(page_map)]
        cost = None if self.cost_per_page_usd is None else self.cost_per_page_usd * len(page_map)
        return ParseResult(self.name, doc_id, pages, page_map, secs, cost, err)

    def _parse(self, pdf: Path, n_pages: int) -> list[str]:
        raise NotImplementedError


def which(binary: str) -> str | None:
    return shutil.which(binary)
