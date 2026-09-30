from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import structlog

logger = structlog.get_logger()

_ocr_engine = None
_embed_model = None


@dataclass
class PageResult:
    page_num: int
    text: str
    tables: list[list[list[str]]] = field(default_factory=list)
    confidence: float = 0.0


@dataclass
class SearchResult:
    chunk_id: str
    text: str
    score: float
    source_doc: str
    page_num: int | None = None


def _get_ocr():
    global _ocr_engine
    if _ocr_engine is None:
        try:
            from paddleocr import PaddleOCR
            _ocr_engine = PaddleOCR(use_angle_cls=True, lang="en", use_gpu=False, show_log=False)
            logger.info("ocr.paddleocr_loaded")
        except ImportError:
            logger.warning("ocr.paddleocr_not_installed")
            return None
    return _ocr_engine


def _get_embed_model():
    global _embed_model
    if _embed_model is None:
        try:
            from sentence_transformers import SentenceTransformer
            _embed_model = SentenceTransformer("BAAI/bge-m3", device="cpu")
            logger.info("embeddings.bge_m3_loaded")
        except ImportError:
            logger.warning("embeddings.sentence_transformers_not_installed")
            return None
    return _embed_model


def extract_text_ocr(file_bytes: bytes, lang: str = "en") -> list[PageResult]:
    try:
        import fitz  # PyMuPDF
    except ImportError:
        logger.warning("ocr.pymupdf_not_installed")
        return []

    doc = fitz.open(stream=file_bytes, filetype="pdf")
    pages = []
    for i, page in enumerate(doc):
        text = page.get_text("text")
        tables_raw: list[list[list[str]]] = []

        if not text.strip():
            ocr = _get_ocr()
            if ocr:
                pix = page.get_pixmap(dpi=200)
                img_bytes = pix.tobytes("png")
                import tempfile, os
                with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
                    f.write(img_bytes)
                    tmp = f.name
                try:
                    result = ocr.ocr(tmp, cls=True)
                    if result and result[0]:
                        text = "\n".join(line[1][0] for line in result[0] if line[1])
                finally:
                    os.unlink(tmp)

        pages.append(PageResult(page_num=i + 1, text=text, tables=tables_raw, confidence=0.9 if text.strip() else 0.0))
    doc.close()
    return pages


def chunk_text(text: str, chunk_size: int = 512, overlap: int = 64) -> list[str]:
    words = text.split()
    if not words:
        return []
    chunks = []
    start = 0
    while start < len(words):
        end = start + chunk_size
        chunks.append(" ".join(words[start:end]))
        start = end - overlap
    return chunks


def generate_embeddings(texts: list[str]) -> list[list[float]]:
    model = _get_embed_model()
    if model is None:
        return [[0.0] * 1024 for _ in texts]
    embeddings = model.encode(texts, normalize_embeddings=True)
    return [e.tolist() for e in embeddings]


def cosine_similarity(a: list[float], b: list[float]) -> float:
    a_arr = np.array(a)
    b_arr = np.array(b)
    dot = np.dot(a_arr, b_arr)
    norm = np.linalg.norm(a_arr) * np.linalg.norm(b_arr)
    if norm < 1e-9:
        return 0.0
    return float(dot / norm)


async def hybrid_search(
    query: str,
    chunks: list[dict],
    limit: int = 10,
    text_weight: float = 0.4,
    vector_weight: float = 0.6,
) -> list[SearchResult]:
    query_lower = query.lower()
    query_terms = set(query_lower.split())

    query_embedding = generate_embeddings([query])[0]

    scored = []
    for c in chunks:
        text_score = 0.0
        chunk_lower = c.get("text", "").lower()
        matching_terms = sum(1 for t in query_terms if t in chunk_lower)
        if query_terms:
            text_score = matching_terms / len(query_terms)

        vec_score = 0.0
        if c.get("embedding"):
            vec_score = cosine_similarity(query_embedding, c["embedding"])

        combined = text_weight * text_score + vector_weight * vec_score
        scored.append((combined, c))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [
        SearchResult(
            chunk_id=c.get("id", ""),
            text=c.get("text", ""),
            score=score,
            source_doc=c.get("document_id", ""),
            page_num=c.get("page_number"),
        )
        for score, c in scored[:limit]
    ]
