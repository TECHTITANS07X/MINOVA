"""Production Loss Ledger / Recovery Debt.

Records every verified loss event and carries the cumulative effect forward as
a "debt" into future planning. Each review meeting can start with: "we are X MT
behind because of Y, Z events." Derived automatically from approved cause
records; manual entries also supported.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_EVEN

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import EntryStatus, LossRecoveryStatus, LossSourceType, MetricName
from app.domain.models import CauseRecord, EntryValue, LossLedgerEntry, Mine, ShiftEntry


def _q(v, places: str = "0.0001") -> Decimal:
    return Decimal(str(v)).quantize(Decimal(places), rounding=ROUND_HALF_EVEN)


async def mine_avg_hourly_production(db: AsyncSession, mine_id: uuid.UUID) -> Decimal:
    """Average tonnes per operating hour from approved entries (fallback 500 t/h)."""
    result = await db.execute(
        select(EntryValue.metric, func.sum(EntryValue.value))
        .join(ShiftEntry, EntryValue.shift_entry_id == ShiftEntry.id)
        .where(
            ShiftEntry.mine_id == mine_id,
            ShiftEntry.status == EntryStatus.APPROVED,
            EntryValue.metric.in_([MetricName.PRODUCTION_TONNES, MetricName.OPERATING_HOURS]),
        )
        .group_by(EntryValue.metric)
    )
    totals = {metric: Decimal(str(total or 0)) for metric, total in result.all()}
    prod = totals.get(MetricName.PRODUCTION_TONNES, Decimal("0"))
    hours = totals.get(MetricName.OPERATING_HOURS, Decimal("0"))
    if prod > 0 and hours > 0:
        return _q(prod / hours, "0.01")
    return Decimal("500")


async def derive_from_cause_records(db: AsyncSession, mine_id: uuid.UUID, since: datetime | None = None) -> list[LossLedgerEntry]:
    """Turn un-ledgered approved cause records into loss ledger entries.

    tonnes_lost = hours_lost × mine's average hourly production (deterministic).
    """
    since = since or (datetime.now(timezone.utc) - timedelta(days=90))
    q = (
        select(CauseRecord, ShiftEntry.shift_date)
        .join(ShiftEntry, CauseRecord.shift_entry_id == ShiftEntry.id)
        .where(
            ShiftEntry.mine_id == mine_id,
            ShiftEntry.status == EntryStatus.APPROVED,
            ShiftEntry.shift_date >= since,
        )
        .order_by(ShiftEntry.shift_date)
    )
    cause_rows = (await db.execute(q)).all()

    existing_ids = set(
        (await db.execute(
            select(LossLedgerEntry.source_id).where(
                LossLedgerEntry.source_type == LossSourceType.CAUSE_RECORD,
                LossLedgerEntry.source_id.isnot(None),
            )
        )).scalars().all()
    )
    rate = await mine_avg_hourly_production(db, mine_id)
    created = []
    for c, shift_date in cause_rows:
        if c.id in existing_ids:
            continue
        entry = LossLedgerEntry(
            mine_id=mine_id,
            loss_date=shift_date,
            cause_type=c.cause_type,
            description=c.description,
            tonnes_lost=_q(Decimal(str(c.hours_lost)) * rate, "0.01"),
            hours_lost=c.hours_lost,
            source_type=LossSourceType.CAUSE_RECORD,
            source_id=c.id,
            recovery_status=LossRecoveryStatus.OPEN,
        )
        db.add(entry)
        created.append(entry)
    if created:
        await db.flush()
    return created


async def debt_summary(db: AsyncSession, mine_id: uuid.UUID | None = None) -> dict:
    """Cumulative recovery debt: how much each mine is behind and why."""
    q = select(
        LossLedgerEntry.mine_id,
        LossLedgerEntry.cause_type,
        func.sum(LossLedgerEntry.tonnes_lost),
        func.sum(LossLedgerEntry.recovered_tonnes),
        func.count(),
    ).group_by(LossLedgerEntry.mine_id, LossLedgerEntry.cause_type)
    if mine_id:
        q = q.where(LossLedgerEntry.mine_id == mine_id)

    mines = {m.id: m for m in (await db.execute(select(Mine))).scalars().all()}
    rows = (await db.execute(q)).all()

    per_mine: dict[str, dict] = {}
    for mid, cause, lost, recovered, n in rows:
        key = str(mid)
        bucket = per_mine.setdefault(key, {
            "mine_id": key,
            "mine_name": mines[mid].name if mid in mines else key,
            "total_lost": Decimal("0"),
            "recovered": Decimal("0"),
            "open_debt": Decimal("0"),
            "events": 0,
            "by_cause": {},
        })
        lost = Decimal(str(lost or 0))
        recovered = Decimal(str(recovered or 0))
        bucket["total_lost"] += lost
        bucket["recovered"] += recovered
        bucket["open_debt"] += lost - recovered
        bucket["events"] += int(n)
        bucket["by_cause"][cause.value] = bucket["by_cause"].get(cause.value, Decimal("0")) + lost

    out = []
    for bucket in per_mine.values():
        total = bucket["total_lost"]
        recovery_rate = float(_q(bucket["recovered"] / total * 100, "0.1")) if total > 0 else 100.0
        bucket["total_lost"] = float(_q(bucket["total_lost"], "0.01"))
        bucket["recovered"] = float(_q(bucket["recovered"], "0.01"))
        bucket["open_debt"] = float(_q(bucket["open_debt"], "0.01"))
        bucket["recovery_rate_pct"] = recovery_rate
        bucket["by_cause"] = {k: float(_q(v, "0.01")) for k, v in bucket["by_cause"].items()}
        out.append(bucket)
    out.sort(key=lambda b: -b["open_debt"])
    return {
        "mines": out,
        "total_open_debt": float(_q(sum(b["open_debt"] for b in out), "0.01")),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "note": "Open debt = verified losses not yet recovered; feeds weather-aware recovery planning",
    }
