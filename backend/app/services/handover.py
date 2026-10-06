"""Shift Handover Intelligence.

Auto-generates the structured shift handover brief: what was produced, what is
pending, equipment status, safety observations, weather, and notes. The
incoming shift officer gets the complete picture — no missing context.

430 mines × 3 shifts/day = 1,290 handovers/day that currently happen with no
digital record. Deterministic composition from stored data.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_EVEN

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import (
    AnomalyStatus,
    CauseType,
    EntryStatus,
    MetricName,
    ShiftNumber,
)
from app.domain.models import (
    AnomalyFlag,
    CauseRecord,
    EntryValue,
    Mine,
    ShiftEntry,
    ShiftHandover,
    Target,
    TargetPeriod,
    WeatherObservation,
)


def _q(v, places: str = "0.1") -> Decimal:
    return Decimal(str(v)).quantize(Decimal(places), rounding=ROUND_HALF_EVEN)


def _day_bounds(shift_date: datetime) -> tuple[datetime, datetime]:
    d = shift_date.date() if hasattr(shift_date, "date") else shift_date
    start = datetime(d.year, d.month, d.day, tzinfo=timezone.utc)
    return start, start + timedelta(days=1)


SAFETY_CAUSES = {CauseType.FIRE_MAJOR_INCIDENT, CauseType.LABOUR_DISRUPTION}
EQUIPMENT_CAUSES = {CauseType.EQUIPMENT_FAILURE, CauseType.POWER_FAILURE, CauseType.SUPPLY}


async def generate_brief(db: AsyncSession, mine_id: uuid.UUID, shift_date: datetime, shift_number: ShiftNumber) -> ShiftHandover:
    mine = await db.get(Mine, mine_id)
    if mine is None:
        raise ValueError("Mine not found")
    day_start, day_end = _day_bounds(shift_date)

    entries = (
        await db.execute(
            select(ShiftEntry)
            .where(
                ShiftEntry.mine_id == mine_id,
                ShiftEntry.shift_date >= day_start,
                ShiftEntry.shift_date < day_end,
                ShiftEntry.shift_number == shift_number,
            )
            .order_by(ShiftEntry.shift_number)
        )
    ).scalars().all()
    entry_ids = [e.id for e in entries]

    values: dict[MetricName, Decimal] = {}
    if entry_ids:
        rows = (
            await db.execute(
                select(EntryValue.metric, func.sum(EntryValue.value))
                .where(EntryValue.shift_entry_id.in_(entry_ids))
                .group_by(EntryValue.metric)
            )
        ).all()
        values = {metric: Decimal(str(total or 0)) for metric, total in rows}

    production = values.get(MetricName.PRODUCTION_TONNES, Decimal("0"))
    ob = values.get(MetricName.OVERBURDEN_M3, Decimal("0"))

    # Target reference: monthly target / 30 (deterministic proration)
    month_start = day_start.replace(day=1)
    target_row = (
        await db.execute(
            select(Target)
            .where(
                Target.mine_id == mine_id,
                Target.period == TargetPeriod.MONTHLY,
                Target.period_start <= month_start,
                Target.period_end >= month_start,
            )
            .limit(1)
        )
    ).scalars().first()
    shift_target = Decimal(str(target_row.value)) / 90 if target_row else None  # monthly/30 ÷ 3 shifts
    achievement_pct = None
    if shift_target and shift_target > 0:
        achievement_pct = float(_q(production / shift_target * 100, "0.1"))

    # Causes in this shift
    causes: list[CauseRecord] = []
    if entry_ids:
        causes = (
            await db.execute(select(CauseRecord).where(CauseRecord.shift_entry_id.in_(entry_ids)))
        ).scalars().all()
    equipment_items = [c for c in causes if c.cause_type in EQUIPMENT_CAUSES]
    safety_items = [c for c in causes if c.cause_type in SAFETY_CAUSES]
    hours_lost = sum((c.hours_lost for c in causes), Decimal("0"))

    # Weather that day
    weather = (
        await db.execute(
            select(WeatherObservation)
            .where(
                WeatherObservation.mine_id == mine_id,
                WeatherObservation.observation_date >= day_start,
                WeatherObservation.observation_date < day_end,
            )
            .limit(1)
        )
    ).scalars().first()

    # Anomalies in the window
    anomalies = (
        await db.execute(
            select(AnomalyFlag)
            .where(
                AnomalyFlag.mine_id == mine_id,
                AnomalyFlag.flag_date >= day_start - timedelta(hours=6),
                AnomalyFlag.flag_date < day_end,
                AnomalyFlag.status.in_([AnomalyStatus.FLAGGED, AnomalyStatus.ACKNOWLEDGED]),
            )
        )
    ).scalars().all()

    pending = [
        {"entry_id": str(e.id), "shift": e.shift_number.value, "status": e.status.value, "submitted": bool(e.submitted_at)}
        for e in entries
        if e.status not in (EntryStatus.APPROVED,)
    ]

    critical_items: list[str] = []
    for c in equipment_items:
        critical_items.append(f"CHECK BEFORE LOADING: {c.description} ({_q(c.hours_lost)} h lost this shift)")
    for c in safety_items:
        critical_items.append(f"SAFETY: {c.description}")
    for a in anomalies:
        critical_items.append(
            f"ANOMALY: {a.metric} {_q(a.actual_value)} vs expected {_q(a.expected_value)} — review pending"
        )
    if weather and weather.precipitation_mm and weather.precipitation_mm >= Decimal("10"):
        critical_items.append(f"WEATHER: {_q(weather.precipitation_mm)} mm rainfall — watch haul-road conditions")
    if achievement_pct is not None and achievement_pct < 90:
        critical_items.append(f"TARGET: shift at {achievement_pct}% of prorated target — carry gap into next shift plan")

    brief = {
        "mine": {"id": str(mine_id), "name": mine.name, "code": mine.code},
        "shift_date": day_start.date().isoformat(),
        "outgoing_shift": shift_number.value,
        "production": {
            "production_tonnes": float(_q(production, "0.01")),
            "overburden_m3": float(_q(ob, "0.01")),
            "shift_target_tonnes": float(_q(shift_target, "0.01")) if shift_target else None,
            "achievement_pct": achievement_pct,
            "operating_hours": float(_q(values.get(MetricName.OPERATING_HOURS, Decimal("0")), "0.01")),
            "workers_present": float(values.get(MetricName.WORKERS_PRESENT, Decimal("0"))),
        },
        "pending": {"unapproved_entries": pending, "count": len(pending)},
        "equipment": {
            "stoppages": [
                {"type": c.cause_type.value, "description": c.description, "hours_lost": float(c.hours_lost)}
                for c in equipment_items
            ],
            "hours_lost": float(_q(hours_lost, "0.1")),
        },
        "safety": {
            "observations": [
                {"type": c.cause_type.value, "description": c.description} for c in safety_items
            ],
        },
        "weather": {
            "precipitation_mm": float(weather.precipitation_mm) if weather else None,
            "temp_max": float(weather.temperature_max) if weather and weather.temperature_max else None,
            "wind_kmh": float(weather.wind_speed_kmh) if weather and weather.wind_speed_kmh else None,
        } if weather else None,
        "anomalies": [
            {"metric": a.metric, "actual": float(a.actual_value), "expected": float(a.expected_value)}
            for a in anomalies
        ],
        "notes": [e.remarks for e in entries if e.remarks],
    }

    handover = ShiftHandover(
        mine_id=mine_id,
        shift_date=day_start,
        outgoing_shift=shift_number,
        brief=brief,
        critical_items=critical_items,
    )
    db.add(handover)
    await db.flush()
    return handover
