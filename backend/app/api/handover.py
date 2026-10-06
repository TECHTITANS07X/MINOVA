from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import CurrentUser
from app.domain.enums import ShiftNumber
from app.domain.models import ShiftHandover
from app.services import handover as handover_service

router = APIRouter()


class ShiftHandoverOut(BaseModel):
    id: uuid.UUID
    mine_id: uuid.UUID
    shift_date: datetime
    outgoing_shift: ShiftNumber
    brief: dict
    critical_items: list
    generated_at: datetime
    acknowledged_at: datetime | None

    model_config = {"from_attributes": True}


class GenerateRequest(BaseModel):
    mine_id: uuid.UUID
    shift_date: datetime
    shift_number: ShiftNumber


@router.post("/generate", response_model=ShiftHandoverOut)
async def generate(body: GenerateRequest, user: CurrentUser, db: AsyncSession = Depends(get_db)):
    """Auto-generate the structured handover brief for the outgoing shift."""
    try:
        h = await handover_service.generate_brief(db, body.mine_id, body.shift_date, body.shift_number)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return h


@router.get("", response_model=list[ShiftHandoverOut])
async def list_handovers(
    mine_id: uuid.UUID | None = None,
    limit: int = Query(default=20, le=100),
    user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
):
    q = select(ShiftHandover).order_by(ShiftHandover.generated_at.desc()).limit(limit)
    if mine_id:
        q = q.where(ShiftHandover.mine_id == mine_id)
    rows = (await db.execute(q)).scalars().all()
    return [ShiftHandoverOut.model_validate(r) for r in rows]


@router.get("/{handover_id}", response_model=ShiftHandoverOut)
async def get_handover(handover_id: uuid.UUID, user: CurrentUser, db: AsyncSession = Depends(get_db)):
    h = await db.get(ShiftHandover, handover_id)
    if h is None:
        raise HTTPException(404, "Handover not found")
    return h


@router.post("/{handover_id}/acknowledge", response_model=ShiftHandoverOut)
async def acknowledge(handover_id: uuid.UUID, user: CurrentUser, db: AsyncSession = Depends(get_db)):
    """Incoming shift officer acknowledges the brief."""
    h = await db.get(ShiftHandover, handover_id)
    if h is None:
        raise HTTPException(404, "Handover not found")
    if h.acknowledged_at:
        raise HTTPException(400, "Handover already acknowledged")
    h.acknowledged_at = datetime.now(timezone.utc)
    await db.flush()
    return h
