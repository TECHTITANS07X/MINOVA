"""Explosive-to-Output Correlation.

Tracks explosive consumption vs overburden volume removed. Flags when more (or
less) explosive is used than the mine's historical baseline for the material
moved — anomalies indicate waste, theft, or unexpected geological conditions.
Explosives are PESO-regulated and expensive; even 5% waste across CIL is crores.

Deterministic: deviation = kg/m3 actual vs baseline (median of prior logs).
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_EVEN

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import ExplosiveFlag
from app.domain.models import ExplosiveLog, Mine

# Deviation beyond which we flag (PESO-sensitive: lower threshold than generic)
OVER_PCT = Decimal("15")
UNDER_PCT = Decimal("-15")


def _q(v, places: str = "0.0001") -> Decimal:
    return Decimal(str(v)).quantize(Decimal(places), rounding=ROUND_HALF_EVEN)


async def analyze_logs(db: AsyncSession, mine_id: str | None = None) -> dict:
    """Compute kg/m3 and flag deviations for all logs, oldest first so the
    baseline builds up naturally."""
    q = select(ExplosiveLog).order_by(ExplosiveLog.log_date)
    if mine_id:
        q = q.where(ExplosiveLog.mine_id == mine_id)
    logs = (await db.execute(q)).scalars().all()
    mines = {m.id: m for m in (await db.execute(select(Mine))).scalars().all()}

    history: dict[tuple, list[float]] = {}
    flagged: list[dict] = []

    for log in logs:
        if log.ob_m3 and log.ob_m3 > 0:
            log.kg_per_m3 = _q(Decimal(str(log.explosives_kg)) / Decimal(str(log.ob_m3)), "0.0001")
        else:
            log.kg_per_m3 = Decimal("0")

        key = (log.mine_id, log.bench_id)
        prior = history.get(key) or history.get((log.mine_id, None)) or []
        if len(prior) >= 3:
            ordered = sorted(prior)
            n = len(ordered)
            baseline = Decimal(str(ordered[n // 2] if n % 2 else (ordered[n // 2 - 1] + ordered[n // 2]) / 2))
            log.baseline_kg_per_m3 = _q(baseline, "0.0001")
            if baseline > 0:
                dev = _q((log.kg_per_m3 - baseline) / baseline * 100, "0.0001")
                log.deviation_pct = dev
                if dev >= OVER_PCT:
                    log.flag = ExplosiveFlag.OVER_CONSUMPTION
                elif dev <= UNDER_PCT:
                    log.flag = ExplosiveFlag.UNDER_CONSUMPTION
                else:
                    log.flag = ExplosiveFlag.NORMAL
                if log.flag != ExplosiveFlag.NORMAL:
                    mine_name = mines[log.mine_id].name if log.mine_id in mines else str(log.mine_id)
                    flagged.append({
                        "log_id": str(log.id),
                        "mine": mine_name,
                        "date": log.log_date.date().isoformat(),
                        "kg_per_m3": float(log.kg_per_m3),
                        "baseline": float(log.baseline_kg_per_m3),
                        "deviation_pct": float(dev),
                        "flag": log.flag.value,
                        "explosives_kg": float(log.explosives_kg),
                        "ob_m3": float(log.ob_m3),
                        "possible_explanations": (
                            ["wastage/theft", "unexpected hard rock", "charging practice change"]
                            if log.flag == ExplosiveFlag.OVER_CONSUMPTION
                            else ["under-charging (poor fragmentation risk)", "softer strata than baseline"]
                        ),
                    })
        else:
            log.baseline_kg_per_m3 = Decimal("0")
            log.deviation_pct = Decimal("0")
            log.flag = ExplosiveFlag.NORMAL

        history.setdefault(key, []).append(float(log.kg_per_m3))
        history.setdefault((log.mine_id, None), []).append(float(log.kg_per_m3))

    await db.flush()
    total_kg = sum(float(l.explosives_kg) for l in logs)
    waste_kg = sum(
        float(l.explosives_kg) - float(l.baseline_kg_per_m3) * float(l.ob_m3)
        for l in logs
        if l.flag == ExplosiveFlag.OVER_CONSUMPTION and l.baseline_kg_per_m3 > 0
    )
    return {
        "logs_analyzed": len(logs),
        "flagged": flagged,
        "total_explosives_kg": round(total_kg, 1),
        "estimated_excess_kg": round(max(waste_kg, 0), 1),
        "thresholds": {"over_pct": float(OVER_PCT), "under_pct": float(UNDER_PCT)},
        "note": "Explosives are PESO-regulated — persistent over-consumption warrants physical verification",
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
    }
