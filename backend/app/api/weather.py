from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import CurrentUser, require_role
from app.domain.models import Mine, RecoveryPlan, WeatherForecast, WeatherObservation
from app.domain.enums import RecoveryPlanStatus

router = APIRouter()


class WeatherOut(BaseModel):
    id: UUID
    mine_id: UUID
    observation_date: datetime
    temperature_max: Decimal | None
    temperature_min: Decimal | None
    precipitation_mm: Decimal
    wind_speed_kmh: Decimal | None
    humidity_pct: Decimal | None
    weather_code: int | None
    source: str

    model_config = {"from_attributes": True}


class ForecastOut(BaseModel):
    id: UUID
    mine_id: UUID
    forecast_date: datetime
    precipitation_mm: Decimal
    temperature_max: Decimal | None
    weather_code: int | None

    model_config = {"from_attributes": True}


class RecoveryPlanOut(BaseModel):
    id: UUID
    mine_id: UUID
    period_start: datetime
    period_end: datetime
    gap_tonnes: Decimal
    proposed_daily_targets: dict
    rationale: str
    historical_evidence: dict
    status: str
    decision_reason: str
    created_at: datetime
    decided_at: datetime | None

    model_config = {"from_attributes": True}


class RecoveryPlanDecision(BaseModel):
    action: str  # "accept" or "reject"
    reason: str


@router.get("/observations/{mine_id}")
async def get_weather_observations(
    mine_id: UUID,
    start_date: date = Query(None),
    end_date: date = Query(None),
    limit: int = Query(90, le=365),
    user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
) -> list[WeatherOut]:
    stmt = select(WeatherObservation).where(WeatherObservation.mine_id == mine_id)
    if start_date:
        stmt = stmt.where(WeatherObservation.observation_date >= datetime.combine(start_date, datetime.min.time()))
    if end_date:
        stmt = stmt.where(WeatherObservation.observation_date <= datetime.combine(end_date, datetime.max.time()))
    stmt = stmt.order_by(WeatherObservation.observation_date.desc()).limit(limit)
    result = await db.execute(stmt)
    return [WeatherOut.model_validate(r) for r in result.scalars().all()]


@router.get("/forecast/{mine_id}")
async def get_weather_forecast(
    mine_id: UUID,
    days: int = Query(7, le=14),
    user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
) -> list[ForecastOut]:
    stmt = (
        select(WeatherForecast)
        .where(WeatherForecast.mine_id == mine_id)
        .where(WeatherForecast.forecast_date >= datetime.utcnow())
        .order_by(WeatherForecast.forecast_date)
        .limit(days)
    )
    result = await db.execute(stmt)
    return [ForecastOut.model_validate(r) for r in result.scalars().all()]


@router.get("/recovery-plans/{mine_id}")
async def list_recovery_plans(
    mine_id: UUID,
    status: RecoveryPlanStatus | None = None,
    user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
) -> list[RecoveryPlanOut]:
    stmt = select(RecoveryPlan).where(RecoveryPlan.mine_id == mine_id)
    if status:
        stmt = stmt.where(RecoveryPlan.status == status)
    stmt = stmt.order_by(RecoveryPlan.created_at.desc())
    result = await db.execute(stmt)
    return [RecoveryPlanOut.model_validate(r) for r in result.scalars().all()]


@router.get("/recovery-plans/detail/{plan_id}")
async def get_recovery_plan(
    plan_id: UUID,
    user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
) -> RecoveryPlanOut:
    plan = await db.get(RecoveryPlan, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Recovery plan not found")
    return RecoveryPlanOut.model_validate(plan)


@router.post("/recovery-plans/{plan_id}/decide")
async def decide_recovery_plan(
    plan_id: UUID,
    decision: RecoveryPlanDecision,
    user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
) -> RecoveryPlanOut:
    plan = await db.get(RecoveryPlan, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Recovery plan not found")
    if plan.status != RecoveryPlanStatus.PROPOSED:
        raise HTTPException(status_code=400, detail=f"Plan already {plan.status.value}")
    if not decision.reason.strip():
        raise HTTPException(status_code=422, detail="Decision reason is required")

    if decision.action == "accept":
        plan.status = RecoveryPlanStatus.ACCEPTED
    elif decision.action == "reject":
        plan.status = RecoveryPlanStatus.REJECTED
    else:
        raise HTTPException(status_code=422, detail="Action must be 'accept' or 'reject'")

    plan.decision_reason = decision.reason
    plan.decided_at = datetime.utcnow()
    await db.flush()
    return RecoveryPlanOut.model_validate(plan)
