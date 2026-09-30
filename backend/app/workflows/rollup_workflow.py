"""
Temporal workflow for daily/periodic rollup calculations.
Aggregates shift entries into daily, weekly, monthly, quarterly reports.
Creates lineage edges and audit trail for each computation.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

from temporalio import activity, workflow

with workflow.unsafe.imports_passed_through():
    from sqlalchemy import select
    from app.core.database import async_session_factory
    from app.domain.enums import EntryStatus, MetricName, ShiftNumber
    from app.domain.models import (
        ShiftEntry, EntryValue, Report, ReportValue, CalcRun, LineageEdge,
        ReportTemplate, ReportTemplateVersion, Mine,
    )
    from app.services.calculation import (
        aggregate_shifts_to_daily, CalcRunRecord, ShiftValue,
    )


@dataclass
class RollupRequest:
    mine_id: str
    target_date: str  # ISO format date
    period: str  # daily, weekly, monthly


@activity.defn
async def gather_approved_entries(mine_id: str, target_date: str) -> list[dict]:
    from decimal import Decimal

    async with async_session_factory() as db:
        dt = date.fromisoformat(target_date)
        result = await db.execute(
            select(ShiftEntry)
            .where(
                ShiftEntry.mine_id == uuid.UUID(mine_id),
                ShiftEntry.shift_date >= datetime(dt.year, dt.month, dt.day, tzinfo=timezone.utc),
                ShiftEntry.shift_date < datetime(dt.year, dt.month, dt.day, tzinfo=timezone.utc) + timedelta(days=1),
                ShiftEntry.status == EntryStatus.APPROVED,
            )
        )
        entries = result.scalars().all()

        data = []
        for entry in entries:
            vals_result = await db.execute(
                select(EntryValue).where(EntryValue.shift_entry_id == entry.id)
            )
            vals = vals_result.scalars().all()
            data.append({
                "entry_id": str(entry.id),
                "shift_number": entry.shift_number.value,
                "values": {v.metric.value: str(v.value) for v in vals},
            })
        return data


@activity.defn
async def compute_daily_rollup(mine_id: str, target_date: str, entries: list[dict]) -> dict:
    from decimal import Decimal

    if not entries:
        return {"status": "no_entries"}

    shift_records = []
    for e in entries:
        production = Decimal(e["values"].get("PRODUCTION_TONNES", "0"))
        ob = Decimal(e["values"].get("OVERBURDEN_M3", "0"))
        shift_records.append(ShiftValue(
            shift_number=int(e["shift_number"].replace("FIRST", "1").replace("SECOND", "2").replace("THIRD", "3")),
            production_tonnes=production,
            ob_m3=ob,
            is_resubmission=False,
        ))

    result = aggregate_shifts_to_daily(shift_records)
    calc_run = CalcRunRecord(
        formula_id="daily_rollup",
        formula_version=1,
        input_ids=[e["entry_id"] for e in entries],
        output_value=str(result.total_production),
    )

    return {
        "status": "computed",
        "total_production": str(result.total_production),
        "total_ob": str(result.total_ob),
        "shift_count": result.shift_count,
        "calc_run_hash": calc_run.input_hash,
        "entry_ids": [e["entry_id"] for e in entries],
    }


@activity.defn
async def persist_rollup(mine_id: str, target_date: str, rollup: dict) -> str:
    from decimal import Decimal

    async with async_session_factory() as db:
        template_result = await db.execute(
            select(ReportTemplate).where(ReportTemplate.is_active == True).limit(1)
        )
        template = template_result.scalar_one_or_none()
        if not template:
            return "no_template"

        dt = date.fromisoformat(target_date)
        start = datetime(dt.year, dt.month, dt.day, tzinfo=timezone.utc)
        end = start + timedelta(days=1)

        calc_run = CalcRun(
            id=uuid.uuid4(),
            formula_id="daily_rollup",
            formula_version=1,
            input_ids=rollup["entry_ids"],
            output_value=rollup["total_production"],
            input_hash=rollup["calc_run_hash"],
            computed_at=datetime.now(timezone.utc),
        )
        db.add(calc_run)

        report = Report(
            id=uuid.uuid4(),
            mine_id=uuid.UUID(mine_id),
            template_id=template.id,
            period="DAILY",
            period_start=start,
            period_end=end,
            status="DRAFT",
            generated_description="",
            calc_run_id=calc_run.id,
            created_at=datetime.now(timezone.utc),
        )
        db.add(report)

        prod_val = ReportValue(
            id=uuid.uuid4(),
            report_id=report.id,
            metric="production_tonnes",
            value=Decimal(rollup["total_production"]),
            unit="tonnes",
            section="production",
            row_key=f"daily_{target_date}_production",
        )
        db.add(prod_val)

        ob_val = ReportValue(
            id=uuid.uuid4(),
            report_id=report.id,
            metric="overburden_m3",
            value=Decimal(rollup["total_ob"]),
            unit="m3",
            section="overburden",
            row_key=f"daily_{target_date}_ob",
        )
        db.add(ob_val)

        for entry_id in rollup["entry_ids"]:
            for rv in [prod_val, ob_val]:
                edge = LineageEdge(
                    id=uuid.uuid4(),
                    report_value_id=rv.id,
                    source_type="ShiftEntry",
                    source_id=uuid.UUID(entry_id),
                    relationship_type="aggregated_from",
                )
                db.add(edge)

        await db.commit()
        return str(report.id)


@workflow.defn
class DailyRollupWorkflow:
    @workflow.run
    async def run(self, request: RollupRequest) -> dict:
        entries = await workflow.execute_activity(
            gather_approved_entries,
            args=[request.mine_id, request.target_date],
            start_to_close_timeout=timedelta(seconds=60),
        )

        if not entries:
            return {"status": "no_approved_entries", "date": request.target_date}

        rollup = await workflow.execute_activity(
            compute_daily_rollup,
            args=[request.mine_id, request.target_date, entries],
            start_to_close_timeout=timedelta(seconds=60),
        )

        if rollup["status"] != "computed":
            return rollup

        report_id = await workflow.execute_activity(
            persist_rollup,
            args=[request.mine_id, request.target_date, rollup],
            start_to_close_timeout=timedelta(seconds=60),
        )

        return {
            "status": "completed",
            "report_id": report_id,
            "total_production": rollup["total_production"],
            "total_ob": rollup["total_ob"],
            "shift_count": rollup["shift_count"],
        }


@dataclass
class PeriodRollupRequest:
    mine_id: str
    period: str  # weekly, monthly, quarterly, half_yearly, yearly
    start_date: str
    end_date: str


@activity.defn
async def gather_daily_values(mine_id: str, start_date: str, end_date: str) -> list[dict]:
    from decimal import Decimal

    async with async_session_factory() as db:
        result = await db.execute(
            select(Report, ReportValue)
            .join(ReportValue, ReportValue.report_id == Report.id)
            .where(
                Report.mine_id == uuid.UUID(mine_id),
                Report.period == "DAILY",
                Report.period_start >= datetime.fromisoformat(start_date),
                Report.period_end <= datetime.fromisoformat(end_date) + timedelta(days=1),
            )
        )
        rows = result.all()
        daily_vals = []
        for report, rv in rows:
            daily_vals.append({
                "report_id": str(report.id),
                "date": report.period_start.isoformat(),
                "metric": rv.metric,
                "value": str(rv.value),
            })
        return daily_vals


@activity.defn
async def compute_period_rollup(mine_id: str, period: str, daily_values: list[dict]) -> dict:
    from decimal import Decimal

    if not daily_values:
        return {"status": "no_daily_data"}

    totals: dict[str, Decimal] = {}
    count = 0
    source_ids = set()
    for dv in daily_values:
        metric = dv["metric"]
        val = Decimal(dv["value"])
        totals[metric] = totals.get(metric, Decimal("0")) + val
        source_ids.add(dv["report_id"])
        count += 1

    return {
        "status": "computed",
        "period": period,
        "totals": {k: str(v) for k, v in totals.items()},
        "daily_count": count,
        "source_report_ids": list(source_ids),
    }


@workflow.defn
class PeriodRollupWorkflow:
    @workflow.run
    async def run(self, request: PeriodRollupRequest) -> dict:
        daily_values = await workflow.execute_activity(
            gather_daily_values,
            args=[request.mine_id, request.start_date, request.end_date],
            start_to_close_timeout=timedelta(seconds=120),
        )

        if not daily_values:
            return {"status": "no_daily_data", "period": request.period}

        rollup = await workflow.execute_activity(
            compute_period_rollup,
            args=[request.mine_id, request.period, daily_values],
            start_to_close_timeout=timedelta(seconds=60),
        )

        return rollup
