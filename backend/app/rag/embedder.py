"""
BGE-M3 embedding service for document chunks.
Produces 1024-dim dense vectors for pgvector cosine search.
"""
from __future__ import annotations

import os
from functools import lru_cache

import structlog

from app.core.config import settings

logger = structlog.get_logger()

# Model cache location is configurable; defaults to a repo-local directory.
os.environ.setdefault("HF_HOME", settings.hf_home)
os.environ.setdefault("HF_HUB_CACHE", os.path.join(settings.hf_home, "hub"))

_model = None


def _get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer("BAAI/bge-m3")
        logger.info("embedder.model_loaded", model="BAAI/bge-m3", dim=1024)
    return _model


async def embed_chunks(texts: list[str], batch_size: int = 32) -> list[list[float]]:
    model = _get_model()
    all_embeddings = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        embeddings = model.encode(batch, normalize_embeddings=True)
        all_embeddings.extend(emb.tolist() for emb in embeddings)
    return all_embeddings


async def embed_query(text: str) -> list[float]:
    model = _get_model()
    embedding = model.encode([text], normalize_embeddings=True)
    return embedding[0].tolist()
