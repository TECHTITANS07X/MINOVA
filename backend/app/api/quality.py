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
from app.domain.enums import QualityPredictionStatus, QualityRisk
from app.domain.models import Mine, QualityPrediction, QualitySample
from app.services import quality_correlation

router = APIRouter()


class QualitySampleOut(BaseModel):
    id: uuid.UUID
    mine_id: uuid.UUID
    sample_date: datetime
    gcv_kcal: Decimal
    grade: str
    source: str

    model_config = {"from_attributes": True}


class QualityPredictionOut(BaseModel):
    id: uuid.UUID
    mine_id: uuid.UUID
    prediction_date: datetime
    baseline_gcv: Decimal
    predicted_gcv: Decimal
    declared_gcv: Decimal
    deviation_pct: Decimal
    risk: QualityRisk
    status: QualityPredictionStatus
    basis: dict
    lab_gcv: Decimal | None
    lab_confirmed_at: datetime | None
    flagged_at: datetime | None

    model_config = {"from_attributes": True}


class PredictRequest(BaseModel):
    mine_id: uuid.UUID
    declared_gcv: Decimal
    bench_id: uuid.UUID | None = None


class ConfirmLabRequest(BaseModel):
    lab_gcv: Decimal


@router.get("/summary")
async def quality_summary(mine_id: uuid.UUID | None = None, user: CurrentUser = None, db: AsyncSession = Depends(get_db)):
    """Risk snapshot: flags raised BEFORE the UTTAM lab result arrives."""
    mines = {m.id: m.name for m in (await db.execute(select(Mine))).scalars().all()}
    summary = await quality_correlation.risk_summary(db, mine_id)
    summary["mines"] = {str(k): v for k, v in mines.items()}
    return summary


@router.get("/samples", response_model=list[QualitySampleOut])
async def list_samples(
    mine_id: uuid.UUID | None = None,
    limit: int = Query(default=100, le=500),
    user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
):
    """Historical UTTAM lab results used as the correlation baseline."""
    q = select(QualitySample).order_by(QualitySample.sample_date.desc()).limit(limit)
    if mine_id:
        q = q.where(QualitySample.mine_id == mine_id)
    rows = (await db.execute(q)).scalars().all()
    return [QualitySampleOut.model_validate(r) for r in rows]


@router.get("/predictions", response_model=list[QualityPredictionOut])
async def list_predictions(
    mine_id: uuid.UUID | None = None,
    risk: QualityRisk | None = None,
    limit: int = Query(default=50, le=200),
    user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
):
    q = select(QualityPrediction).order_by(QualityPrediction.prediction_date.desc()).limit(limit)
    if mine_id:
        q = q.where(QualityPrediction.mine_id == mine_id)
    if risk:
        q = q.where(QualityPrediction.risk == risk)
    rows = (await db.execute(q)).scalars().all()
    return [QualityPredictionOut.model_validate(r) for r in rows]


@router.post("/predict", response_model=QualityPredictionOut)
async def predict(body: PredictRequest, user: CurrentUser, db: AsyncSession = Depends(get_db)):
    """Flag likely grade slippage from patterns — before the lab result comes back."""
    try:
        pred = await quality_correlation.create_prediction(
            db, body.mine_id, body.declared_gcv, datetime.now(timezone.utc), body.bench_id
        )
    except ValueError as e:
        raise HTTPException(400, str(e))
    return pred


@router.post("/predictions/{prediction_id}/confirm-lab", response_model=QualityPredictionOut)
async def confirm_lab(prediction_id: uuid.UUID, body: ConfirmLabRequest, user: CurrentUser, db: AsyncSession = Depends(get_db)):
    """Record the UTTAM lab result; raises a Truth Gate conflict if it confirms slippage."""
    try:
        pred, _conflict = await quality_correlation.confirm_lab(db, prediction_id, body.lab_gcv)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return pred
