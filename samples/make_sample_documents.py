"""Generate professional sample mine documents for the document-to-report pipeline.

Each PDF is a realistic CIL-area monthly production report. The labeled figures
(Production, Overburden removal, Operating hours, Workers present) are what the
extraction engine parses — every number lands in the finalized report with
page-level provenance via Replay the Number.
"""
from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

HERE = Path(__file__).parent

GREEN = colors.HexColor("#1B5E20")
GREY = colors.HexColor("#546E7A")
LIGHT = colors.HexColor("#ECEFF1")

HEADER = "MINOVA - Mining Intelligence Platform"
FOOTER = "Machine-generated copies must reference the source document ID."

STYLES = getSampleStyleSheet()


def _styles():
    cover_title = ParagraphStyle("CoverTitle", parent=STYLES["Title"], fontSize=20, textColor=GREEN, spaceAfter=8)
    cover_sub = ParagraphStyle("CoverSub", parent=STYLES["Heading2"], fontSize=13, textColor=GREY, spaceAfter=20)
    h2 = ParagraphStyle("H2", parent=STYLES["Heading2"], fontSize=12, textColor=GREEN, spaceBefore=12, spaceAfter=4)
    body = ParagraphStyle("Body", parent=STYLES["BodyText"], fontSize=10, leading=14)
    small = ParagraphStyle("Small", parent=STYLES["BodyText"], fontSize=8, textColor=GREY)
    return cover_title, cover_sub, h2, body, small


def _header_footer(title, doc_ref):
    def draw(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica-Bold", 8)
        canvas.setFillColor(GREY)
        canvas.drawString(18 * mm, 285 * mm, HEADER)
        canvas.drawRightString(192 * mm, 285 * mm, doc_ref)
        canvas.setStrokeColor(LIGHT)
        canvas.line(18 * mm, 283.4 * mm, 192 * mm, 283.4 * mm)
        canvas.setFont("Helvetica", 7.5)
        canvas.drawString(18 * mm, 10 * mm, FOOTER)
        canvas.drawRightString(192 * mm, 10 * mm, f"Page {canvas.getPageNumber()}")
        canvas.setFillColor(colors.black)
        canvas.restoreState()
    return draw


def _kv_table(rows):
    t = Table(rows, colWidths=[62 * mm, 108 * mm])
    t.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#B0BEC5")),
        ("BACKGROUND", (0, 0), (0, -1), LIGHT),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9.5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return t


def _metrics_table(rows):
    data = [["Parameter", "Value", "Remarks"]] + rows
    t = Table(data, colWidths=[62 * mm, 34 * mm, 74 * mm])
    t.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#B0BEC5")),
        ("BACKGROUND", (0, 0), (-1, 0), GREEN),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9.5),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return t


def _signatures(small):
    t = Table(
        [[Paragraph("Prepared by<br/>Shift Supervisor", small),
          Paragraph("Verified by<br/>Mine Manager", small),
          Paragraph("Approved by<br/>General Manager", small)]],
        colWidths=[58 * mm, 58 * mm, 58 * mm],
    )
    t.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#B0BEC5")),
        ("TOPPADDING", (0, 0), (-1, -1), 18),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 18),
    ]))
    return t


def build_doc(spec: dict) -> Path:
    cover_title, cover_sub, h2, body, small = _styles()
    out = HERE / spec["filename"]
    doc = SimpleDocTemplate(
        str(out), pagesize=A4,
        leftMargin=18 * mm, rightMargin=18 * mm, topMargin=24 * mm, bottomMargin=18 * mm,
        title=spec["doc_title"], author=spec["author"], subject=spec["doc_title"],
    )

    story = [
        Paragraph("Coal India Limited", ParagraphStyle("org", parent=STYLES["Heading2"], textColor=GREY, fontSize=11)),
        Paragraph(spec["org_line"], cover_title),
        Paragraph(spec["period_line"], cover_sub),
        _kv_table(spec["cover"]),
        Spacer(1, 16),
        Paragraph("This document is the authoritative source of the production figures summarised herein.", small),
        PageBreak(),
    ]

    story += [
        Paragraph("1. Production Summary", h2),
        _metrics_table(spec["metrics_rows"]),
        Spacer(1, 6),
        Paragraph(spec["production_narrative"], body),

        Paragraph("2. Equipment Utilisation", h2),
        Paragraph(spec["equipment"], body),

        Paragraph("3. Manpower", h2),
        Paragraph(spec["manpower"], body),

        Paragraph("4. Safety", h2),
        Paragraph(spec["safety"], body),

        Paragraph("5. Remarks", h2),
        Paragraph(spec["remarks"], body),

        Spacer(1, 20),
        Paragraph("Signatures", h2),
        _signatures(small),
    ]

    doc.build(story, onFirstPage=_header_footer(spec["header_ref"], spec["doc_ref"]),
              onLaterPages=_header_footer(spec["header_ref"], spec["doc_ref"]))
    return out


SPECS = [
    {
        "filename": "Rajmahal_OCP_Monthly_Production_Report_Sep2026.pdf",
        "doc_title": "Monthly Production Report - Rajmahal OCP - September 2026",
        "org_line": "Rajmahal Open Cast Project",
        "period_line": "Monthly Production &amp; Safety Report - September 2026",
        "author": "Rajmahal Area, Eastern Coalfields Limited",
        "doc_ref": "RAJ/MPR/2026-09",
        "header_ref": "Rajmahal OCP - Monthly Production Report",
        "cover": [
            ["Document reference", "RAJ/MPR/2026-09"],
            ["Mine", "Rajmahal Open Cast Project (OCP)"],
            ["Subsidiary", "Eastern Coalfields Limited (ECL)"],
            ["Reporting period", "01 September 2026 - 30 September 2026"],
            ["Classification", "Internal - Management Review"],
            ["Prepared by", "Shift Supervisor, Rajmahal OCP"],
        ],
        "metrics_rows": [
            ["Production", "9,500 t", "Coal won during the reporting month"],
            ["Overburden removal", "4,200 m3", "Volume of overburden handled"],
            ["Operating hours", "18", "Primary shovel-dumper combination"],
            ["Workers present", "140", "Including 12 contractual staff"],
        ],
        "production_narrative": (
            "Output was affected by two days of planned maintenance on the HEMM fleet. "
            "Stripping continued on Bench 3 and Bench 4 throughout the period. Figures above "
            "reconcile with shift-level entries recorded in the platform."
        ),
        "equipment": (
            "Operating hours: 18 across the primary shovel-dumper combination on the reporting day. "
            "Dragline availability remained above 92 percent. No major breakdowns were reported during "
            "the last week of the month."
        ),
        "manpower": "Workers present: 140 (including 12 contractual staff) on the reporting shift. Attendance averaged 96 percent for the month.",
        "safety": (
            "Zero lost-time injuries during the month. One near-miss was reported involving dumper "
            "movement near the coal stockpile; corrective toolbox training has been completed and the "
            "haul-road lighting was upgraded."
        ),
        "remarks": (
            "This document is the authoritative source for the monthly report figures. Despatch "
            "records and weighbridge logs are appended in the master file."
        ),
    },
    {
        "filename": "Gevra_OCP_Monthly_Production_Report_Sep2026.pdf",
        "doc_title": "Monthly Production Report - Gevra OCP - September 2026",
        "org_line": "Gevra Open Cast Project",
        "period_line": "Monthly Production &amp; Safety Report - September 2026",
        "author": "Gevra Area, South Eastern Coalfields Limited",
        "doc_ref": "GEV/MPR/2026-09",
        "header_ref": "Gevra OCP - Monthly Production Report",
        "cover": [
            ["Document reference", "GEV/MPR/2026-09"],
            ["Mine", "Gevra Open Cast Project (OCP)"],
            ["Subsidiary", "South Eastern Coalfields Limited (SECL)"],
            ["Reporting period", "01 September 2026 - 30 September 2026"],
            ["Classification", "Internal - Management Review"],
            ["Prepared by", "Shift Supervisor, Gevra OCP"],
        ],
        "metrics_rows": [
            ["Production", "12,400 t", "Coal won during the reporting month"],
            ["Overburden removal", "6,150 m3", "Volume of overburden handled"],
            ["Operating hours", "21", "Primary shovel-dumper combination"],
            ["Workers present", "176", "Including 21 contractual staff"],
        ],
        "production_narrative": (
            "Highest monthly output of the quarter, supported by commissioning of the third shovel. "
            "Coal quality remained within band; GCV samples are appended in the master file."
        ),
        "equipment": (
            "Operating hours: 21 across the primary shovel-dumper combination on the reporting day. "
            "Two dumpers underwent scheduled transmission service; no availability impact."
        ),
        "manpower": "Workers present: 176 (including 21 contractual staff) on the reporting shift. Night-shift attendance improved after the lighting upgrade.",
        "safety": "No reportable incidents. Safety audit score 94/100; two observations closed during the month.",
        "remarks": "Figures reconcile with weighbridge despatch records; variance within prescribed tolerance.",
    },
    {
        "filename": "Piparwar_OCP_Production_Bulletin_Oct2026.pdf",
        "doc_title": "Production Bulletin - Piparwar OCP - October 2026",
        "org_line": "Piparwar Open Cast Project",
        "period_line": "Fortnightly Production Bulletin - October 2026",
        "author": "Piparwar Area, Central Coalfields Limited",
        "doc_ref": "PIP/PRB/2026-10",
        "header_ref": "Piparwar OCP - Production Bulletin",
        "cover": [
            ["Document reference", "PIP/PRB/2026-10"],
            ["Mine", "Piparwar Open Cast Project (OCP)"],
            ["Subsidiary", "Central Coalfields Limited (CCL)"],
            ["Reporting period", "01 October 2026 - 15 October 2026"],
            ["Classification", "Internal - Management Review"],
            ["Prepared by", "Shift Supervisor, Piparwar OCP"],
        ],
        "metrics_rows": [
            ["Production", "7,850 t", "Coal won during the reporting fortnight"],
            ["Overburden removal", "3,975 m3", "Volume of overburden handled"],
            ["Operating hours", "16", "Primary shovel-dumper combination"],
            ["Workers present", "128", "Including 9 contractual staff"],
        ],
        "production_narrative": (
            "Rainfall on two shifts reduced effective cutting hours. Output is expected to recover "
            "in the second fortnight with the resumption of the bench-2 haul road."
        ),
        "equipment": "Operating hours: 16 across the primary shovel-dumper combination on the reporting day. Pumping units deployed at the sump for two shifts.",
        "manpower": "Workers present: 128 (including 9 contractual staff) on the reporting shift.",
        "safety": "Zero lost-time injuries. Monsoon-specific precautions briefed at all gate meetings.",
        "remarks": "This bulletin is the authoritative source for the fortnightly figures reported to the area office.",
    },
]


def main() -> None:
    for spec in SPECS:
        path = build_doc(spec)
        print(f"written: {path}")


if __name__ == "__main__":
    main()
