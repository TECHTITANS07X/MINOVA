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
from app.domain.enums import ComplianceAuthority, ComplianceFrequency, FilingStatus
from app.domain.models import ComplianceFiling, ComplianceObligation
from app.services import compliance as compliance_service

router = APIRouter()


class ObligationOut(BaseModel):
    id: uuid.UUID
    mine_id: uuid.UUID | None
    authority: ComplianceAuthority
    title: str
    description: str
    frequency: ComplianceFrequency
    due_day: int
    required_metrics: list

    model_config = {"from_attributes": True}


class FilingRow(BaseModel):
    obligation_id: str
    obligation_title: str
    authority: str
    frequency: str
    mine_id: str
    mine_name: str
    period_start: str
    period_end: str
    due_date: str
    due_in_days: int
    status: str
    completion_pct: float
    missing_metrics: list


class SyncResponse(BaseModel):
    filings: list[FilingRow]
    counts: dict
    synced_at: str


class CreateObligationRequest(BaseModel):
    authority: ComplianceAuthority
    title: str
    description: str = ""
    frequency: ComplianceFrequency
    due_day: int = 10
    required_metrics: list[str] = []
    mine_id: uuid.UUID | None = None


@router.get("/obligations", response_model=list[ObligationOut])
async def list_obligations(user: CurrentUser, db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(ComplianceObligation).where(ComplianceObligation.is_active))).scalars().all()
    return [ObligationOut.model_validate(r) for r in rows]


@router.post("/obligations", response_model=ObligationOut)
async def create_obligation(body: CreateObligationRequest, user: CurrentUser, db: AsyncSession = Depends(get_db)):
    if not 1 <= body.due_day <= 31:
        raise HTTPException(422, "due_day must be 1-31")
    obligation = ComplianceObligation(
        mine_id=body.mine_id,
        authority=body.authority,
        title=body.title,
        description=body.description,
        frequency=body.frequency,
        due_day=body.due_day,
        required_metrics=body.required_metrics,
    )
    db.add(obligation)
    await db.flush()
    return obligation


@router.post("/sync", response_model=SyncResponse)
async def sync(user: CurrentUser, db: AsyncSession = Depends(get_db)):
    """Recompute filing periods, deadlines and data completeness across all mines."""
    return await compliance_service.sync_filings(db, datetime.now(timezone.utc))


@router.get("/filings")
async def list_filings(
    mine_id: uuid.UUID | None = None,
    status: FilingStatus | None = None,
    user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
):
    """Latest synced filings (run POST /sync first for fresh status)."""
    q = select(ComplianceFiling).order_by(ComplianceFiling.due_date)
    if mine_id:
        q = q.where(ComplianceFiling.mine_id == mine_id)
    if status:
        q = q.where(ComplianceFiling.status == status)
    rows = (await db.execute(q)).scalars().all()
    obligations = {
        o.id: o for o in (await db.execute(select(ComplianceObligation))).scalars().all()
    }
    from app.domain.models import Mine

    mines = {m.id: m.name for m in (await db.execute(select(Mine))).scalars().all()}
    out = []
    for f in rows:
        o = obligations.get(f.obligation_id)
        out.append({
            "filing_id": str(f.id),
            "obligation_title": o.title if o else str(f.obligation_id),
            "authority": o.authority.value if o else None,
            "frequency": o.frequency.value if o else None,
            "mine_id": str(f.mine_id),
            "mine_name": mines.get(f.mine_id, str(f.mine_id)),
            "period_start": f.period_start.date().isoformat(),
            "period_end": f.period_end.date().isoformat(),
            "due_date": f.due_date.date().isoformat(),
            "due_in_days": (f.due_date - datetime.now(timezone.utc)).days,
            "status": f.status.value,
            "completion_pct": float(f.completion_pct),
            "missing_metrics": f.missing_metrics,
            "submitted_at": f.submitted_at.isoformat() if f.submitted_at else None,
        })
    out.sort(key=lambda d: (d["status"] != "late", d["status"] != "incomplete", d["due_in_days"]))
    return out


@router.post("/filings/{filing_id}/submit")
async def submit_filing(filing_id: uuid.UUID, user: CurrentUser, db: AsyncSession = Depends(get_db)):
    try:
        filing = await compliance_service.mark_submitted(db, filing_id, None)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"status": "submitted", "filing_id": str(filing.id), "submitted_at": filing.submitted_at.isoformat()}
