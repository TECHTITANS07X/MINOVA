"""
Temporal workflow for document ingestion pipeline.
Steps: download -> OCR -> chunk -> embed -> index.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import timedelta

from temporalio import activity, workflow

with workflow.unsafe.imports_passed_through():
    from app.core.database import async_session_factory
    from app.domain.models import Document, DocumentPage, DocChunk


@dataclass
class IngestionRequest:
    document_id: str
    object_key: str
    filename: str
    mine_id: str | None


@activity.defn
async def download_document(document_id: str, object_key: str) -> str:
    from app.services.storage import storage
    data = await storage.get_object("documents", object_key)
    import tempfile, os
    tmp = os.path.join(tempfile.gettempdir(), f"minova_doc_{document_id}")
    with open(tmp, "wb") as f:
        f.write(data)
    return tmp


@activity.defn
async def run_ocr(document_id: str, file_path: str, filename: str) -> list[dict]:
    pages = []
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    if ext in ("pdf", "png", "jpg", "jpeg", "tiff", "bmp"):
        try:
            from app.ocr.paddle_ocr import extract_text
            pages = await extract_text(file_path)
        except ImportError:
            pages = [{"page": 1, "text": f"[OCR not available] File: {filename}", "confidence": 0.0}]
    elif ext in ("csv", "xlsx", "xls"):
        pages = [{"page": 1, "text": f"[Spreadsheet] {filename}", "confidence": 1.0}]
    else:
        pages = [{"page": 1, "text": f"[Unsupported format] {filename}", "confidence": 0.0}]

    async with async_session_factory() as db:
        for p in pages:
            page = DocumentPage(
                id=uuid.uuid4(),
                document_id=uuid.UUID(document_id),
                page_number=p["page"],
                text_content=p["text"],
                ocr_confidence=p.get("confidence"),
            )
            db.add(page)
        await db.commit()

    return pages


@activity.defn
async def chunk_and_embed(document_id: str, pages: list[dict]) -> int:
    from app.rag.embedder import embed_chunks

    all_text = "\n\n".join(p["text"] for p in pages)
    chunks = []
    chunk_size = 512
    overlap = 64
    words = all_text.split()
    i = 0
    idx = 0
    while i < len(words):
        chunk_text = " ".join(words[i:i + chunk_size])
        if chunk_text.strip():
            chunks.append({"index": idx, "text": chunk_text})
            idx += 1
        i += chunk_size - overlap

    if not chunks:
        return 0

    try:
        embeddings = await embed_chunks([c["text"] for c in chunks])
    except Exception:
        embeddings = [None] * len(chunks)

    async with async_session_factory() as db:
        from datetime import datetime, timezone
        for c, emb in zip(chunks, embeddings):
            doc_chunk = DocChunk(
                id=uuid.uuid4(),
                document_id=uuid.UUID(document_id),
                chunk_index=c["index"],
                text=c["text"],
                embedding=emb,
                metadata_json={},
                created_at=datetime.now(timezone.utc),
            )
            db.add(doc_chunk)
        await db.commit()

    return len(chunks)


@activity.defn
async def index_chunks(document_id: str) -> None:
    async with async_session_factory() as db:
        from sqlalchemy import text
        await db.execute(text("""
            UPDATE doc_chunk SET tsv = to_tsvector('english', text)
            WHERE document_id = :doc_id AND tsv IS NULL
        """), {"doc_id": document_id})
        await db.commit()


@activity.defn
async def update_ingestion_status(document_id: str, status: str) -> None:
    from sqlalchemy import update
    async with async_session_factory() as db:
        await db.execute(
            update(Document)
            .where(Document.id == uuid.UUID(document_id))
            .values(ingestion_status=status)
        )
        await db.commit()


@workflow.defn
class IngestionWorkflow:
    @workflow.run
    async def run(self, request: IngestionRequest) -> dict:
        await workflow.execute_activity(
            update_ingestion_status,
            args=[request.document_id, "PROCESSING"],
            start_to_close_timeout=timedelta(seconds=30),
        )

        file_path = await workflow.execute_activity(
            download_document,
            args=[request.document_id, request.object_key],
            start_to_close_timeout=timedelta(seconds=120),
        )

        pages = await workflow.execute_activity(
            run_ocr,
            args=[request.document_id, file_path, request.filename],
            start_to_close_timeout=timedelta(minutes=10),
        )

        await workflow.execute_activity(
            update_ingestion_status,
            args=[request.document_id, "OCR_COMPLETE"],
            start_to_close_timeout=timedelta(seconds=30),
        )

        chunk_count = await workflow.execute_activity(
            chunk_and_embed,
            args=[request.document_id, pages],
            start_to_close_timeout=timedelta(minutes=15),
        )

        await workflow.execute_activity(
            update_ingestion_status,
            args=[request.document_id, "EMBEDDED"],
            start_to_close_timeout=timedelta(seconds=30),
        )

        await workflow.execute_activity(
            index_chunks,
            args=[request.document_id],
            start_to_close_timeout=timedelta(seconds=60),
        )

        await workflow.execute_activity(
            update_ingestion_status,
            args=[request.document_id, "INDEXED"],
            start_to_close_timeout=timedelta(seconds=30),
        )

        return {
            "status": "indexed",
            "pages": len(pages),
            "chunks": chunk_count,
        }
