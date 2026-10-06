"""Smart Anomaly Narratives.

When an anomaly is flagged, the AI layer does not just report the number — it
cross-references weather, cause records (equipment logs), historical similar
events and target pressure to produce a probable explanation with evidence
citations. Template-based and deterministic; every claim names its evidence.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import AnomalyStatus, CauseType, EntryStatus, MetricName
from app.domain.models import (
    AnomalyFlag,
    CauseRecord,
    EntryValue,
    Mine,
    ShiftEntry,
    Target,
    TargetPeriod,
    WeatherObservation,
)

WINDOW_DAYS = 2  # look ±2 days around the anomaly for correlated events


def _fmt(v) -> str:
    d = Decimal(str(v))
    d = d.quantize(Decimal("0.1")) if abs(d) < 1000 else d.quantize(Decimal("1"))
    return f"{d:,}"


async def build_narrative(db: AsyncSession, anomaly: AnomalyFlag) -> dict:
    """Build a cross-referenced explanation for an anomaly flag."""
    now = datetime.now(timezone.utc)
    window_start = anomaly.flag_date - timedelta(days=WINDOW_DAYS)
    window_end = anomaly.flag_date + timedelta(days=WINDOW_DAYS)

    mine = await db.get(Mine, anomaly.mine_id)
    mine_name = mine.name if mine else str(anomaly.mine_id)

    direction = "dropped" if anomaly.actual_value < anomaly.expected_value else "spiked"
    delta = abs(anomaly.actual_value - anomaly.expected_value)
    delta_pct = (delta / anomaly.expected_value * 100) if anomaly.expected_value else Decimal("0")

    evidence: list[dict] = []
    probable_causes: list[dict] = []

    # 1. Cause records near the anomaly (equipment logs / stoppage reports)
    causes = (
        await db.execute(
            select(CauseRecord)
            .join(ShiftEntry, CauseRecord.shift_entry_id == ShiftEntry.id)
            .where(
                ShiftEntry.mine_id == anomaly.mine_id,
                ShiftEntry.shift_date >= window_start,
                ShiftEntry.shift_date <= window_end,
            )
            .order_by(ShiftEntry.shift_date)
        )
    ).scalars().all()
    for c in causes[:5]:
        probable_causes.append({
            "type": c.cause_type.value,
            "description": c.description,
            "hours_lost": float(c.hours_lost),
            "confidence": "high" if c.hours_lost >= 3 else "medium",
        })
        evidence.append({
            "source_type": "cause_record",
            "source_id": str(c.id),
            "detail": f"{c.cause_type.value.replace('_', ' ').title()}: {c.description} ({_fmt(c.hours_lost)} h lost)",
        })

    # 2. Weather in the window
    weather = (
        await db.execute(
            select(WeatherObservation)
            .where(
                WeatherObservation.mine_id == anomaly.mine_id,
                WeatherObservation.observation_date >= window_start,
                WeatherObservation.observation_date <= window_end,
            )
            .order_by(WeatherObservation.observation_date)
        )
    ).scalars().all()
    rainy = [w for w in weather if w.precipitation_mm and w.precipitation_mm >= Decimal("10")]
    if rainy:
        total_rain = sum(w.precipitation_mm for w in rainy)
        probable_causes.append({
            "type": "rain_weather",
            "description": f"Rainfall of {_fmt(total_rain)} mm within ±{WINDOW_DAYS} days of the anomaly",
            "hours_lost": 0,
            "confidence": "medium",
        })
        for w in rainy[:3]:
            evidence.append({
                "source_type": "weather_observation",
                "source_id": str(w.id),
                "detail": f"{w.observation_date.date()}: {_fmt(w.precipitation_mm)} mm rainfall",
            })

    # 3. Similar historical events at this mine (same metric, last 180 days)
    similar = (
        await db.execute(
            select(AnomalyFlag)
            .where(
                AnomalyFlag.mine_id == anomaly.mine_id,
                AnomalyFlag.metric == anomaly.metric,
                AnomalyFlag.id != anomaly.id,
                AnomalyFlag.flag_date >= now - timedelta(days=180),
            )
            .order_by(AnomalyFlag.flag_date.desc())
            .limit(5)
        )
    ).scalars().all()
    similar_events = [
        {
            "date": s.flag_date.date().isoformat(),
            "expected": float(s.expected_value),
            "actual": float(s.actual_value),
            "status": s.status.value,
        }
        for s in similar
    ]
    if similar_events:
        evidence.append({
            "source_type": "anomaly_flag",
            "source_id": str(similar[0].id),
            "detail": f"{len(similar)} similar {anomaly.metric} anomaly flag(s) at this mine in the last 180 days — recurring pattern",
        })

    # 4. Target pressure (how far behind plan the mine is this month)
    month_start = anomaly.flag_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if month_start.tzinfo is None:
        month_start = month_start.replace(tzinfo=timezone.utc)
    target_row = (
        await db.execute(
            select(Target)
            .where(
                Target.mine_id == anomaly.mine_id,
                Target.period == TargetPeriod.MONTHLY,
                Target.period_start <= month_start,
                Target.period_end >= month_start,
            )
            .limit(1)
        )
    ).scalars().first()
    target_pressure = None
    if target_row:
        produced = await db.scalar(
            select(func.sum(EntryValue.value))
            .join(ShiftEntry, EntryValue.shift_entry_id == ShiftEntry.id)
            .where(
                ShiftEntry.mine_id == anomaly.mine_id,
                ShiftEntry.shift_date >= month_start,
                ShiftEntry.shift_date <= anomaly.flag_date,
                ShiftEntry.status == EntryStatus.APPROVED,
                EntryValue.metric == MetricName.PRODUCTION_TONNES,
            )
        )
        produced = Decimal(str(produced or 0))
        target_pressure = {
            "monthly_target": float(target_row.value),
            "month_to_date": float(produced),
            "achievement_pct": float((produced / target_row.value * 100).quantize(Decimal("0.1"))) if target_row.value else None,
        }
        evidence.append({
            "source_type": "target",
            "source_id": str(target_row.id),
            "detail": f"Monthly target {_fmt(target_row.value)} t; MTD achieved {target_pressure['achievement_pct']}%",
        })

    # ── Compose the narrative ────────────────────────────────────────────────
    summary = (
        f"{anomaly.metric.replace('_', ' ').title()} at {mine_name} {direction} from an expected "
        f"{_fmt(anomaly.expected_value)} to {_fmt(anomaly.actual_value)} ({_fmt(delta_pct)}% off) on "
        f"{anomaly.flag_date.date().isoformat()}."
    )
    if probable_causes:
        top = probable_causes[0]
        summary += f" Most probable cause: {top['description']}."
    elif rainy:
        summary += " Weather in the window is the most probable contributing factor."
    else:
        summary += " No correlated equipment, weather or stoppage event was found — review recommended."
    if similar_events:
        summary += f" Note: {len(similar_events)} similar event(s) at this mine in the last 180 days."

    return {
        "anomaly_id": str(anomaly.id),
        "summary": summary,
        "probable_causes": probable_causes,
        "similar_events": similar_events,
        "target_pressure": target_pressure,
        "evidence": evidence,
        "method": "deterministic cross-reference (causes + weather + history + targets)",
        "generated_at": now.isoformat(),
    }
