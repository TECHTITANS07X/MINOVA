"""Geological Deviation Learning Loop.

Compares actual geology encountered during mining (seam thickness, quality)
against CMPDI's original predictions. Builds a mine-by-mine deviation map and
feeds the accumulated deviation statistics back as adjusted confidence bounds
for future predictions — a self-improving geological intelligence loop.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_EVEN
from statistics import fmean, pstdev

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.enums import DeviationSeverity
from app.domain.models import GeologicalObservation, GeologicalPrediction, Mine


def _q(v, places: str = "0.0001") -> Decimal:
    return Decimal(str(v)).quantize(Decimal(places), rounding=ROUND_HALF_EVEN)


def _pct(actual: Decimal, predicted: Decimal) -> Decimal:
    if not predicted:
        return Decimal("0")
    return _q((actual - predicted) / predicted * 100)


def _severity(dev_pct: Decimal, tolerance_pct: Decimal) -> DeviationSeverity:
    abs_dev = abs(dev_pct)
    if abs_dev <= tolerance_pct:
        return DeviationSeverity.WITHIN_TOLERANCE
    if abs_dev <= tolerance_pct * 2:
        return DeviationSeverity.MODERATE
    return DeviationSeverity.SEVERE


async def record_observation(
    db: AsyncSession,
    prediction_id: uuid.UUID,
    observed_date: datetime,
    actual_thickness_m: Decimal,
    actual_gcv: Decimal,
    notes: str = "",
    recorded_by: uuid.UUID | None = None,
) -> GeologicalObservation:
    """Record actual geology and compute deviations against the prediction."""
    pred = await db.get(GeologicalPrediction, prediction_id)
    if pred is None:
        raise ValueError("Prediction not found")

    t_dev = _pct(Decimal(str(actual_thickness_m)), Decimal(str(pred.predicted_thickness_m)))
    g_dev = _pct(Decimal(str(actual_gcv)), Decimal(str(pred.predicted_gcv)))
    # Severity keyed on the worse of the two deviations
    severity = _severity(max(abs(t_dev), abs(g_dev)), pred.tolerance_pct)

    obs = GeologicalObservation(
        prediction_id=prediction_id,
        observed_date=observed_date,
        actual_thickness_m=_q(actual_thickness_m, "0.01"),
        actual_gcv=_q(actual_gcv, "0.01"),
        thickness_dev_pct=t_dev,
        gcv_dev_pct=g_dev,
        severity=severity,
        notes=notes,
        recorded_by=recorded_by,
    )
    db.add(obs)
    await db.flush()
    return obs


async def deviation_map(db: AsyncSession, mine_id: uuid.UUID | None = None) -> dict:
    """Mine-by-mine map of prediction vs reality with accuracy stats."""
    q = select(GeologicalPrediction).options(selectinload(GeologicalPrediction.observations)).order_by(GeologicalPrediction.created_at)
    if mine_id:
        q = q.where(GeologicalPrediction.mine_id == mine_id)
    preds = (await db.execute(q)).scalars().all()
    mines = {m.id: m for m in (await db.execute(select(Mine))).scalars().all()}

    entries = []
    all_t_devs: list[float] = []
    all_g_devs: list[float] = []
    severe_count = 0

    for p in preds:
        obs = sorted(p.observations, key=lambda o: o.observed_date)
        t_devs = [float(o.thickness_dev_pct) for o in obs]
        g_devs = [float(o.gcv_dev_pct) for o in obs]
        all_t_devs.extend(t_devs)
        all_g_devs.extend(g_devs)
        latest = obs[-1] if obs else None
        n_severe = sum(1 for o in obs if o.severity == DeviationSeverity.SEVERE)
        severe_count += n_severe
        entries.append({
            "prediction_id": str(p.id),
            "mine": mines[p.mine_id].name if p.mine_id in mines else str(p.mine_id),
            "seam": p.seam_name,
            "source": p.source,
            "predicted_thickness_m": float(p.predicted_thickness_m),
            "predicted_gcv": float(p.predicted_gcv),
            "tolerance_pct": float(p.tolerance_pct),
            "observations": len(obs),
            "latest": {
                "date": latest.observed_date.date().isoformat(),
                "actual_thickness_m": float(latest.actual_thickness_m),
                "actual_gcv": float(latest.actual_gcv),
                "thickness_dev_pct": float(latest.thickness_dev_pct),
                "gcv_dev_pct": float(latest.gcv_dev_pct),
                "severity": latest.severity.value,
            } if latest else None,
            "mean_thickness_dev_pct": round(fmean(t_devs), 2) if t_devs else None,
            "mean_gcv_dev_pct": round(fmean(g_devs), 2) if g_devs else None,
            "severe_deviations": n_severe,
        })

    def _stats(devs: list[float]) -> dict:
        if not devs:
            return {"n": 0}
        mean = fmean(devs)
        sd = pstdev(devs) if len(devs) > 1 else 0.0
        return {
            "n": len(devs),
            "bias_pct": round(mean, 2),
            "mean_abs_dev_pct": round(fmean([abs(d) for d in devs]), 2),
            "std_pct": round(sd, 2),
        }

    t_stats = _stats(all_t_devs)
    g_stats = _stats(all_g_devs)

    # Learning loop: adjusted recommended tolerance = |bias| + 2σ (95% band)
    def _recommend(stats: dict, fallback: float = 10.0) -> float | None:
        if stats.get("n", 0) < 5:
            return None
        return round(abs(stats["bias_pct"]) + 2 * stats["std_pct"], 2) or fallback

    return {
        "predictions": entries,
        "thickness_accuracy": t_stats,
        "gcv_accuracy": g_stats,
        "recommended_tolerance": {
            "thickness_pct": _recommend(t_stats),
            "gcv_pct": _recommend(g_stats),
            "note": "Derived from observed deviations (|bias| + 2σ) — feed back into future CMPDI prediction confidence bounds",
        },
        "severe_deviations_total": severe_count,
        "alert": (
            f"{severe_count} severe geological deviation(s) — mine plans may need re-verification"
            if severe_count else None
        ),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
