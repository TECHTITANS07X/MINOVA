from __future__ import annotations

import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.schemas import LineageNode, ReplayResult
from app.core.database import get_db
from app.core.security import CurrentUser
from app.domain.models import (
    CalcRun,
    EntryValue,
    LineageEdge,
    Report,
    ReportValue,
    ShiftEntry,
)
from app.services.calculation import (
    ShiftValue,
    aggregate_shifts_to_daily,
    ZERO,
)

router = APIRouter()


async def _build_tree(
    db: AsyncSession,
    source_type: str,
    source_id: uuid.UUID,
    depth: int = 0,
) -> LineageNode:
    if depth > 10:
        return LineageNode(source_type=source_type, source_id=source_id, relationship_type="truncated", label="max depth")

    node = LineageNode(source_type=source_type, source_id=source_id, relationship_type="input")

    if source_type == "report_value":
        rv_res = await db.execute(select(ReportValue).where(ReportValue.id == source_id))
        rv = rv_res.scalar_one_or_none()
        if rv:
            node.value = rv.value
            node.label = f"{rv.metric} = {rv.value} {rv.unit}"
            edges_res = await db.execute(
                select(LineageEdge).where(LineageEdge.report_value_id == source_id)
            )
            for edge in edges_res.scalars().all():
                child = await _build_tree(db, edge.source_type, edge.source_id, depth + 1)
                child.relationship_type = edge.relationship_type
                node.children.append(child)

    elif source_type == "shift_entry":
        entry_res = await db.execute(
            select(ShiftEntry).where(ShiftEntry.id == source_id).options(selectinload(ShiftEntry.values))
        )
        entry = entry_res.scalar_one_or_none()
        if entry:
            node.label = f"Shift {entry.shift_number.value} on {entry.shift_date}"
            for v in entry.values:
                node.children.append(LineageNode(
                    source_type="entry_value",
                    source_id=v.id,
                    relationship_type="data",
                    value=v.value,
                    label=f"{v.metric.value} = {v.value} {v.unit}",
                ))

    elif source_type == "report":
        report_res = await db.execute(
            select(Report).where(Report.id == source_id).options(selectinload(Report.values))
        )
        report = report_res.scalar_one_or_none()
        if report:
            node.label = f"Report {report.period.value} ({report.period_start} — {report.period_end})"
            for rv in report.values:
                child = await _build_tree(db, "report_value", rv.id, depth + 1)
                node.children.append(child)

    return node


@router.get("/{report_value_id}", response_model=LineageNode)
async def get_lineage(
    report_value_id: uuid.UUID,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    rv_res = await db.execute(select(ReportValue).where(ReportValue.id == report_value_id))
    if not rv_res.scalar_one_or_none():
        raise HTTPException(404, "Report value not found")
    return await _build_tree(db, "report_value", report_value_id)


@router.post("/{report_value_id}/replay", response_model=ReplayResult)
async def replay_number(
    report_value_id: uuid.UUID,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    rv_res = await db.execute(
        select(ReportValue).where(ReportValue.id == report_value_id)
        .options(selectinload(ReportValue.lineage_edges))
    )
    rv = rv_res.scalar_one_or_none()
    if not rv:
        raise HTTPException(404, "Report value not found")

    entry_ids = [e.source_id for e in rv.lineage_edges if e.source_type == "shift_entry"]

    if not entry_ids:
        return ReplayResult(
            report_value_id=report_value_id,
            stored_value=rv.value,
            recomputed_value=rv.value,
            match=True,
        )

    entries_res = await db.execute(
        select(ShiftEntry)
        .where(ShiftEntry.id.in_(entry_ids))
        .options(selectinload(ShiftEntry.values))
    )
    entries = entries_res.scalars().all()

    shift_values: list[ShiftValue] = []
    for e in entries:
        prod = ZERO
        ob = ZERO
        for v in e.values:
            if v.metric.value == "production_tonnes":
                prod = v.value
            elif v.metric.value == "overburden_m3":
                ob = v.value
        shift_values.append(ShiftValue(
            entry_id=str(e.id),
            shift_number=int(e.shift_number.value.replace("first", "1").replace("second", "2").replace("third", "3")),
            shift_date=e.shift_date.date(),
            mine_id=str(e.mine_id),
            production_tonnes=prod,
            ob_volume_m3=ob,
        ))

    recomputed = ZERO
    if shift_values:
        daily, _ = aggregate_shifts_to_daily(shift_values)
        if rv.metric == "production_tonnes":
            recomputed = daily.total_production_tonnes
        elif rv.metric == "overburden_m3":
            recomputed = daily.total_ob_volume_m3

    tree = await _build_tree(db, "report_value", report_value_id)

    return ReplayResult(
        report_value_id=report_value_id,
        stored_value=rv.value,
        recomputed_value=recomputed,
        match=rv.value == recomputed,
        lineage_tree=tree,
    )
