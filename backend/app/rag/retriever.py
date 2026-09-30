"""
Hybrid retriever: dense (BGE-M3 cosine) + keyword (pg_trgm + tsvector).
Fused via Reciprocal Rank Fusion (RRF).
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy import select, text, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models import DocChunk, Document
from app.rag.embedder import embed_query


@dataclass
class RetrievedChunk:
    chunk_id: str
    document_id: str
    text: str
    score: float
    page_number: int | None
    filename: str


async def hybrid_search(
    db: AsyncSession,
    query: str,
    mine_id: str | None = None,
    top_k: int = 10,
    rrf_k: int = 60,
) -> list[RetrievedChunk]:
    query_embedding = await embed_query(query)

    dense_results = await _dense_search(db, query_embedding, mine_id, top_k=top_k * 2)
    keyword_results = await _keyword_search(db, query, mine_id, top_k=top_k * 2)

    dense_ranks = {r["chunk_id"]: i + 1 for i, r in enumerate(dense_results)}
    keyword_ranks = {r["chunk_id"]: i + 1 for i, r in enumerate(keyword_results)}

    all_ids = set(dense_ranks.keys()) | set(keyword_ranks.keys())
    scored = []
    for cid in all_ids:
        dr = dense_ranks.get(cid, len(dense_results) + rrf_k)
        kr = keyword_ranks.get(cid, len(keyword_results) + rrf_k)
        rrf_score = 1.0 / (rrf_k + dr) + 1.0 / (rrf_k + kr)
        scored.append((cid, rrf_score))

    scored.sort(key=lambda x: x[1], reverse=True)
    top_ids = [s[0] for s in scored[:top_k]]

    if not top_ids:
        return []

    result = await db.execute(
        select(DocChunk, Document.filename)
        .join(Document, DocChunk.document_id == Document.id)
        .where(DocChunk.id.in_([uuid.UUID(i) for i in top_ids]))
    )
    rows = result.all()

    chunk_map = {str(row[0].id): row for row in rows}
    results = []
    for cid, score in scored[:top_k]:
        if cid in chunk_map:
            chunk, filename = chunk_map[cid]
            results.append(RetrievedChunk(
                chunk_id=cid,
                document_id=str(chunk.document_id),
                text=chunk.text,
                score=score,
                page_number=chunk.page_number,
                filename=filename,
            ))
    return results


async def _dense_search(db: AsyncSession, query_embedding: list[float], mine_id: str | None, top_k: int) -> list[dict]:
    result = await db.execute(
        select(DocChunk.id, DocChunk.embedding)
        .where(DocChunk.embedding.isnot(None))
        .limit(top_k * 5)
    )
    rows = result.all()

    import numpy as np
    q = np.array(query_embedding)
    scored = []
    for row in rows:
        if row.embedding:
            v = np.array(row.embedding)
            cos = float(np.dot(q, v) / (np.linalg.norm(q) * np.linalg.norm(v) + 1e-10))
            scored.append({"chunk_id": str(row.id), "score": cos})

    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:top_k]


async def _keyword_search(db: AsyncSession, query: str, mine_id: str | None, top_k: int) -> list[dict]:
    result = await db.execute(
        select(DocChunk.id, func.ts_rank(DocChunk.tsv, func.plainto_tsquery("english", query)).label("rank"))
        .where(DocChunk.tsv.op("@@")(func.plainto_tsquery("english", query)))
        .order_by(text("rank DESC"))
        .limit(top_k)
    )
    rows = result.all()
    return [{"chunk_id": str(row.id), "score": float(row.rank)} for row in rows]
