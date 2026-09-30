from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import ConflictOut, ConflictResolveRequest, Page, StatusResponse
from app.core.database import get_db
from app.core.security import CurrentUser
from app.domain.enums import ConflictResolution
from app.domain.models import ConflictFlag

router = APIRouter()


@router.get("", response_model=Page)
async def list_conflicts(
    user: CurrentUser,
    resolution: ConflictResolution | None = None,
    entity_type: str | None = None,
    mine_id: uuid.UUID | None = None,
    cursor: str | None = None,
    limit: int = Query(default=50, le=200),
    db: AsyncSession = Depends(get_db),
):
    q = select(ConflictFlag)
    if resolution:
        q = q.where(ConflictFlag.resolution == resolution)
    if entity_type:
        q = q.where(ConflictFlag.entity_type == entity_type)
    if cursor:
        q = q.where(ConflictFlag.id > uuid.UUID(cursor))

    q = q.order_by(ConflictFlag.created_at.desc()).limit(limit + 1)
    rows = (await db.execute(q)).scalars().all()
    has_more = len(rows) > limit
    items = rows[:limit]
    return Page(
        items=[ConflictOut.model_validate(c) for c in items],
        total=len(items),
        cursor=str(items[-1].id) if items else None,
        has_more=has_more,
    )


@router.get("/{conflict_id}", response_model=ConflictOut)
async def get_conflict(
    conflict_id: uuid.UUID,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(ConflictFlag).where(ConflictFlag.id == conflict_id))
    conflict = result.scalar_one_or_none()
    if not conflict:
        raise HTTPException(404, "Conflict not found")
    return conflict


@router.post("/{conflict_id}/resolve", response_model=StatusResponse)
async def resolve_conflict(
    conflict_id: uuid.UUID,
    body: ConflictResolveRequest,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(ConflictFlag).where(ConflictFlag.id == conflict_id))
    conflict = result.scalar_one_or_none()
    if not conflict:
        raise HTTPException(404, "Conflict not found")
    if conflict.resolution != ConflictResolution.UNRESOLVED:
        raise HTTPException(400, "Conflict already resolved")
    if not body.reason.strip():
        raise HTTPException(400, "Resolution requires a mandatory reason")
    if body.resolution == ConflictResolution.UNRESOLVED:
        raise HTTPException(400, "Cannot set resolution to UNRESOLVED")

    conflict.resolution = body.resolution
    conflict.resolved_value = body.resolved_value
    conflict.resolution_reason = body.reason
    conflict.resolved_at = datetime.now(timezone.utc)

    return StatusResponse(status="resolved", message=f"Conflict resolved as {body.resolution.value}")
