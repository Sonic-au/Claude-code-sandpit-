"""Parser registry. `get_parsers()` returns adapters by name; `all_parsers()` lists every known one."""
from __future__ import annotations

from .base import ParseResult, Parser
from .local import (Docling, LiteParse, LiteParseMarkdown, Marker, MinerU, PyMuPDF4LLM, PypdfText,
                    UnstructuredOSS)
from .remote import AzureDocumentIntelligence, ClaudeVLM, LlamaParseAPI, OpenAICompatibleVLM, ReductoAPI
from .router import TenderRouter

FACTORIES = {
    "pypdf-text": PypdfText,
    "pymupdf4llm": PyMuPDF4LLM,
    "docling": Docling,
    "docling-forceocr": lambda: Docling(force_ocr=True),
    "liteparse": LiteParse,
    "liteparse-md": LiteParseMarkdown,
    "mineru": MinerU,
    "marker": Marker,
    "unstructured-fast": lambda: UnstructuredOSS("fast"),
    "unstructured-hi_res": lambda: UnstructuredOSS("hi_res"),
    "azure-di-layout": AzureDocumentIntelligence,
    "vlm": OpenAICompatibleVLM,
    "claude-vlm": ClaudeVLM,
    "llamaparse": LlamaParseAPI,
    "reducto": ReductoAPI,
    "router": TenderRouter,
}


def get_parser(name: str) -> Parser:
    if name not in FACTORIES:
        raise KeyError(f"unknown parser '{name}'. Known: {', '.join(FACTORIES)}")
    return FACTORIES[name]()


def all_parsers() -> list[Parser]:
    return [f() for f in FACTORIES.values()]


__all__ = ["Parser", "ParseResult", "get_parser", "all_parsers", "FACTORIES"]
