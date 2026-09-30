from __future__ import annotations

import io
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.schemas import (
    Page,
    ReportDescriptionEdit,
    ReportGenerateRequest,
    ReportOut,
    ReportValueOut,
    StatusResponse,
)
from app.core.database import get_db
from app.core.security import CurrentUser
from app.domain.enums import EntryStatus, ReportPeriod, ReportStatus
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
)

router = APIRouter()


@router.post("/generate", response_model=ReportOut)
async def generate_report(
    body: ReportGenerateRequest,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    entries_q = (
        select(ShiftEntry)
        .where(
            ShiftEntry.mine_id == body.mine_id,
            ShiftEntry.status == EntryStatus.APPROVED,
            ShiftEntry.shift_date >= body.period_start,
            ShiftEntry.shift_date <= body.period_end,
        )
        .options(selectinload(ShiftEntry.values))
    )
    entries = (await db.execute(entries_q)).scalars().all()

    shift_values: list[ShiftValue] = []
    for e in entries:
        prod = Decimal("0")
        ob = Decimal("0")
        op_hrs = Decimal("0")
        dt_hrs = Decimal("0")
        for v in e.values:
            if v.metric.value == "production_tonnes":
                prod = v.value
            elif v.metric.value == "overburden_m3":
                ob = v.value
            elif v.metric.value == "operating_hours":
                op_hrs = v.value
            elif v.metric.value == "downtime_hours":
                dt_hrs = v.value

        shift_values.append(ShiftValue(
            entry_id=str(e.id),
            shift_number=int(e.shift_number.value.replace("first", "1").replace("second", "2").replace("third", "3")),
            shift_date=e.shift_date.date() if isinstance(e.shift_date, datetime) else e.shift_date,
            mine_id=str(e.mine_id),
            bench_id=str(e.bench_id) if e.bench_id else None,
            production_tonnes=prod,
            ob_volume_m3=ob,
            operating_hours=op_hrs,
            downtime_hours=dt_hrs,
        ))

    report = Report(
        mine_id=body.mine_id,
        template_id=body.template_id,
        period=body.period,
        period_start=body.period_start,
        period_end=body.period_end,
        status=ReportStatus.DRAFT,
    )
    db.add(report)
    await db.flush()

    if shift_values:
        daily, calc_record = aggregate_shifts_to_daily(shift_values)

        cr = CalcRun(
            formula_id=calc_record.formula_id,
            formula_version=calc_record.formula_version,
            input_ids=calc_record.input_ids,
            output_value=calc_record.output_value,
            input_hash=calc_record.input_hash,
        )
        db.add(cr)
        await db.flush()
        report.calc_run_id = cr.id

        rv_prod = ReportValue(
            report_id=report.id,
            metric="production_tonnes",
            value=daily.total_production_tonnes,
            unit="t",
            section="production",
            row_key="total",
            calc_run_id=cr.id,
        )
        db.add(rv_prod)
        await db.flush()

        for eid in daily.input_entry_ids:
            db.add(LineageEdge(
                report_value_id=rv_prod.id,
                source_type="shift_entry",
                source_id=uuid.UUID(eid),
                relationship_type="input",
            ))

        rv_ob = ReportValue(
            report_id=report.id,
            metric="overburden_m3",
            value=daily.total_ob_volume_m3,
            unit="m3",
            section="overburden",
            row_key="total",
            calc_run_id=cr.id,
        )
        db.add(rv_ob)

    await db.flush()
    result = await db.execute(
        select(Report).where(Report.id == report.id).options(selectinload(Report.values))
    )
    return result.scalar_one()


@router.get("", response_model=Page)
async def list_reports(
    user: CurrentUser,
    mine_id: uuid.UUID | None = None,
    period: ReportPeriod | None = None,
    report_status: ReportStatus | None = None,
    cursor: str | None = None,
    limit: int = Query(default=50, le=200),
    db: AsyncSession = Depends(get_db),
):
    q = select(Report)
    if mine_id:
        q = q.where(Report.mine_id == mine_id)
    if period:
        q = q.where(Report.period == period)
    if report_status:
        q = q.where(Report.status == report_status)
    if cursor:
        q = q.where(Report.id > uuid.UUID(cursor))

    q = q.order_by(Report.created_at.desc()).limit(limit + 1)
    rows = (await db.execute(q)).scalars().all()
    has_more = len(rows) > limit
    items = rows[:limit]
    return Page(
        items=[ReportOut.model_validate(r) for r in items],
        total=len(items),
        cursor=str(items[-1].id) if items else None,
        has_more=has_more,
    )


@router.get("/{report_id}", response_model=ReportOut)
async def get_report(
    report_id: uuid.UUID,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Report).where(Report.id == report_id).options(selectinload(Report.values))
    )
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(404, "Report not found")
    return report


@router.patch("/{report_id}/description", response_model=StatusResponse)
async def edit_description(
    report_id: uuid.UUID,
    body: ReportDescriptionEdit,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Report).where(Report.id == report_id))
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(404, "Report not found")
    report.edited_description = body.edited_description
    return StatusResponse(status="updated", message="Description updated")


@router.get("/{report_id}/export")
async def export_report(
    report_id: uuid.UUID,
    user: CurrentUser,
    fmt: str = Query(default="xlsx", pattern="^(xlsx|pdf|docx)$"),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Report).where(Report.id == report_id).options(selectinload(Report.values))
    )
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(404, "Report not found")

    if fmt == "xlsx":
        from openpyxl import Workbook
        wb = Workbook()
        ws = wb.active
        ws.title = "Report"
        ws.append(["Metric", "Value", "Unit", "Section"])
        for rv in report.values:
            ws.append([rv.metric, float(rv.value), rv.unit, rv.section])
        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)
        return Response(
            content=buf.getvalue(),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="report_{report_id}.xlsx"'},
        )

    elif fmt == "pdf":
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas as pdf_canvas
        buf = io.BytesIO()
        c = pdf_canvas.Canvas(buf, pagesize=A4)
        c.setFont("Helvetica-Bold", 14)
        c.drawString(50, 780, f"MINOVA Report — {report.period.value}")
        c.setFont("Helvetica", 10)
        y = 750
        c.drawString(50, y, f"Mine: {report.mine_id}  |  Period: {report.period_start} — {report.period_end}")
        y -= 30
        c.setFont("Helvetica-Bold", 10)
        c.drawString(50, y, "Metric")
        c.drawString(250, y, "Value")
        c.drawString(350, y, "Unit")
        y -= 15
        c.setFont("Helvetica", 10)
        for rv in report.values:
            c.drawString(50, y, rv.metric)
            c.drawString(250, y, str(rv.value))
            c.drawString(350, y, rv.unit)
            y -= 15
            if y < 50:
                c.showPage()
                y = 780
        if report.generated_description:
            y -= 20
            c.setFont("Helvetica-Bold", 10)
            c.drawString(50, y, "Description:")
            y -= 15
            c.setFont("Helvetica", 9)
            desc = report.edited_description or report.generated_description
            for line in desc.split("\n")[:20]:
                c.drawString(50, y, line[:100])
                y -= 12
        c.save()
        buf.seek(0)
        return Response(
            content=buf.getvalue(),
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="report_{report_id}.pdf"'},
        )

    elif fmt == "docx":
        from docx import Document as DocxDoc
        doc = DocxDoc()
        doc.add_heading(f"MINOVA Report — {report.period.value}", level=1)
        doc.add_paragraph(f"Mine: {report.mine_id}  |  Period: {report.period_start} — {report.period_end}")
        table = doc.add_table(rows=1, cols=4)
        table.style = "Table Grid"
        hdr = table.rows[0].cells
        hdr[0].text, hdr[1].text, hdr[2].text, hdr[3].text = "Metric", "Value", "Unit", "Section"
        for rv in report.values:
            row = table.add_row().cells
            row[0].text = rv.metric
            row[1].text = str(rv.value)
            row[2].text = rv.unit
            row[3].text = rv.section
        if report.generated_description:
            doc.add_heading("Description", level=2)
            doc.add_paragraph(report.edited_description or report.generated_description)
        buf = io.BytesIO()
        doc.save(buf)
        buf.seek(0)
        return Response(
            content=buf.getvalue(),
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f'attachment; filename="report_{report_id}.docx"'},
        )
