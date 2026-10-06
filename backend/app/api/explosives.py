from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import CurrentUser
from app.domain.enums import ExplosiveFlag
from app.domain.models import ExplosiveLog
from app.services import explosives

router = APIRouter()


class ExplosiveLogOut(BaseModel):
    id: uuid.UUID
    mine_id: uuid.UUID
    bench_id: uuid.UUID | None
    log_date: datetime
    explosives_kg: Decimal
    ob_m3: Decimal
    coal_tonnes: Decimal
    kg_per_m3: Decimal
    baseline_kg_per_m3: Decimal
    deviation_pct: Decimal
    flag: ExplosiveFlag
    notes: str

    model_config = {"from_attributes": True}


class CreateLogRequest(BaseModel):
    mine_id: uuid.UUID
    bench_id: uuid.UUID | None = None
    log_date: datetime
    explosives_kg: Decimal
    ob_m3: Decimal
    coal_tonnes: Decimal = Decimal("0")
    notes: str = ""


@router.get("/logs", response_model=list[ExplosiveLogOut])
async def list_logs(
    mine_id: uuid.UUID | None = None,
    flag: ExplosiveFlag | None = None,
    limit: int = Query(default=100, le=500),
    user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
):
    q = select(ExplosiveLog).order_by(ExplosiveLog.log_date.desc()).limit(limit)
    if mine_id:
        q = q.where(ExplosiveLog.mine_id == mine_id)
    if flag:
        q = q.where(ExplosiveLog.flag == flag)
    rows = (await db.execute(q)).scalars().all()
    return [ExplosiveLogOut.model_validate(r) for r in rows]


@router.post("/logs", response_model=ExplosiveLogOut)
async def create_log(body: CreateLogRequest, user: CurrentUser, db: AsyncSession = Depends(get_db)):
    if body.ob_m3 <= 0:
        raise HTTPException(422, "ob_m3 must be positive")
    if body.explosives_kg < 0:
        raise HTTPException(422, "explosives_kg cannot be negative")
    log = ExplosiveLog(
        mine_id=body.mine_id,
        bench_id=body.bench_id,
        log_date=body.log_date,
        explosives_kg=body.explosives_kg,
        ob_m3=body.ob_m3,
        coal_tonnes=body.coal_tonnes,
        notes=body.notes,
    )
    db.add(log)
    await db.flush()
    return log


@router.post("/analyze")
async def analyze(mine_id: uuid.UUID | None = None, user: CurrentUser = None, db: AsyncSession = Depends(get_db)):
    """Recompute kg/m3, baselines and flags; returns flagged anomalies."""
    return await explosives.analyze_logs(db, mine_id)
