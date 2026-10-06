from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import CurrentUser
from app.domain.enums import KnowledgeCategory
from app.domain.models import KnowledgeEntry

router = APIRouter()


class EntryCreate(BaseModel):
    mine_id: uuid.UUID | None = None
    category: KnowledgeCategory
    title: str
    content: str
    author_name: str
    author_designation: str = ""
    years_experience: int = 0
    tags: list[str] = []


class EntryOut(BaseModel):
    id: uuid.UUID
    mine_id: uuid.UUID | None
    category: KnowledgeCategory
    title: str
    content: str
    author_name: str
    author_designation: str
    years_experience: int
    tags: list
    is_verified: bool
    created_at: datetime

    model_config = {"from_attributes": True}


@router.get("/entries", response_model=list[EntryOut])
async def list_entries(
    mine_id: uuid.UUID | None = None,
    category: KnowledgeCategory | None = None,
    user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
):
    q = select(KnowledgeEntry).order_by(KnowledgeEntry.created_at.desc())
    if mine_id:
        q = q.where(KnowledgeEntry.mine_id == mine_id)
    if category:
        q = q.where(KnowledgeEntry.category == category)
    rows = (await db.execute(q)).scalars().all()
    return [EntryOut.model_validate(r) for r in rows]


@router.post("/entries", response_model=EntryOut, status_code=201)
async def create_entry(
    body: EntryCreate,
    user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
):
    entry = KnowledgeEntry(**body.model_dump())
    db.add(entry)
    await db.flush()
    return EntryOut.model_validate(entry)


@router.post("/entries/{entry_id}/verify")
async def verify_entry(
    entry_id: uuid.UUID,
    user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(KnowledgeEntry).where(KnowledgeEntry.id == entry_id))
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(404, "Knowledge entry not found")
    entry.is_verified = True
    await db.flush()
    return {"id": str(entry.id), "is_verified": True}


@router.get("/search")
async def search_entries(
    q: str = Query(..., min_length=1),
    mine_id: uuid.UUID | None = None,
    user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
):
    pattern = f"%{q}%"
    stmt = (
        select(KnowledgeEntry)
        .where(or_(KnowledgeEntry.title.ilike(pattern), KnowledgeEntry.content.ilike(pattern)))
        .order_by(KnowledgeEntry.created_at.desc())
        .limit(50)
    )
    if mine_id:
        stmt = stmt.where(KnowledgeEntry.mine_id == mine_id)
    rows = (await db.execute(stmt)).scalars().all()
    return [EntryOut.model_validate(r) for r in rows]
