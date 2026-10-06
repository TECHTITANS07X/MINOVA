"""Statutory Compliance Sentinel.

Auto-tracks regulatory deadlines across mines (DGMS returns, MoEF conditions,
state board submissions). For each filing period it computes data completeness
from approved shift entries and flags filings that are due with incomplete
data. Missing a DGMS deadline can shut a mine — this makes deadlines visible.

Deterministic: completeness = fraction of required metrics present in approved
entries for the period.
"""
from __future__ import annotations

import calendar
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_EVEN

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import (
    ComplianceFrequency,
    EntryStatus,
    FilingStatus,
    MetricName,
)
from app.domain.models import (
    ComplianceFiling,
    ComplianceObligation,
    EntryValue,
    Mine,
    ShiftEntry,
)


def _q(v, places: str = "0.01") -> Decimal:
    return Decimal(str(v)).quantize(Decimal(places), rounding=ROUND_HALF_EVEN)


def period_bounds(now: datetime, frequency: ComplianceFrequency) -> tuple[datetime, datetime]:
    """The reporting period whose filing is currently due (the previous one)."""
    tz = timezone.utc
    now = now.astimezone(tz)
    if frequency == ComplianceFrequency.MONTHLY:
        first = datetime(now.year, now.month, 1, tzinfo=tz)
        end = first - timedelta(microseconds=1)
        start = (end - timedelta(days=31)).replace(day=1)
        start = datetime(end.year, end.month, 1, tzinfo=tz)
        return start, end
    if frequency == ComplianceFrequency.QUARTERLY:
        q_month = ((now.month - 1) // 3) * 3 + 1  # current quarter start month
        cur_q_start = datetime(now.year, q_month, 1, tzinfo=tz)
        end = cur_q_start - timedelta(microseconds=1)
        start = datetime(end.year, ((end.month - 1) // 3) * 3 + 1, 1, tzinfo=tz)
        return start, end
    if frequency == ComplianceFrequency.HALF_YEARLY:
        h_month = 1 if now.month <= 6 else 7
        cur_h_start = datetime(now.year, h_month, 1, tzinfo=tz)
        end = cur_h_start - timedelta(microseconds=1)
        start = datetime(end.year, 1 if end.month <= 6 else 7, 1, tzinfo=tz)
        return start, end
    # ANNUAL — fiscal year Apr-Mar
    fy_start_year = now.year - 1 if now.month <= 3 else now.year
    return datetime(fy_start_year, 4, 1, tzinfo=tz), datetime(now.year, 3, 31, 23, 59, 59, tzinfo=tz)


def due_date_for(now: datetime, frequency: ComplianceFrequency, due_day: int) -> datetime:
    """The deadline for the previous period's filing, given its due day."""
    tz = timezone.utc
    now = now.astimezone(tz)
    # months after the previous period ended
    if frequency == ComplianceFrequency.MONTHLY:
        first = datetime(now.year, now.month, 1, tzinfo=tz)
        prev_end_month = (first - timedelta(days=1)).month
        prev_end_year = (first - timedelta(days=1)).year
        return datetime(prev_end_year, prev_end_month, min(due_day, calendar.monthrange(prev_end_year, prev_end_month)[1]), 23, 59, tzinfo=tz)
    if frequency == ComplianceFrequency.QUARTERLY:
        q_month = ((now.month - 1) // 3) * 3 + 1
        cur_q_start = datetime(now.year, q_month, 1, tzinfo=tz)
        end = cur_q_start - timedelta(microseconds=1)
        due_month = end.month + 1
        due_year = end.year
        if due_month > 12:
            due_month, due_year = 1, due_year + 1
        return datetime(due_year, due_month, min(due_day, calendar.monthrange(due_year, due_month)[1]), 23, 59, tzinfo=tz)
    if frequency == ComplianceFrequency.HALF_YEARLY:
        h_month = 1 if now.month <= 6 else 7
        cur_h_start = datetime(now.year, h_month, 1, tzinfo=tz)
        end = cur_h_start - timedelta(microseconds=1)
        due_month = end.month + 1
        due_year = end.year
        if due_month > 12:
            due_month, due_year = 1, due_year + 1
        return datetime(due_year, due_month, min(due_day, calendar.monthrange(due_year, due_month)[1]), 23, 59, tzinfo=tz)
    # ANNUAL — fiscal year Apr-Mar; filing due one month after FY end
    fy_start_year = now.year - 1 if now.month <= 3 else now.year
    due_year = fy_start_year + 1
    return datetime(due_year, 4, 30, 23, 59, tzinfo=tz)


async def compute_filing_state(
    db: AsyncSession, obligation: ComplianceObligation, mine: Mine, period_start: datetime, period_end: datetime, due: datetime, now: datetime
) -> dict:
    """Completeness of required metrics in approved entries for the period."""
    required: list[str] = obligation.required_metrics or []
    present: set[str] = set()
    if required:
        wanted = {m for m in required}
        rows = (
            await db.execute(
                select(EntryValue.metric, func.count())
                .join(ShiftEntry, EntryValue.shift_entry_id == ShiftEntry.id)
                .where(
                    ShiftEntry.mine_id == mine.id,
                    ShiftEntry.shift_date >= period_start,
                    ShiftEntry.shift_date <= period_end,
                    ShiftEntry.status == EntryStatus.APPROVED,
                )
                .group_by(EntryValue.metric)
            )
        ).all()
        present = {m.value if hasattr(m, "value") else str(m) for m, _ in rows if (m.value if hasattr(m, "value") else str(m)) in wanted}

    missing = [m for m in required if m not in present]
    completion = _q(len(present) / len(required) * 100, "0.01") if required else Decimal("100")

    existing = (
        await db.execute(
            select(ComplianceFiling)
            .where(
                ComplianceFiling.obligation_id == obligation.id,
                ComplianceFiling.mine_id == mine.id,
                ComplianceFiling.period_start == period_start,
            )
            .limit(1)
        )
    ).scalars().first()

    if existing and existing.submitted_at:
        status = FilingStatus.SUBMITTED
    elif now > due:
        status = FilingStatus.LATE
    elif completion >= 100:
        status = FilingStatus.READY
    elif completion > 0:
        status = FilingStatus.INCOMPLETE
    else:
        status = FilingStatus.NOT_STARTED

    days_remaining = (due - now).days
    return {
        "existing": existing,
        "period_start": period_start,
        "period_end": period_end,
        "due": due,
        "status": status,
        "completion_pct": completion,
        "missing_metrics": missing,
        "days_remaining": days_remaining,
    }


async def sync_filings(db: AsyncSession, now: datetime | None = None) -> dict:
    """Ensure a filing row exists for every active obligation × mine and update
    computed status/completeness. Returns the dashboard data."""
    now = now or datetime.now(timezone.utc)
    obligations = (await db.execute(select(ComplianceObligation).where(ComplianceObligation.is_active))).scalars().all()
    mines = (await db.execute(select(Mine).where(Mine.is_active))).scalars().all()

    dashboard = []
    for obligation in obligations:
        p_start, p_end = period_bounds(now, obligation.frequency)
        due = due_date_for(now, obligation.frequency, obligation.due_day)
        mine_scopes = [m for m in mines if obligation.mine_id in (None, m.id)]
        for mine in mine_scopes:
            state = await compute_filing_state(db, obligation, mine, p_start, p_end, due, now)
            filing = state["existing"] or ComplianceFiling(
                obligation_id=obligation.id,
                mine_id=mine.id,
                period_start=state["period_start"],
                period_end=state["period_end"],
                due_date=due,
            )
            filing.status = state["status"]
            filing.completion_pct = state["completion_pct"]
            filing.missing_metrics = state["missing_metrics"]
            if state["existing"] is None:
                db.add(filing)
            dashboard.append({
                "obligation_id": str(obligation.id),
                "obligation_title": obligation.title,
                "authority": obligation.authority.value,
                "frequency": obligation.frequency.value,
                "mine_id": str(mine.id),
                "mine_name": mine.name,
                "period_start": state["period_start"].date().isoformat(),
                "period_end": state["period_end"].date().isoformat(),
                "due_date": due.date().isoformat(),
                "due_in_days": state["days_remaining"],
                "status": state["status"].value,
                "completion_pct": float(state["completion_pct"]),
                "missing_metrics": state["missing_metrics"],
            })
    await db.flush()
    dashboard.sort(key=lambda d: (d["status"] != FilingStatus.LATE.value, d["status"] != FilingStatus.INCOMPLETE.value, d["due_in_days"]))
    counts: dict[str, int] = {}
    for d in dashboard:
        counts[d["status"]] = counts.get(d["status"], 0) + 1
    return {"filings": dashboard, "counts": counts, "synced_at": now.isoformat()}


async def mark_submitted(db: AsyncSession, filing_id: uuid.UUID, user_id: uuid.UUID | None) -> ComplianceFiling:
    filing = await db.get(ComplianceFiling, filing_id)
    if filing is None:
        raise ValueError("Filing not found")
    if filing.submitted_at:
        raise ValueError("Filing already submitted")
    if filing.completion_pct < 100:
        raise ValueError("Cannot submit incomplete filing — complete the required data first")
    filing.status = FilingStatus.SUBMITTED
    filing.submitted_at = datetime.now(timezone.utc)
    filing.submitted_by = user_id
    await db.flush()
    return filing
