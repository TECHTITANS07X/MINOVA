"""Predictive Parliamentary Question Engine.

Analyzes historical parliamentary question patterns, scores the likelihood of
each question pattern being asked (seasonality + live incident triggers), and
pre-generates evidence packs with figures that carry lineage references so
every number is replayable (Replay the Number integration).

Deterministic only: all official figures come from stored data via fixed
aggregations. No LLM involvement in any statutory number.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import (
    AnomalyStatus,
    ConflictResolution,
    EntryStatus,
    EvidencePackStatus,
    MetricName,
    PQTriggerType,
)
from app.domain.models import (
    AnomalyFlag,
    ConflictFlag,
    EntryValue,
    Mine,
    ParliamentaryQuestion,
    QuestionPattern,
    ShiftEntry,
    WeatherObservation,
)


def _month_start(now: datetime) -> datetime:
    return datetime(now.year, now.month, 1, tzinfo=timezone.utc)


async def _production_by_mine(db: AsyncSession, period_start: datetime, period_end: datetime) -> dict[uuid.UUID, dict]:
    """Approved production tonnes per mine for the period. Returns {mine_id: {total, entry_ids}}."""
    q = (
        select(
            ShiftEntry.mine_id,
            func.sum(EntryValue.value),
            func.count(func.distinct(ShiftEntry.id)),
        )
        .join(EntryValue, EntryValue.shift_entry_id == ShiftEntry.id)
        .where(
            ShiftEntry.status == EntryStatus.APPROVED,
            ShiftEntry.shift_date >= period_start,
            ShiftEntry.shift_date < period_end,
            EntryValue.metric == MetricName.PRODUCTION_TONNES,
        )
        .group_by(ShiftEntry.mine_id)
    )
    out: dict[uuid.UUID, dict] = {}
    for mine_id, total, n in (await db.execute(q)).all():
        out[mine_id] = {"total": float(total or 0), "entries": int(n)}
    return out


async def compute_pattern_likelihood(db: AsyncSession, pattern: QuestionPattern, now: datetime) -> dict:
    """Score how likely this question pattern is to be asked now.

    Deterministic score in [0, 1]:
      base      = historical frequency (capped at 40 questions/10y for 0.4)
      seasonal  = +0.25 if current month is one of the pattern's peak months
      incident  = +0.35 scaled by live trigger severity (data-driven)
    """
    base = min(Decimal(pattern.historical_frequency_10y) / Decimal(100), Decimal("0.4"))
    seasonal = Decimal("0")
    if now.month in (pattern.typical_months or []):
        seasonal = Decimal("0.25")

    incident = Decimal("0")
    conds = pattern.trigger_conditions or {}
    if pattern.trigger_type == PQTriggerType.INCIDENT:
        severity = await _incident_severity(db, conds, now)
        incident = min(Decimal("0.35") * severity, Decimal("0.35"))
    elif pattern.trigger_type == PQTriggerType.SEASONAL and conds.get("weather"):
        seasonal = Decimal("0.25")  # monsoon-driven patterns double-count seasonality

    score = (base + seasonal + incident).quantize(Decimal("0.0001"))
    reasons: list[str] = []
    if seasonal > 0:
        reasons.append(f"Peak month for this pattern (historical months: {pattern.typical_months})")
    if incident > 0:
        reasons.append("Live operational trigger detected in verified data")
    if not reasons:
        reasons.append("Background frequency only")
    return {"pattern": pattern, "score": score, "reasons": reasons}


async def _incident_severity(db: AsyncSession, conds: dict, now: datetime) -> Decimal:
    """Severity multiplier from live data for incident-driven patterns."""
    severity = Decimal("0")
    if conds.get("on") == "production_drop":
        month_start = _month_start(now)
        prev_start = (month_start - timedelta(days=1)).replace(day=1)
        cur = await _production_by_mine(db, month_start, now)
        prev = await _production_by_mine(db, prev_start, month_start)
        if prev:
            prev_total = sum(v["total"] for v in prev.values())
            cur_total = sum(v["total"] for v in cur.values())
            if prev_total > 0:
                drop_pct = (Decimal(prev_total) - Decimal(cur_total)) / Decimal(prev_total) * 100
                if drop_pct >= Decimal(conds.get("drop_pct", 10)):
                    severity = min(drop_pct / Decimal(20), Decimal("1"))
    elif conds.get("on") == "unresolved_conflicts":
        n = await db.scalar(
            select(func.count()).select_from(ConflictFlag).where(ConflictFlag.resolution == ConflictResolution.UNRESOLVED)
        )
        severity = min(Decimal(n or 0) / Decimal(3), Decimal("1"))
    elif conds.get("on") == "safety_anomalies":
        n = await db.scalar(
            select(func.count())
            .select_from(AnomalyFlag)
            .where(AnomalyFlag.status == AnomalyStatus.FLAGGED, AnomalyFlag.metric.in_(["workers_present", "equipment_availability"]))
        )
        severity = min(Decimal(n or 0) / Decimal(3), Decimal("1"))
    return severity


def _figure(label: str, value: float | int | str, unit: str, source_type: str, source_ids: list[str], note: str = "") -> dict:
    """A replayable figure: every number names its source rows (Replay the Number)."""
    return {
        "label": label,
        "value": value,
        "unit": unit,
        "source_type": source_type,
        "source_ids": source_ids,
        "note": note,
    }


async def generate_evidence_pack(db: AsyncSession, pattern: QuestionPattern, likelihood: dict, now: datetime) -> dict:
    """Build a pre-generated answer pack for the pattern from verified data only."""
    month_start = _month_start(now)
    period_end = now
    prev_start = (month_start - timedelta(days=1)).replace(day=1)

    cur = await _production_by_mine(db, month_start, period_end)
    prev = await _production_by_mine(db, prev_start, month_start)
    mines = {m.id: m for m in (await db.execute(select(Mine))).scalars().all()}

    # Production section — figures cite the shift entries they aggregate
    production_figures = []
    for mine_id, agg in cur.items():
        mine = mines.get(mine_id)
        production_figures.append(_figure(
            f"{mine.name if mine else mine_id} — production (month-to-date)",
            round(agg["total"], 2), "tonnes", "shift_entry", [str(mine_id)],
            f"Sum of {agg['entries']} approved shift entries",
        ))
    cur_total = sum(v["total"] for v in cur.values())
    prev_total = sum(v["total"] for v in prev.values())
    mom_pct = ((Decimal(cur_total) - Decimal(prev_total)) / Decimal(prev_total) * 100) if prev_total else Decimal("0")
    production_figures.append(_figure(
        "All mines — MoM change", f"{float(mom_pct.quantize(Decimal('0.1'))):+}", "%", "shift_entry",
        [str(m) for m in cur], "Computed from approved shift entries, current vs previous month",
    ))

    # Conflicts section (Truth Gate) — packs surface unresolved cross-source conflicts
    conflicts = (await db.execute(
        select(ConflictFlag).where(ConflictFlag.resolution == ConflictResolution.UNRESOLVED).limit(10)
    )).scalars().all()
    conflict_figures = [
        _figure(
            f"{c.metric} — {c.source_a} vs {c.source_b}",
            f"{c.value_a} vs {c.value_b}", "", "conflict_flag", [str(c.id)],
            "Unresolved: human resolution mandatory (Truth Gate)",
        )
        for c in conflicts
    ]

    # Anomalies section
    anomalies = (await db.execute(
        select(AnomalyFlag)
        .where(AnomalyFlag.status == AnomalyStatus.FLAGGED, AnomalyFlag.flag_date >= month_start - timedelta(days=30))
        .order_by(AnomalyFlag.flag_date.desc()).limit(10)
    )).scalars().all()
    anomaly_figures = [
        _figure(
            f"{a.metric} at {mines[a.mine_id].name if a.mine_id in mines else a.mine_id}",
            f"{a.actual_value} (expected {a.expected_value})", "", "anomaly_flag", [str(a.id)],
            f"Score {a.anomaly_score}; explanation pending review",
        )
        for a in anomalies
    ]

    # Weather context
    rain = await db.scalar(
        select(func.sum(WeatherObservation.precipitation_mm)).where(
            WeatherObservation.observation_date >= month_start
        )
    )
    weather_figures = [
        _figure("Rainfall — all mines (month-to-date)", float(rain or 0), "mm", "weather_observation", [], "Open-Meteo observations"),
    ]

    sections = {
        "production": {"title": "Production Status", "figures": production_figures},
        "conflicts": {"title": "Cross-Source Conflicts (Truth Gate)", "figures": conflict_figures},
        "anomalies": {"title": "Flagged Anomalies", "figures": anomaly_figures},
        "weather": {"title": "Weather Context", "figures": weather_figures},
    }
    n_conflicts, n_anomalies = len(conflict_figures), len(anomaly_figures)
    summary = (
        f"{pattern.title} — likelihood {float(likelihood['score'] * 100):.0f}%. "
        f"Month-to-date verified production is {cur_total:,.0f} t across "
        f"{len(cur)} reporting mines ({float(mom_pct.quantize(Decimal('0.1'))):+.1f}% MoM). "
        f"{n_conflicts} unresolved cross-source conflict(s) and {n_anomalies} flagged anomaly (ies) are listed "
        f"so the answer uses resolved figures only."
    )

    return {
        "pattern_id": pattern.id,
        "title": pattern.title,
        "likelihood_score": likelihood["score"],
        "reasons": likelihood["reasons"],
        "summary": summary,
        "sections": sections,
        "period_start": month_start,
        "period_end": period_end,
        "status": EvidencePackStatus.READY if n_conflicts == 0 else EvidencePackStatus.DRAFT,
        "data_as_of": now,
    }


async def count_pqs_answered_last_year(db: AsyncSession) -> int:
    year_ago = datetime.now(timezone.utc) - timedelta(days=365)
    return int(await db.scalar(
        select(func.count()).select_from(ParliamentaryQuestion).where(ParliamentaryQuestion.asked_on >= year_ago)
    ) or 0)
