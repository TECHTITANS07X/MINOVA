from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import CurrentUser
from app.domain.enums import IncidentCategory, IncidentSeverity
from app.domain.models import SafetyIncident, SafetyPattern

router = APIRouter()


class IncidentCreate(BaseModel):
    mine_id: uuid.UUID
    bench_id: uuid.UUID | None = None
    incident_date: datetime
    category: IncidentCategory
    severity: IncidentSeverity
    description: str
    location_description: str = ""
    workers_involved: int = 0
    injuries: int = 0
    root_cause: str = ""
    corrective_actions: str = ""


class IncidentOut(BaseModel):
    id: uuid.UUID
    mine_id: uuid.UUID
    bench_id: uuid.UUID | None
    incident_date: datetime
    category: IncidentCategory
    severity: IncidentSeverity
    description: str
    location_description: str
    workers_involved: int
    injuries: int
    root_cause: str
    corrective_actions: str
    created_at: datetime

    model_config = {"from_attributes": True}


class PatternOut(BaseModel):
    id: uuid.UUID
    mine_id: uuid.UUID | None
    pattern_name: str
    category: IncidentCategory
    description: str
    incident_count: int
    confidence: Decimal
    contributing_factors: list
    recommendations: list
    detected_at: datetime

    model_config = {"from_attributes": True}


@router.get("/incidents", response_model=list[IncidentOut])
async def list_incidents(
    mine_id: uuid.UUID | None = None,
    category: IncidentCategory | None = None,
    severity: IncidentSeverity | None = None,
    user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
):
    q = select(SafetyIncident).order_by(SafetyIncident.incident_date.desc())
    if mine_id:
        q = q.where(SafetyIncident.mine_id == mine_id)
    if category:
        q = q.where(SafetyIncident.category == category)
    if severity:
        q = q.where(SafetyIncident.severity == severity)
    rows = (await db.execute(q)).scalars().all()
    return [IncidentOut.model_validate(r) for r in rows]


@router.post("/incidents", response_model=IncidentOut, status_code=201)
async def report_incident(
    body: IncidentCreate,
    user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
):
    incident = SafetyIncident(**body.model_dump())
    db.add(incident)
    await db.flush()
    return IncidentOut.model_validate(incident)


@router.get("/patterns", response_model=list[PatternOut])
async def list_patterns(
    mine_id: uuid.UUID | None = None,
    user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
):
    q = select(SafetyPattern).order_by(SafetyPattern.detected_at.desc())
    if mine_id:
        q = q.where(SafetyPattern.mine_id == mine_id)
    rows = (await db.execute(q)).scalars().all()
    return [PatternOut.model_validate(r) for r in rows]


@router.post("/detect")
async def detect_patterns(
    mine_id: uuid.UUID | None = None,
    user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
):
    q = select(SafetyIncident).order_by(SafetyIncident.incident_date.desc())
    if mine_id:
        q = q.where(SafetyIncident.mine_id == mine_id)
    rows = (await db.execute(q)).scalars().all()

    groups: dict[str, list[SafetyIncident]] = defaultdict(list)
    for inc in rows:
        groups[inc.category.value].append(inc)

    patterns_created = []
    for cat_value, incidents in groups.items():
        if len(incidents) < 2:
            continue

        severity_counts: dict[str, int] = defaultdict(int)
        locations: set[str] = set()
        for inc in incidents:
            severity_counts[inc.severity.value] += 1
            if inc.location_description:
                locations.add(inc.location_description)

        confidence = min(Decimal("99.99"), Decimal(str(len(incidents) * 10)))
        factors = [f"{sev}: {cnt}" for sev, cnt in severity_counts.items()]

        pattern = SafetyPattern(
            mine_id=mine_id,
            pattern_name=f"Recurring {cat_value.replace('_', ' ').title()} incidents",
            category=IncidentCategory(cat_value),
            description=f"{len(incidents)} incidents detected in category {cat_value}",
            incident_count=len(incidents),
            confidence=confidence,
            contributing_factors=factors,
            recommendations=[f"Review {cat_value} procedures", "Increase monitoring frequency"],
        )
        db.add(pattern)
        await db.flush()
        patterns_created.append(PatternOut.model_validate(pattern))

    return {"patterns_detected": len(patterns_created), "patterns": patterns_created}
