"""Chunking and retrieval over one document's parsed pages.

Chunks never cross a page boundary, so every retrieved chunk carries a page citation.
Strategies: bm25, dense, hybrid (reciprocal rank fusion), and hybrid-ctx, which prefixes each
chunk with the document title and its heading path - a no-LLM form of contextual retrieval.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from .normalize import markdown_to_text

DENSE_MODEL = "BAAI/bge-small-en-v1.5"
_dense_cache: dict = {}


@dataclass
class Chunk:
    page: int
    text: str
    heading: str = ""


def chunk_pages(pages: list[str], page_map: list[int], max_chars: int = 1200) -> list[Chunk]:
    chunks = []
    heading = ""
    for md, page in zip(pages, page_map):
        buf = ""
        for block in re.split(r"\n\s*\n", md or ""):
            m = re.match(r"^\s{0,3}#{1,6}\s+(.*)", block.strip())
            if m:
                if buf.strip():
                    chunks.append(Chunk(page, buf.strip(), heading))
                    buf = ""
                heading = re.sub(r"[*_`]", "", m.group(1)).strip()
            block_txt = " ".join(markdown_to_text(block).split())
            if not block_txt:
                continue
            if len(buf) + len(block_txt) > max_chars and buf:
                chunks.append(Chunk(page, buf.strip(), heading))
                buf = ""
            while len(block_txt) > max_chars:
                chunks.append(Chunk(page, block_txt[:max_chars], heading))
                block_txt = block_txt[max_chars - 150:]   # overlap so a clause cut in two stays findable
            buf += " " + block_txt
        if buf.strip():
            chunks.append(Chunk(page, buf.strip(), heading))
    return chunks


def _tok(s: str) -> list[str]:
    return re.findall(r"[a-z0-9]+(?:[.%][0-9]+)?", s.lower())


def _rank_bm25(query: str, texts: list[str]) -> list[int]:
    from rank_bm25 import BM25Okapi
    bm = BM25Okapi([_tok(t) or ["_"] for t in texts])
    scores = bm.get_scores(_tok(query))
    return sorted(range(len(texts)), key=lambda i: -scores[i])


def _rank_dense(query: str, texts: list[str]) -> list[int]:
    from sentence_transformers import SentenceTransformer
    if DENSE_MODEL not in _dense_cache:
        _dense_cache[DENSE_MODEL] = SentenceTransformer(DENSE_MODEL, device="cpu")
    model = _dense_cache[DENSE_MODEL]
    q = model.encode(["Represent this sentence for searching relevant passages: " + query], normalize_embeddings=True)
    d = model.encode(texts, normalize_embeddings=True, batch_size=32)
    scores = (d @ q.T).ravel()
    return sorted(range(len(texts)), key=lambda i: -scores[i])


def _rrf(rankings: list[list[int]], k: int = 60) -> list[int]:
    score: dict[int, float] = {}
    for r in rankings:
        for pos, i in enumerate(r):
            score[i] = score.get(i, 0.0) + 1.0 / (k + pos + 1)
    return sorted(score, key=lambda i: -score[i])


def search(query: str, chunks: list[Chunk], strategy: str, title: str = "") -> list[Chunk]:
    if not chunks:
        return []
    if strategy == "hybrid-ctx":
        texts = [f"{title} | {c.heading} | {c.text}" for c in chunks]
    else:
        texts = [c.text for c in chunks]
    if strategy == "bm25":
        order = _rank_bm25(query, texts)
    elif strategy == "dense":
        order = _rank_dense(query, texts)
    elif strategy in ("hybrid", "hybrid-ctx"):
        order = _rrf([_rank_bm25(query, texts), _rank_dense(query, texts)])
    else:
        raise ValueError(strategy)
    return [chunks[i] for i in order]


ANSWER_PROMPT = """Answer the question using ONLY the numbered extracts from the tender "{title}".
Cite the extract numbers you used like [2]. If the extracts do not contain the answer, reply exactly
"NOT FOUND" and nothing else.

Question: {question}

Extracts:
{extracts}"""


def answer(llm, question: str, top: list[Chunk], title: str) -> tuple[str, list[int]]:
    ex = "\n\n".join(f"[{i + 1}] (page {c.page}) {c.text}" for i, c in enumerate(top))
    text = llm.complete(ANSWER_PROMPT.format(title=title, question=question, extracts=ex), max_tokens=800)
    cited = sorted({top[int(n) - 1].page for n in re.findall(r"\[(\d+)\]", text) if 0 < int(n) <= len(top)})
    return text.strip(), cited
