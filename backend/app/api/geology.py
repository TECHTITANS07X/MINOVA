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
from app.domain.models import GeologicalPrediction
from app.services import geology

router = APIRouter()


class PredictionOut(BaseModel):
    id: uuid.UUID
    mine_id: uuid.UUID
    bench_id: uuid.UUID | None
    seam_name: str
    predicted_thickness_m: Decimal
    predicted_gcv: Decimal
    tolerance_pct: Decimal
    source: str

    model_config = {"from_attributes": True}


class CreatePredictionRequest(BaseModel):
    mine_id: uuid.UUID
    bench_id: uuid.UUID | None = None
    seam_name: str
    predicted_thickness_m: Decimal
    predicted_gcv: Decimal
    tolerance_pct: Decimal = Decimal("10.000")
    source: str = "CMPDI"


class ObservationRequest(BaseModel):
    observed_date: datetime
    actual_thickness_m: Decimal
    actual_gcv: Decimal
    notes: str = ""


@router.get("/predictions", response_model=list[PredictionOut])
async def list_predictions(
    mine_id: uuid.UUID | None = None,
    user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
):
    q = select(GeologicalPrediction).order_by(GeologicalPrediction.created_at.desc())
    if mine_id:
        q = q.where(GeologicalPrediction.mine_id == mine_id)
    rows = (await db.execute(q)).scalars().all()
    return [PredictionOut.model_validate(r) for r in rows]


@router.post("/predictions", response_model=PredictionOut)
async def create_prediction(body: CreatePredictionRequest, user: CurrentUser, db: AsyncSession = Depends(get_db)):
    if body.predicted_thickness_m <= 0 or body.tolerance_pct <= 0:
        raise HTTPException(422, "predicted_thickness_m and tolerance_pct must be positive")
    pred = GeologicalPrediction(
        mine_id=body.mine_id,
        bench_id=body.bench_id,
        seam_name=body.seam_name,
        predicted_thickness_m=body.predicted_thickness_m,
        predicted_gcv=body.predicted_gcv,
        tolerance_pct=body.tolerance_pct,
        source=body.source,
    )
    db.add(pred)
    await db.flush()
    return pred


@router.post("/predictions/{prediction_id}/observations")
async def record_observation(
    prediction_id: uuid.UUID,
    body: ObservationRequest,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """Record actual geology encountered — feeds the deviation loop."""
    try:
        obs = await geology.record_observation(
            db,
            prediction_id,
            body.observed_date,
            body.actual_thickness_m,
            body.actual_gcv,
            notes=body.notes,
        )
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {
        "observation_id": str(obs.id),
        "thickness_dev_pct": float(obs.thickness_dev_pct),
        "gcv_dev_pct": float(obs.gcv_dev_pct),
        "severity": obs.severity.value,
    }


@router.get("/deviations")
async def deviations(mine_id: uuid.UUID | None = None, user: CurrentUser = None, db: AsyncSession = Depends(get_db)):
    """Deviation map + learning-loop accuracy stats and recommended tolerances."""
    return await geology.deviation_map(db, mine_id)
