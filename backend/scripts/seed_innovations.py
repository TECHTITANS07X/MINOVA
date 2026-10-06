"""Seed demo data for the 8 plan innovations (idempotent — safe to re-run).

Covers: Parliamentary Question Engine, Quality-Dispatch Correlation,
Production Loss Ledger, Shift Handover, Statutory Compliance Sentinel,
Explosive-to-Output Correlation, Geological Deviation Learning Loop.
(Smart Anomaly Narratives work off existing anomaly/cause data.)
"""
from __future__ import annotations

import random
import sys
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.domain.enums import (
    CauseType,
    ComplianceAuthority,
    ComplianceFrequency,
    DeviationSeverity,
    EntryStatus,
    ExplosiveFlag,
    LossRecoveryStatus,
    LossSourceType,
    MetricName,
    PQCategory,
    PQHouse,
    PQTriggerType,
)
from app.domain.models import (
    AnomalyFlag,
    AppUser,
    CauseRecord,
    ComplianceObligation,
    EntryValue,
    ExplosiveLog,
    GeologicalObservation,
    GeologicalPrediction,
    LossLedgerEntry,
    Mine,
    ParliamentaryQuestion,
    QualityPrediction,
    QualitySample,
    QuestionPattern,
    ShiftEntry,
    ShiftHandover,
    Target,
    TargetPeriod,
    WeatherObservation,
)

DB_URL = "postgresql+psycopg2://minova_app:minova_dev@localhost:5433/minova"
engine = create_engine(DB_URL, echo=False)
random.seed(2026)

NOW = datetime(2026, 10, 3, 12, 0, tzinfo=timezone.utc)


def uid() -> uuid.UUID:
    return uuid.uuid4()


def seed_question_patterns(session: Session) -> int:
    if session.scalar(select(QuestionPattern).limit(1)):
        return 0
    defs = [
        ("PQ-PROD-01", "Coal production shortfall against annual target", PQCategory.PRODUCTION, PQTriggerType.SEASONAL,
         38, [2, 3, 7, 12], {"on": "production_drop", "drop_pct": 10},
         ["What is the current status of coal production against the annual target?",
          "Reasons for shortfall in coal production during the current financial year?"]),
        ("PQ-SAFE-02", "Mine safety incidents and fatal accidents", PQCategory.SAFETY, PQTriggerType.INCIDENT,
         34, [1, 6, 9], {"on": "safety_anomalies"},
         ["Number of fatal accidents in coal mines in the last three years?",
          "Steps taken to improve safety in underground mines?"]),
        ("PQ-ENV-03", "Environmental clearance violations and compliance", PQCategory.ENVIRONMENT, PQTriggerType.POLICY,
         22, [4, 7, 10], {},
         ["Mines operating in violation of environmental clearance conditions?",
          "Status of compliance with MoEF conditions across subsidiaries?"]),
        ("PQ-FIN-04", "Coal imports and foreign exchange outgo", PQCategory.IMPORT_EXPORT, PQTriggerType.BUDGET,
         19, [2, 7], {},
         ["Quantity of coal imported during the last fiscal year?",
          "Steps to reduce import dependence for thermal coal?"]),
        ("PQ-QUAL-05", "Coal grade slippage and quality complaints", PQCategory.PRODUCTION, PQTriggerType.INCIDENT,
         14, [8, 11], {"on": "unresolved_conflicts"},
         ["Complaints received from power plants regarding coal quality (GCV)?",
          "Financial loss due to grade slippage penalties?"]),
        ("PQ-LAND-06", "Land acquisition and project displacement", PQCategory.LAND_DISPLACEMENT, PQTriggerType.POLICY,
         27, [3, 11], {},
         ["Status of land acquisition for ongoing expansion projects?",
          "Rehabilitation of families displaced by mining projects?"]),
        ("PQ-DISPT-07", "Coal dispatch to power plants and rake availability", PQCategory.PRODUCTION, PQTriggerType.SEASONAL,
         25, [4, 5, 9, 10], {},
         ["Railway rakes supplied vs demanded for coal evacuation?",
          "Coal stock position at thermal power plants?"]),
        ("PQ-CLOS-08", "Mine closure plans and abandoned mines", PQCategory.ENVIRONMENT, PQTriggerType.POLICY,
         11, [6, 12], {},
         ["Status of mine closure plans for exhausted mines?",
          "Funds utilised for progressive mine closure?"]),
    ]
    patterns = [
        QuestionPattern(
            id=uid(), code=code, title=title, category=cat, trigger_type=trig,
            historical_frequency_10y=freq, typical_months=months,
            trigger_conditions=conds, sample_questions=questions,
        )
        for code, title, cat, trig, freq, months, conds, questions in defs
    ]
    session.add_all(patterns)
    session.flush()
    return len(patterns)


def seed_historical_pqs(session: Session, patterns: list[QuestionPattern]) -> int:
    if session.scalar(select(ParliamentaryQuestion).limit(1)):
        return 0
    members = [
        ("Rama Devi", "Bihar"), ("Suresh Angadi", "Karnataka"), ("Nishikant Dubey", "Jharkhand"),
        ("Mahua Moitra", "West Bengal"), ("Sunil Singh", "Bihar"), ("Gopal Shetty", "Maharashtra"),
    ]
    pqs = []
    for i in range(40):
        p = random.choice(patterns)
        days_ago = random.randint(20, 3400)
        asked = NOW - timedelta(days=days_ago)
        member, constituency = random.choice(members)
        pqs.append(ParliamentaryQuestion(
            house=random.choice([PQHouse.LOK_SABHA, PQHouse.RAJYA_SABHA]),
            question_number=f"{random.randint(100, 4999)}",
            asked_on=asked,
            session_name=random.choice(["Winter", "Monsoon", "Budget"]) + " Session",
            member_name=member,
            constituency=constituency,
            subject=p.title,
            question_text=(p.sample_questions[0] if p.sample_questions else p.title),
            category=p.category,
            pattern_id=p.id,
            days_to_answer=random.randint(2, 5),
        ))
    session.add_all(pqs)
    session.flush()
    return len(pqs)


def seed_quality(session: Session, mines: list[Mine]) -> tuple[int, int]:
    n_samples = 0
    n_preds = 0
    if not session.scalar(select(QualitySample).limit(1)):
        samples = []
        for m in mines:
            base = {"RAJMAHAL": 3400, "SONEPUR": 3600, "JHARIA": 4600, "MOONIDIH": 5200,
                    "PIPARWAR": 4200, "GEVRA": 4000}.get(m.code, 3800)
            for week in range(52 * 3):  # 3 years of lab history
                d = NOW - timedelta(weeks=week)
                if d.month == NOW.month and d.year >= NOW.year - 1:
                    continue  # keep current month unlabeled for prediction demo
                samples.append(QualitySample(
                    mine_id=m.id, sample_date=d,
                    gcv_kcal=Decimal(str(round(random.gauss(base, 110), 1))),
                    grade=random.choice(["G10", "G11", "G12"]),
                    source="uttam_lab",
                ))
                n_samples += 1
        session.add_all(samples)
        session.flush()

    if not session.scalar(select(QualityPrediction).limit(1)):
        preds = []
        cases = [  # (mine_code, declared, risk outcome)
            ("RAJMAHAL", 3550, "high"),   # declared above pattern baseline -> flag
            ("GEVRA", 4050, "low"),       # within pattern
            ("JHARIA", 4300, "medium"),   # below pattern (slippage)
        ]
        for code, declared, _ in cases:
            mine = next(m for m in mines if m.code == code)
            preds.append(QualityPrediction(
                mine_id=mine.id, prediction_date=NOW - timedelta(days=2),
                baseline_gcv=Decimal(str({"RAJMAHAL": 3400, "GEVRA": 4000, "JHARIA": 4600}[code])),
                predicted_gcv=Decimal(str({"RAJMAHAL": 3400, "GEVRA": 4000, "JHARIA": 4600}[code])),
                declared_gcv=Decimal(declared),
                deviation_pct=Decimal(str(round((declared - {"RAJMAHAL": 3400, "GEVRA": 4000, "JHARIA": 4600}[code])
                                                / {"RAJMAHAL": 3400, "GEVRA": 4000, "JHARIA": 4600}[code] * 100, 4))),
                risk={"high": "high", "low": "low", "medium": "medium"}[_],
                status={"high": "slippage_flagged", "low": "pending", "medium": "slippage_flagged"}[_],
                basis={"samples_used": 12, "method": "seeded demo baseline"},
                flagged_at=NOW - timedelta(days=2) if _ in ("high", "medium") else None,
            ))
            n_preds += 1
        session.add_all(preds)
        session.flush()
    return n_samples, n_preds


def seed_loss_ledger(session: Session, mines: list[Mine]) -> int:
    if session.scalar(select(LossLedgerEntry).limit(1)):
        return 0
    defs = [
        ("equipment_failure", "Dragline #3 breakdown — main shaft bearing", 14.0, 6100),
        ("rain_weather", "Monsoon: 65 mm rainfall, pit water logging", 9.5, 4200),
        ("power_failure", "Grid outage — 11kV feeder trip", 6.0, 2600),
        ("blasting_delay", "Misfire re-drilling, delayed bench face", 4.5, 1800),
        ("equipment_failure", "Shovel #2 hydraulic failure", 8.0, 3500),
        ("labour_disruption", "Contractor labour stalemate at dispatcher", 3.0, 1300),
    ]
    entries = []
    for i, (cause, desc, hours, tonnes) in enumerate(defs):
        mine = mines[i % 3]
        entries.append(LossLedgerEntry(
            mine_id=mine.id,
            loss_date=NOW - timedelta(days=3 + i * 4),
            cause_type=CauseType(cause),
            description=desc,
            tonnes_lost=Decimal(str(tonnes)),
            hours_lost=Decimal(str(hours)),
            source_type=LossSourceType.MANUAL,
            recovery_status=LossRecoveryStatus.OPEN,
        ))
    session.add_all(entries)
    session.flush()
    return len(entries)


def seed_compliance(session: Session) -> int:
    if session.scalar(select(ComplianceObligation).limit(1)):
        return 0
    obligations = [
        (ComplianceAuthority.DGMS, "DGMS Monthly Return — Form I (accidents & employment)",
         "Statutory monthly return under Mines Rules", ComplianceFrequency.MONTHLY, 10,
         ["production_tonnes", "workers_present"]),
        (ComplianceAuthority.DGMS, "DGMS Quarterly Safety Status Report",
         "Quarterly safety performance submission", ComplianceFrequency.QUARTERLY, 15,
         ["production_tonnes", "workers_present", "equipment_availability"]),
        (ComplianceAuthority.MOEF, "MoEF Environmental Clearance Compliance Report",
         "Half-yearly EC conditions compliance", ComplianceFrequency.HALF_YEARLY, 30,
         ["production_tonnes", "overburden_m3"]),
        (ComplianceAuthority.STATE_PCB, "State Pollution Board — Air/Water Consent Return",
         "Monthly consent condition monitoring", ComplianceFrequency.MONTHLY, 7,
         ["production_tonnes"]),
        (ComplianceAuthority.COAL_CONTROLLER, "Coal Controller Grade-wise Production Return",
         "Monthly grade-wise production and dispatch", ComplianceFrequency.MONTHLY, 5,
         ["production_tonnes", "dispatch_tonnes"]),
    ]
    session.add_all([
        ComplianceObligation(
            mine_id=None, authority=auth, title=title, description=desc,
            frequency=freq, due_day=day, required_metrics=metrics,
        )
        for auth, title, desc, freq, day, metrics in obligations
    ])
    session.flush()
    return len(obligations)


def seed_explosives(session: Session, mines: list[Mine]) -> int:
    if session.scalar(select(ExplosiveLog).limit(1)):
        return 0
    logs = []
    for m in mines[:4]:
        baseline = random.uniform(0.72, 0.85)
        for day in range(20):
            d = NOW - timedelta(days=20 - day)
            kg_m3 = baseline + random.gauss(0, 0.03)
            if m.code == "RAJMAHAL" and day >= 15:
                kg_m3 = baseline * 1.28  # over-consumption anomaly for demo
            ob = random.randint(9000, 14000)
            logs.append(ExplosiveLog(
                mine_id=m.id, log_date=d,
                explosives_kg=Decimal(str(round(kg_m3 * ob, 1))),
                ob_m3=Decimal(ob),
                coal_tonnes=Decimal(str(round(ob * 0.28, 1))),
            ))
    session.add_all(logs)
    session.flush()
    return len(logs)


def seed_geology(session: Session, mines: list[Mine]) -> tuple[int, int]:
    if session.scalar(select(GeologicalPrediction).limit(1)):
        return 0
    seams = ["XV-A", "XVI", "XVII", "B-10", "A-5"]
    preds, obs = [], []
    for i, m in enumerate(mines[:4]):
        seam = seams[i % len(seams)]
        pred_t = Decimal(str(round(random.uniform(2.2, 6.5), 2)))
        pred_g = Decimal(str(round(random.uniform(3800, 5300), 0)))
        pred = GeologicalPrediction(
            mine_id=m.id, seam_name=seam, predicted_thickness_m=pred_t,
            predicted_gcv=pred_g, tolerance_pct=Decimal("10.000"), source="CMPDI",
        )
        session.add(pred)
        preds.append(pred)
        session.flush()
        # Observed reality: mostly close, one severe deviation
        for k, days_ago in enumerate([75, 45, 15]):
            bias = 1.0
            if m.code == "JHARIA" and k == 2:
                bias = 0.62  # severe thickness deviation for demo
            elif k == 1:
                bias = 1.06
            act_t = pred_t * Decimal(str(bias))
            act_g = pred_g * Decimal(str(round(1 + random.uniform(-0.05, 0.05), 3)))
            t_dev = (act_t - pred_t) / pred_t * 100
            g_dev = (act_g - pred_g) / pred_g * 100
            severity = "within_tolerance"
            if max(abs(t_dev), abs(g_dev)) > 20:
                severity = "severe"
            elif max(abs(t_dev), abs(g_dev)) > 10:
                severity = "moderate"
            obs.append(GeologicalObservation(
                prediction_id=pred.id, observed_date=NOW - timedelta(days=days_ago),
                actual_thickness_m=act_t, actual_gcv=act_g,
                thickness_dev_pct=t_dev, gcv_dev_pct=g_dev,
                severity=DeviationSeverity(severity),
                notes="Development face sampling" if severity != "severe" else "Fault zone encountered — thickness collapsed",
            ))
    session.add_all(preds + obs)
    session.flush()
    return len(preds), len(obs)


def seed_handovers(session: Session, mines: list[Mine]) -> int:
    if session.scalar(select(ShiftHandover).limit(1)):
        return 0
    mine = mines[0]
    day_start = datetime(NOW.year, NOW.month, NOW.day, tzinfo=timezone.utc) - timedelta(days=1)
    entries = (
        session.execute(
            select(ShiftEntry)
            .where(ShiftEntry.mine_id == mine.id, ShiftEntry.shift_date == day_start)
        ).scalars().all()
    )
    values: dict[str, float] = {}
    if entries:
        for ev in session.execute(
            select(EntryValue).where(EntryValue.shift_entry_id.in_([e.id for e in entries]))
        ).scalars():
            values[ev.metric.value] = values.get(ev.metric.value, 0) + float(ev.value)
    brief = {
        "mine": {"id": str(mine.id), "name": mine.name, "code": mine.code},
        "shift_date": day_start.date().isoformat(),
        "outgoing_shift": "second",
        "production": {
            "production_tonnes": values.get("production_tonnes", 3150),
            "overburden_m3": values.get("overburden_m3", 6400),
            "shift_target_tonnes": 3200,
            "achievement_pct": round(values.get("production_tonnes", 3150) / 3200 * 100, 1),
        },
        "pending": {"count": 0, "unapproved_entries": []},
        "equipment": {"stoppages": [
            {"type": "equipment_failure", "description": "Conveyor belt C-3 running hot since 14:30", "hours_lost": 1.5}
        ], "hours_lost": 1.5},
        "safety": {"observations": []},
        "weather": {"precipitation_mm": 0.0, "temp_max": 34.2, "wind_kmh": 11.4},
        "anomalies": [],
        "notes": ["Bench RL-130 dewatering pump shifted to north face"],
    }
    session.add(ShiftHandover(
        mine_id=mine.id, shift_date=day_start, outgoing_shift="second",
        brief=brief,
        critical_items=[
            "CHECK BEFORE LOADING: Conveyor belt C-3 running hot since 14:30 (1.5 h lost this shift)",
            "Bench RL-130 dewatering pump shifted to north face",
        ],
    ))
    session.flush()
    return 1


def seed_causes_and_anomalies(session: Session, mines: list[Mine]) -> tuple[int, int]:
    """Attach approved cause records + anomaly flags to existing shift entries so
    the narrative engine and loss-ledger derivation have live data to consume."""
    from app.domain.enums import AnomalyStatus, MetricName

    n_causes, n_anoms = 0, 0
    if not session.scalar(select(CauseRecord).limit(1)):
        mine = mines[0]
        entries = (
            session.execute(
                select(ShiftEntry)
                .where(ShiftEntry.mine_id == mine.id)
                .order_by(ShiftEntry.shift_date.desc())
                .limit(9)
            )
        ).scalars().all()
        cause_defs = [
            (CauseType.EQUIPMENT_FAILURE, "Dragline #3 breakdown — main shaft bearing overheated", 4.5),
            (CauseType.RAIN_WEATHER, "45 mm rainfall 06:00-08:30, haul road muck", 2.5),
            (CauseType.POWER_FAILURE, "11kV feeder trip — dewatering pumps offline", 1.5),
            (CauseType.EQUIPMENT_FAILURE, "Shovel #2 hydraulic hose burst", 3.0),
            (CauseType.BLASTING_DELAY, "Misfire re-drilling delayed bench face opening", 2.0),
        ]
        for i, e in enumerate(entries):
            if i < len(cause_defs):
                ctype, cdesc, chours = cause_defs[i]
                session.add(CauseRecord(
                    shift_entry_id=e.id, cause_type=ctype, description=cdesc,
                    hours_lost=Decimal(str(chours)),
                ))
                n_causes += 1
        session.flush()

    if not session.scalar(select(AnomalyFlag).limit(1)):
        mine = mines[0]
        monthly_target = session.execute(
            select(Target).where(
                Target.mine_id == mine.id,
                Target.period == TargetPeriod.MONTHLY,
                Target.metric == MetricName.PRODUCTION_TONNES,
            ).limit(1)
        ).scalars().first()
        entries = (
            session.execute(
                select(ShiftEntry)
                .where(ShiftEntry.mine_id == mine.id)
                .order_by(ShiftEntry.shift_date.desc())
                .limit(5)
            )
        ).scalars().all()
        # Down-production anomaly on a recent day (expected ~avg of last 20, actual much lower)
        expected = Decimal("3150")
        actual = Decimal("1820")
        flag_date = entries[0].shift_date if entries else NOW
        session.add(AnomalyFlag(
            mine_id=mine.id,
            flag_date=flag_date,
            metric="production_tonnes",
            expected_value=expected,
            actual_value=actual,
            anomaly_score=Decimal("0.92"),
            contributing_features={"z_score": -3.8, "window_days": 20},
            status=AnomalyStatus.FLAGGED,
        ))
        n_anoms += 1
        # Workers-present anomaly (safety-adjacent pattern)
        session.add(AnomalyFlag(
            mine_id=mine.id,
            flag_date=flag_date,
            metric="workers_present",
            expected_value=Decimal("62"),
            actual_value=Decimal("38"),
            anomaly_score=Decimal("0.87"),
            contributing_features={"z_score": -2.9, "window_days": 20},
            status=AnomalyStatus.FLAGGED,
        ))
        n_anoms += 1
        session.flush()
    return n_causes, n_anoms


def main() -> None:
    with Session(engine) as session:
        mines = (session.execute(select(Mine).where(Mine.is_active))).scalars().all()
        if not mines:
            print("Run scripts/seed.py first (base data missing).")
            return

        n_causes, n_anoms = seed_causes_and_anomalies(session, mines)
        n_patterns = seed_question_patterns(session)
        pqs = seed_historical_pqs(session, session.execute(select(QuestionPattern)).scalars().all())
        n_samples, n_preds = seed_quality(session, mines)
        n_losses = seed_loss_ledger(session, mines)
        n_obligations = seed_compliance(session)
        n_explosives = seed_explosives(session, mines)
        geo = seed_geology(session, mines)
        preds, obs = geo if isinstance(geo, tuple) else (geo, 0)
        n_handovers = seed_handovers(session, mines)

        session.commit()
        print("Innovations seed complete!")
        print(f"  Cause records: {n_causes}, anomaly flags: {n_anoms}")
        print(f"  PQ patterns: {n_patterns}, historical PQs: {pqs}")
        print(f"  Quality samples: {n_samples}, predictions: {n_preds}")
        print(f"  Loss ledger entries: {n_losses}")
        print(f"  Compliance obligations: {n_obligations}")
        print(f"  Explosive logs: {n_explosives}")
        print(f"  Geological predictions: {preds}, observations: {obs}")
        print(f"  Shift handovers: {n_handovers}")


if __name__ == "__main__":
    main()
