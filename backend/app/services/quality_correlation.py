"""Quality-Dispatch Correlation.

Predicts likely grade (GCV) slippage from production + dispatch patterns BEFORE
UTTAM lab results arrive (typical 1-week lag). When the lab result does arrive,
it confirms or refutes the prediction and can raise a Truth Gate conflict.

Deterministic only — no LLM in any figure.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_EVEN

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import ConflictResolution, QualityPredictionStatus, QualityRisk
from app.domain.models import ConflictFlag, Mine, QualityPrediction, QualitySample

# Risk thresholds on |deviation| between declared grade GCV and pattern-predicted GCV
RISK_HIGH_PCT = Decimal("5")
RISK_MEDIUM_PCT = Decimal("2.5")


def _q(value: Decimal | float | int, places: str = "0.0001") -> Decimal:
    return Decimal(str(value)).quantize(Decimal(places), rounding=ROUND_HALF_EVEN)


async def compute_baseline(db: AsyncSession, mine_id: uuid.UUID, now: datetime) -> tuple[Decimal, dict]:
    """Baseline GCV for the same calendar month in previous years, plus a
    recent-trend adjustment from the last 3 samples.

    Returns (baseline_gcv, basis) where basis records the evidence used.
    """
    year = now.year
    month = now.month
    samples = (
        await db.execute(
            select(QualitySample)
            .where(QualitySample.mine_id == mine_id, QualitySample.sample_date < datetime(year, month, 1, tzinfo=timezone.utc))
            .order_by(QualitySample.sample_date.desc())
            .limit(60)
        )
    ).scalars().all()

    seasonal = [float(s.gcv_kcal) for s in samples if s.sample_date.month == month]
    recent = [float(s.gcv_kcal) for s in samples[:3]]
    overall = [float(s.gcv_kcal) for s in samples]

    pool = seasonal or overall
    if not pool:
        return Decimal("0"), {"samples_used": 0, "note": "No history — baseline unavailable"}

    baseline = Decimal(str(sum(pool) / len(pool)))
    basis: dict = {
        "samples_used": len(pool),
        "seasonal_samples": len(seasonal),
        "method": "mean of same-month historical GCV" if seasonal else "mean of all historical GCV",
    }
    if len(recent) >= 2:
        recent_avg = sum(recent) / len(recent)
        drift = Decimal(str(recent_avg)) - baseline
        # Dampen the trend: only 30% of recent drift is projected forward
        baseline = baseline + (drift * Decimal("0.3"))
        basis["recent_trend"] = {
            "recent_samples": recent,
            "drift_applied": float((drift * Decimal("0.3")).quantize(Decimal("0.01"))),
        }
    return _q(baseline, "0.01"), basis


async def create_prediction(
    db: AsyncSession, mine_id: uuid.UUID, declared_gcv: Decimal, now: datetime, bench_id: uuid.UUID | None = None
) -> QualityPrediction:
    """Predict GCV from patterns and flag risk if the declared grade deviates."""
    baseline, basis = await compute_baseline(db, mine_id, now)
    if baseline <= 0:
        raise ValueError("No quality history for this mine — cannot predict")

    predicted = baseline  # pattern prediction; trend already folded in
    deviation_pct = _q((declared_gcv - predicted) / predicted * 100)
    abs_dev = abs(deviation_pct)
    if abs_dev >= RISK_HIGH_PCT:
        risk = QualityRisk.HIGH
    elif abs_dev >= RISK_MEDIUM_PCT:
        risk = QualityRisk.MEDIUM
    else:
        risk = QualityRisk.LOW

    status = (
        QualityPredictionStatus.SLIPPAGE_FLAGGED
        if risk in (QualityRisk.HIGH, QualityRisk.MEDIUM)
        else QualityPredictionStatus.PENDING
    )
    pred = QualityPrediction(
        mine_id=mine_id,
        bench_id=bench_id,
        prediction_date=now,
        baseline_gcv=baseline,
        predicted_gcv=_q(predicted, "0.01"),
        declared_gcv=_q(declared_gcv, "0.01"),
        deviation_pct=deviation_pct,
        risk=risk,
        status=status,
        basis=basis,
        flagged_at=now if status == QualityPredictionStatus.SLIPPAGE_FLAGGED else None,
    )
    db.add(pred)
    await db.flush()
    return pred


async def confirm_lab_result(db: AsyncSession, prediction_id: uuid.UUID, lab_gcv: Decimal, tolerance_pct: Decimal = Decimal("1.5")) -> tuple[QualityPrediction, ConflictFlag | None]:
    """Record the UTTAM lab result. If it confirms slippage vs the declared
    grade, raise a Truth Gate conflict for human resolution."""
    pred = await db.get(QualityPrediction, prediction_id)
    if pred is None:
        raise ValueError("Prediction not found")
    if pred.status == QualityPredictionStatus.LAB_CONFIRMED:
        raise ValueError("Lab result already recorded")

    pred.lab_gcv = _q(lab_gcv, "0.01")
    pred.lab_confirmed_at = datetime.now(timezone.utc)
    pred.status = QualityPredictionStatus.LAB_CONFIRMED

    conflict = None
    lab_dev_pct = abs((pred.lab_gcv - pred.declared_gcv) / pred.declared_gcv * 100)
    if lab_dev_pct >= tolerance_pct:
        conflict = ConflictFlag(
            entity_type="quality_prediction",
            entity_id=pred.id,
            metric="declared_gcv",
            value_a=pred.declared_gcv,
            source_a="dispatch_declaration",
            value_b=pred.lab_gcv,
            source_b="uttam_lab",
            tolerance_pct=tolerance_pct,
            resolution=ConflictResolution.UNRESOLVED,
        )
        db.add(conflict)
        pred.status = QualityPredictionStatus.SLIPPAGE_FLAGGED
    await db.flush()
    return pred, conflict


async def risk_summary(db: AsyncSession, mine_id: uuid.UUID | None = None) -> dict:
    q = select(
        QualityPrediction.risk, func.count()
    ).group_by(QualityPrediction.risk)
    if mine_id:
        q = q.where(QualityPrediction.mine_id == mine_id)
    by_risk = {risk.value if hasattr(risk, "value") else str(risk): n for risk, n in (await db.execute(q)).all()}
    pending_lab = int(await db.scalar(
        select(func.count()).select_from(QualityPrediction).where(QualityPrediction.status == QualityPredictionStatus.PENDING)
    ) or 0)
    flagged = int(by_risk.get("high", 0)) + int(by_risk.get("medium", 0))
    return {
        "by_risk": by_risk,
        "pending_lab": pending_lab,
        "flagged": flagged,
        "note": "Flags surface BEFORE the UTTAM lab result (~1 week) arrives",
    }
