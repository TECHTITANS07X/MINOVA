from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import AnomalyOut, AnomalyReviewRequest, Page, StatusResponse
from app.core.database import get_db
from app.core.security import CurrentUser
from app.domain.enums import AnomalyStatus
from app.domain.models import AnomalyFlag

router = APIRouter()


@router.get("", response_model=Page)
async def list_anomalies(
    user: CurrentUser,
    mine_id: uuid.UUID | None = None,
    anomaly_status: AnomalyStatus | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    cursor: str | None = None,
    limit: int = Query(default=50, le=200),
    db: AsyncSession = Depends(get_db),
):
    q = select(AnomalyFlag)
    if mine_id:
        q = q.where(AnomalyFlag.mine_id == mine_id)
    if anomaly_status:
        q = q.where(AnomalyFlag.status == anomaly_status)
    if date_from:
        q = q.where(AnomalyFlag.flag_date >= date_from)
    if date_to:
        q = q.where(AnomalyFlag.flag_date <= date_to)
    if cursor:
        q = q.where(AnomalyFlag.id > uuid.UUID(cursor))

    q = q.order_by(AnomalyFlag.flag_date.desc()).limit(limit + 1)
    rows = (await db.execute(q)).scalars().all()
    has_more = len(rows) > limit
    items = rows[:limit]
    return Page(
        items=[AnomalyOut.model_validate(a) for a in items],
        total=len(items),
        cursor=str(items[-1].id) if items else None,
        has_more=has_more,
    )


@router.get("/{anomaly_id}", response_model=AnomalyOut)
async def get_anomaly(
    anomaly_id: uuid.UUID,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(AnomalyFlag).where(AnomalyFlag.id == anomaly_id))
    flag = result.scalar_one_or_none()
    if not flag:
        raise HTTPException(404, "Anomaly flag not found")
    return flag


@router.post("/{anomaly_id}/review", response_model=StatusResponse)
async def review_anomaly(
    anomaly_id: uuid.UUID,
    body: AnomalyReviewRequest,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(AnomalyFlag).where(AnomalyFlag.id == anomaly_id))
    flag = result.scalar_one_or_none()
    if not flag:
        raise HTTPException(404, "Anomaly flag not found")
    if flag.status != AnomalyStatus.FLAGGED:
        raise HTTPException(400, f"Anomaly already reviewed ({flag.status.value})")

    if body.status == AnomalyStatus.DISMISSED and not body.reason.strip():
        raise HTTPException(400, "Dismissal requires a reason")

    flag.status = body.status
    flag.review_reason = body.reason
    flag.linked_cause_id = body.linked_cause_id

    return StatusResponse(status=body.status.value, message=f"Anomaly {body.status.value}")


@router.get("/{anomaly_id}/narrative")
async def anomaly_narrative(
    anomaly_id: uuid.UUID,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """Smart narrative: a probable explanation with evidence citations, built by
    cross-referencing cause records, weather, similar events and target pressure."""
    from app.services import anomaly_narrative

    result = await db.execute(select(AnomalyFlag).where(AnomalyFlag.id == anomaly_id))
    flag = result.scalar_one_or_none()
    if not flag:
        raise HTTPException(404, "Anomaly flag not found")
    return await anomaly_narrative.build_narrative(db, flag)
