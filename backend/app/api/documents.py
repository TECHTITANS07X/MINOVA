from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from minio import Minio
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.schemas import (
    DocumentOut,
    DocumentUploadRequest,
    ExtractedValueOut,
    Page,
    PresignedUrlResponse,
    SearchHit,
    SearchRequest,
    StagingReviewRequest,
    StatusResponse,
)
from app.core.config import settings
from app.core.database import get_db
from app.core.security import CurrentUser
from app.domain.enums import DocumentCategory, DocumentType, IngestionStatus, StagingReviewStatus
from app.domain.models import DocChunk, Document, DocumentPage, ExtractedTable, ExtractedValueStaging

router = APIRouter()

UPLOAD_DIR = Path(settings.storage_root)


def _get_minio() -> Minio:
    return Minio(
        settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=settings.minio_secure,
    )


@router.post("/upload", response_model=PresignedUrlResponse)
async def request_upload(
    body: DocumentUploadRequest,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    doc_id = uuid.uuid4()
    ext = body.filename.rsplit(".", 1)[-1] if "." in body.filename else "bin"
    object_key = f"uploads/{doc_id}.{ext}"

    doc = Document(
        id=doc_id,
        filename=body.filename,
        doc_type=body.doc_type,
        category=body.category,
        mine_id=body.mine_id,
        object_key=object_key,
        size_bytes=body.size_bytes,
        checksum_sha256="",
        ingestion_status=IngestionStatus.UPLOADED,
    )
    db.add(doc)
    await db.flush()

    client = _get_minio()
    url = client.presigned_put_object(
        settings.minio_bucket_documents,
        object_key,
        expires=timedelta(hours=1),
    )

    return PresignedUrlResponse(upload_url=url, object_key=object_key, document_id=doc_id)


@router.post("/upload/file", response_model=DocumentOut)
async def upload_file(
    file: UploadFile = File(...),
    doc_type: str = Form("other"),
    category: str = Form("general"),
    mine_id: str | None = Form(None),
    user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
):
    doc_id = uuid.uuid4()
    ext = file.filename.rsplit(".", 1)[-1] if file.filename and "." in file.filename else "bin"
    object_key = f"uploads/{doc_id}.{ext}"

    upload_path = UPLOAD_DIR / object_key
    upload_path.parent.mkdir(parents=True, exist_ok=True)

    content = await file.read()
    checksum = hashlib.sha256(content).hexdigest()
    upload_path.write_bytes(content)

    try:
        dtype = DocumentType(doc_type)
    except ValueError:
        dtype = DocumentType.OTHER
    try:
        dcat = DocumentCategory(category)
    except ValueError:
        dcat = DocumentCategory.GENERAL

    doc = Document(
        id=doc_id,
        filename=file.filename or f"upload.{ext}",
        doc_type=dtype,
        category=dcat,
        mine_id=uuid.UUID(mine_id) if mine_id else None,
        object_key=object_key,
        size_bytes=len(content),
        checksum_sha256=checksum,
        ingestion_status=IngestionStatus.UPLOADED,
    )
    db.add(doc)
    await db.flush()
    return DocumentOut.model_validate(doc)


@router.get("", response_model=Page)
async def list_documents(
    user: CurrentUser,
    category: DocumentCategory | None = None,
    mine_id: uuid.UUID | None = None,
    ingestion_status: IngestionStatus | None = None,
    cursor: str | None = None,
    limit: int = Query(default=50, le=200),
    db: AsyncSession = Depends(get_db),
):
    q = select(Document)
    if category:
        q = q.where(Document.category == category)
    if mine_id:
        q = q.where(Document.mine_id == mine_id)
    if ingestion_status:
        q = q.where(Document.ingestion_status == ingestion_status)
    if cursor:
        q = q.where(Document.id > uuid.UUID(cursor))
    q = q.order_by(Document.created_at.desc()).limit(limit + 1)

    rows = (await db.execute(q)).scalars().all()
    has_more = len(rows) > limit
    items = rows[:limit]
    return Page(
        items=[DocumentOut.model_validate(d) for d in items],
        total=len(items),
        cursor=str(items[-1].id) if items else None,
        has_more=has_more,
    )


@router.get("/{document_id}", response_model=DocumentOut)
async def get_document(
    document_id: uuid.UUID,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Document).where(Document.id == document_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(404, "Document not found")
    return doc


@router.get("/{document_id}/pages")
async def get_pages(
    document_id: uuid.UUID,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(DocumentPage)
        .where(DocumentPage.document_id == document_id)
        .order_by(DocumentPage.page_number)
    )
    pages = result.scalars().all()
    return [
        {
            "id": str(p.id),
            "page_number": p.page_number,
            "text_content": p.text_content,
            "ocr_confidence": float(p.ocr_confidence) if p.ocr_confidence else None,
        }
        for p in pages
    ]


@router.post("/search", response_model=list[SearchHit])
async def search_documents(
    body: SearchRequest,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    keyword_sql = text("""
        SELECT dc.id, dc.document_id, dc.page_number, dc.text,
               ts_rank(dc.tsv, websearch_to_tsquery('english', :query)) AS rank
        FROM doc_chunk dc
        JOIN document d ON d.id = dc.document_id
        WHERE dc.tsv @@ websearch_to_tsquery('english', :query)
        ORDER BY rank DESC
        LIMIT :lim
    """)
    kw_result = await db.execute(keyword_sql, {"query": body.query, "lim": body.limit * 2})
    kw_rows = kw_result.fetchall()

    kw_scores: dict[uuid.UUID, float] = {}
    chunks_by_id: dict[uuid.UUID, dict] = {}
    for idx, row in enumerate(kw_rows):
        cid = row[0]
        kw_scores[cid] = 1.0 / (60.0 + idx)
        chunks_by_id[cid] = {
            "chunk_id": cid,
            "document_id": row[1],
            "page_number": row[2],
            "text": row[3],
        }

    all_ids = set(kw_scores.keys())
    fused: dict[uuid.UUID, float] = {}
    for cid in all_ids:
        fused[cid] = kw_scores.get(cid, 0.0)

    ranked = sorted(fused.items(), key=lambda x: x[1], reverse=True)[: body.limit]

    doc_ids = [chunks_by_id[cid]["document_id"] for cid, _ in ranked if cid in chunks_by_id]
    doc_result = await db.execute(select(Document).where(Document.id.in_(doc_ids)))
    docs_map = {d.id: d for d in doc_result.scalars().all()}

    hits: list[SearchHit] = []
    for cid, score in ranked:
        info = chunks_by_id.get(cid)
        if not info:
            continue
        doc = docs_map.get(info["document_id"])
        hits.append(SearchHit(
            chunk_id=cid,
            document_id=info["document_id"],
            filename=doc.filename if doc else "",
            page_number=info["page_number"],
            text=info["text"][:500],
            score=round(score, 6),
        ))

    return hits


@router.get("/{document_id}/tables")
async def get_extracted_tables(
    document_id: uuid.UUID,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ExtractedTable)
        .where(ExtractedTable.document_id == document_id)
        .order_by(ExtractedTable.page_number)
    )
    tables = result.scalars().all()
    return [
        {
            "id": str(t.id),
            "page_number": t.page_number,
            "table_data": t.table_data,
            "confidence": float(t.confidence) if t.confidence else None,
        }
        for t in tables
    ]


@router.get("/{document_id}/staging", response_model=list[ExtractedValueOut])
async def get_staging_values(
    document_id: uuid.UUID,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ExtractedValueStaging).where(ExtractedValueStaging.document_id == document_id)
    )
    return result.scalars().all()


@router.post("/staging/{value_id}/review", response_model=StatusResponse)
async def review_staging_value(
    value_id: uuid.UUID,
    body: StagingReviewRequest,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ExtractedValueStaging).where(ExtractedValueStaging.id == value_id)
    )
    sv = result.scalar_one_or_none()
    if not sv:
        raise HTTPException(404, "Staging value not found")
    if sv.review_status != StagingReviewStatus.PENDING:
        raise HTTPException(400, "Already reviewed")

    sv.review_status = body.status
    sv.accepted_value = body.accepted_value
    sv.reviewed_at = datetime.now(timezone.utc)

    return StatusResponse(status="reviewed", message=f"Value {body.status.value}")
