from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import CurrentUser
from app.domain.enums import CauseType, LossRecoveryStatus, LossSourceType
from app.domain.models import LossLedgerEntry
from app.services import loss_ledger

router = APIRouter()


class LossLedgerEntryOut(BaseModel):
    id: uuid.UUID
    mine_id: uuid.UUID
    loss_date: datetime
    cause_type: CauseType
    description: str
    tonnes_lost: Decimal
    hours_lost: Decimal
    source_type: LossSourceType
    source_id: uuid.UUID | None
    recovery_status: LossRecoveryStatus
    recovered_tonnes: Decimal

    model_config = {"from_attributes": True}


class ManualLossRequest(BaseModel):
    mine_id: uuid.UUID
    loss_date: datetime
    cause_type: CauseType
    description: str
    tonnes_lost: Decimal
    hours_lost: Decimal = Decimal("0")


class RecoverRequest(BaseModel):
    recovered_tonnes: Decimal
    status: LossRecoveryStatus  # partial | recovered | waived
    note: str = ""


@router.post("/derive", response_model=list[LossLedgerEntryOut])
async def derive_entries(user: CurrentUser, db: AsyncSession = Depends(get_db)):
    """Derive ledger entries from all approved cause records not yet ledgered."""
    from app.domain.models import Mine

    mines = (await db.execute(select(Mine).where(Mine.is_active))).scalars().all()
    created = []
    for m in mines:
        created.extend(await loss_ledger.derive_from_cause_records(db, m.id))
    return created


@router.get("/summary")
async def summary(mine_id: uuid.UUID | None = None, user: CurrentUser = None, db: AsyncSession = Depends(get_db)):
    """Recovery debt: how much each mine is behind and why."""
    return await loss_ledger.debt_summary(db, mine_id)


@router.get("", response_model=list[LossLedgerEntryOut])
async def list_entries(
    mine_id: uuid.UUID | None = None,
    recovery_status: LossRecoveryStatus | None = None,
    limit: int = Query(default=100, le=500),
    user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
):
    q = select(LossLedgerEntry).order_by(LossLedgerEntry.loss_date.desc()).limit(limit)
    if mine_id:
        q = q.where(LossLedgerEntry.mine_id == mine_id)
    if recovery_status:
        q = q.where(LossLedgerEntry.recovery_status == recovery_status)
    rows = (await db.execute(q)).scalars().all()
    return [LossLedgerEntryOut.model_validate(r) for r in rows]


@router.post("", response_model=LossLedgerEntryOut)
async def create_manual(body: ManualLossRequest, user: CurrentUser, db: AsyncSession = Depends(get_db)):
    entry = LossLedgerEntry(
        mine_id=body.mine_id,
        loss_date=body.loss_date,
        cause_type=body.cause_type,
        description=body.description,
        tonnes_lost=body.tonnes_lost,
        hours_lost=body.hours_lost,
        source_type=LossSourceType.MANUAL,
    )
    db.add(entry)
    await db.flush()
    return entry


@router.post("/{entry_id}/recover", response_model=LossLedgerEntryOut)
async def recover(entry_id: uuid.UUID, body: RecoverRequest, user: CurrentUser, db: AsyncSession = Depends(get_db)):
    entry = await db.get(LossLedgerEntry, entry_id)
    if entry is None:
        raise HTTPException(404, "Ledger entry not found")
    if entry.recovery_status in (LossRecoveryStatus.RECOVERED, LossRecoveryStatus.WAIVED):
        raise HTTPException(400, "Entry already closed")
    if body.recovered_tonnes < 0 or body.recovered_tonnes > entry.tonnes_lost:
        raise HTTPException(422, "Recovered tonnes must be between 0 and the original loss")
    if body.status == LossRecoveryStatus.OPEN:
        raise HTTPException(422, "Status must be partial, recovered or waived")
    entry.recovered_tonnes = body.recovered_tonnes
    entry.recovery_status = body.status
    await db.flush()
    return entry
