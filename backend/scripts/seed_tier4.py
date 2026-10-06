"""Seed demo data for Tier-4 innovations (idempotent — safe to re-run).

Covers: Meeting Action Tracker, Institutional Knowledge Preservation,
Safety Incident Pattern Detector, Photo-Evidence Geo-Verification.
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
    IncidentCategory,
    IncidentSeverity,
    KnowledgeCategory,
    MeetingActionStatus,
    MeetingType,
    PhotoVerificationStatus,
)
from app.domain.models import (
    KnowledgeEntry,
    MeetingAction,
    Mine,
    PhotoEvidence,
    SafetyIncident,
    SafetyPattern,
)
from app.core.config import settings

NOW = datetime.now(timezone.utc)

engine = create_engine(settings.database_url.replace("+asyncpg", ""))


def _get_mines(session: Session) -> list[Mine]:
    return list(session.execute(select(Mine).where(Mine.is_active == True)).scalars().all())


def seed_meeting_actions(session: Session, mines: list[Mine]):
    existing = session.execute(select(MeetingAction).limit(1)).scalar_one_or_none()
    if existing:
        print("  Meeting actions already seeded, skipping")
        return

    actions_data = [
        ("Install additional dewatering pumps at Bench B3", MeetingType.SAFETY, MeetingActionStatus.OPEN, 5),
        ("Recalibrate weighbridge at siding point", MeetingType.PRODUCTION, MeetingActionStatus.IN_PROGRESS, 3),
        ("Submit revised blasting plan to DGMS", MeetingType.PLANNING, MeetingActionStatus.COMPLETED, -2),
        ("Repair shovel #4 hydraulic system", MeetingType.PRODUCTION, MeetingActionStatus.OVERDUE, -5),
        ("Conduct safety drill for monsoon season", MeetingType.SAFETY, MeetingActionStatus.OPEN, 10),
        ("Update geological map for Seam IV", MeetingType.REVIEW, MeetingActionStatus.IN_PROGRESS, 7),
        ("Arrange refresher training for dumper operators", MeetingType.SAFETY, MeetingActionStatus.OPEN, 14),
        ("Review dispatch schedule for Q4 targets", MeetingType.PLANNING, MeetingActionStatus.COMPLETED, -1),
    ]

    assignees = ["Rajesh Kumar", "Anil Singh", "Suresh Reddy", "Priya Sharma", "Meena Patel"]

    for i, (title, mtype, status, due_offset) in enumerate(actions_data):
        mine = mines[i % len(mines)]
        action = MeetingAction(
            mine_id=mine.id,
            meeting_type=mtype,
            meeting_date=NOW - timedelta(days=random.randint(1, 10)),
            title=title,
            description=f"Action from {mtype.value} meeting",
            assigned_to=assignees[i % len(assignees)],
            assigned_role="shift_supervisor",
            due_date=NOW + timedelta(days=due_offset),
            status=status,
            completed_at=NOW - timedelta(days=1) if status == MeetingActionStatus.COMPLETED else None,
        )
        session.add(action)

    print(f"  Seeded {len(actions_data)} meeting actions")


def seed_knowledge_entries(session: Session, mines: list[Mine]):
    existing = session.execute(select(KnowledgeEntry).limit(1)).scalar_one_or_none()
    if existing:
        print("  Knowledge entries already seeded, skipping")
        return

    entries = [
        (KnowledgeCategory.GEOLOGICAL, "Seam IV fault zone navigation",
         "When approaching the known fault zone near Bench B3 (elevation 180m), reduce advance rate to 2m/day "
         "and increase probe drilling frequency. The fault displaces Seam IV by 3-5m vertically. Historical data "
         "from 2018-2022 shows water ingress risk increases 40% within 15m of the fault plane.",
         "R.K. Sharma", "Chief Geologist", 28, ["fault-zone", "seam-iv", "water-risk"]),
        (KnowledgeCategory.OPERATIONAL, "Monsoon season OB removal strategy",
         "During heavy monsoon (Jul-Sep), switch to shorter OB hauls by using temporary dump yards 200m from pit edge "
         "rather than the main OB dump 1.2km away. This maintains 60-70% of dry-season output despite reduced operating "
         "hours. Critical: ensure haul road drainage channels are cleared daily.",
         "Anil Prasad", "Senior Mining Engineer", 22, ["monsoon", "ob-removal", "haul-road"]),
        (KnowledgeCategory.SAFETY, "Pre-monsoon slope stability protocol",
         "In May-June, inspect all highwall faces >20m for tension cracks using drone surveys. Mark 10m exclusion "
         "zones around any new cracks. The 2019 slope failure at Bench A2 was preceded by hairline cracks visible "
         "3 weeks before failure. Weekly crack-width measurements with digital caliper are mandatory.",
         "Meena Patel", "Safety Officer", 15, ["slope-stability", "highwall", "monsoon"]),
        (KnowledgeCategory.EQUIPMENT, "Shovel bucket tooth replacement schedule",
         "Standard OEM recommendation is 800 operating hours but for our laterite-rich overburden, teeth wear "
         "out by 550-600 hours. Waiting for OEM schedule causes 15-20% drop in digging efficiency in the last "
         "150 hours. Pre-emptive replacement at 550 hrs saves ~3% fuel and avoids unplanned breakdowns.",
         "Suresh Verma", "Maintenance Supervisor", 18, ["shovel", "maintenance", "teeth"]),
        (KnowledgeCategory.ENVIRONMENTAL, "Dust suppression in summer months",
         "Water sprinklers alone are insufficient in May peak heat (>42°C). Mix 0.5% calcium chloride in sprinkler "
         "water for haul roads — reduces re-suspension by 60% compared to water alone. Apply at 6am before shift "
         "start. Reapply if wind exceeds 25 km/h. Cost: ~₹2/sq.m vs ₹8/sq.m for polymer-based suppressants.",
         "K. Venkatesh", "Environment Officer", 12, ["dust", "summer", "haul-road"]),
        (KnowledgeCategory.REGULATORY, "DGMS Form-14 submission tips",
         "Always cross-check production figures against dispatch records before submission. DGMS inspectors compare "
         "Form-14 monthly totals with railway siding records. Any discrepancy >2% triggers an inquiry. Keep a "
         "reconciliation sheet linking each Form-14 line item to the source shift entry for audit trail.",
         "D.N. Mishra", "Compliance Manager", 20, ["dgms", "form-14", "compliance"]),
    ]

    for cat, title, content, author, designation, years, tags in entries:
        mine = random.choice(mines) if cat != KnowledgeCategory.REGULATORY else None
        ke = KnowledgeEntry(
            mine_id=mine.id if mine else None,
            category=cat,
            title=title,
            content=content,
            author_name=author,
            author_designation=designation,
            years_experience=years,
            tags=tags,
            is_verified=random.random() > 0.3,
        )
        session.add(ke)

    print(f"  Seeded {len(entries)} knowledge entries")


def seed_safety_incidents(session: Session, mines: list[Mine]):
    existing = session.execute(select(SafetyIncident).limit(1)).scalar_one_or_none()
    if existing:
        print("  Safety incidents already seeded, skipping")
        return

    incidents = [
        (IncidentCategory.SLOPE_FAILURE, IncidentSeverity.MODERATE, "Minor slope slump on Bench A2 highwall",
         "Bench A2, 195m elevation", 0, 0),
        (IncidentCategory.EQUIPMENT, IncidentSeverity.MINOR, "Dumper brake failure during descent on haul road",
         "Haul road section 3, gradient 8%", 1, 0),
        (IncidentCategory.BLASTING, IncidentSeverity.NEAR_MISS, "Fly rock from blast landed 5m outside exclusion zone",
         "Bench B1, blast area 7", 0, 0),
        (IncidentCategory.TRANSPORT, IncidentSeverity.MINOR, "Two dumpers collided at intersection point",
         "Junction J4, near crusher", 2, 1),
        (IncidentCategory.ELECTRICAL, IncidentSeverity.MODERATE, "Transformer fault caused 2-hour power outage",
         "Substation SS-2", 0, 0),
        (IncidentCategory.SLOPE_FAILURE, IncidentSeverity.SERIOUS, "Major crack developed on Bench B3 face",
         "Bench B3, 180m elevation, near fault zone", 0, 0),
        (IncidentCategory.EQUIPMENT, IncidentSeverity.NEAR_MISS, "Shovel boom cable frayed, spotted during inspection",
         "Shovel #3, Bench A1", 0, 0),
        (IncidentCategory.WATER_INRUSH, IncidentSeverity.MODERATE, "Water seepage increased after heavy rain",
         "Bench B3, sump area", 3, 0),
        (IncidentCategory.FIRE, IncidentSeverity.MINOR, "Small fire in workshop welding area",
         "Central workshop", 2, 0),
        (IncidentCategory.SLOPE_FAILURE, IncidentSeverity.MINOR, "Small rockfall from weathered face",
         "Bench A3, 210m elevation", 0, 0),
        (IncidentCategory.EQUIPMENT, IncidentSeverity.MINOR, "Excavator track link failure",
         "Bench B2", 1, 0),
        (IncidentCategory.BLASTING, IncidentSeverity.NEAR_MISS, "Misfire detected — one hole did not detonate",
         "Bench A1, blast round 12", 0, 0),
    ]

    for i, (cat, sev, desc, loc, workers, injuries) in enumerate(incidents):
        mine = mines[i % len(mines)]
        inc = SafetyIncident(
            mine_id=mine.id,
            incident_date=NOW - timedelta(days=random.randint(1, 90)),
            category=cat,
            severity=sev,
            description=desc,
            location_description=loc,
            workers_involved=workers,
            injuries=injuries,
            root_cause="" if sev == IncidentSeverity.NEAR_MISS else "Under investigation",
        )
        session.add(inc)

    print(f"  Seeded {len(incidents)} safety incidents")

    patterns = [
        (IncidentCategory.SLOPE_FAILURE, "Recurring slope instability",
         "Three slope-related incidents in 90 days across multiple benches. "
         "Pattern suggests systematic highwall management issues.",
         3, Decimal("0.82"),
         ["geological", "rainfall", "bench-height"],
         ["Increase highwall inspection frequency to weekly",
          "Commission independent slope stability assessment",
          "Install crack monitoring pins on all faces >15m"]),
        (IncidentCategory.EQUIPMENT, "Equipment maintenance gaps",
         "Multiple equipment failures suggesting preventive maintenance shortfalls.",
         3, Decimal("0.71"),
         ["maintenance-backlog", "operating-hours", "age-of-fleet"],
         ["Audit current PM schedule compliance",
          "Consider condition-based monitoring for critical components"]),
    ]

    for cat, name, desc, count, conf, factors, recs in patterns:
        mine = random.choice(mines)
        sp = SafetyPattern(
            mine_id=mine.id,
            pattern_name=name,
            category=cat,
            description=desc,
            incident_count=count,
            confidence=conf,
            contributing_factors=factors,
            recommendations=recs,
        )
        session.add(sp)

    print(f"  Seeded {len(patterns)} safety patterns")


def seed_photo_evidence(session: Session, mines: list[Mine]):
    existing = session.execute(select(PhotoEvidence).limit(1)).scalar_one_or_none()
    if existing:
        print("  Photo evidence already seeded, skipping")
        return

    photos = []
    for mine in mines[:3]:
        lat = float(mine.latitude) if mine.latitude else 23.6
        lng = float(mine.longitude) if mine.longitude else 85.4

        photos.append(PhotoEvidence(
            mine_id=mine.id,
            filename=f"bench_progress_{mine.code}_001.jpg",
            object_key=f"photos/{uuid.uuid4()}.jpg",
            photo_latitude=Decimal(str(round(lat + random.uniform(-0.001, 0.001), 6))),
            photo_longitude=Decimal(str(round(lng + random.uniform(-0.001, 0.001), 6))),
            photo_timestamp=NOW - timedelta(hours=random.randint(1, 48)),
            expected_latitude=mine.latitude,
            expected_longitude=mine.longitude,
            distance_m=Decimal(str(round(random.uniform(10, 150), 2))),
            verification_status=PhotoVerificationStatus.VERIFIED,
            context="Weekly bench progress photo",
        ))

        photos.append(PhotoEvidence(
            mine_id=mine.id,
            filename=f"safety_board_{mine.code}_002.jpg",
            object_key=f"photos/{uuid.uuid4()}.jpg",
            photo_latitude=Decimal(str(round(lat + random.uniform(-0.005, 0.005), 6))),
            photo_longitude=Decimal(str(round(lng + random.uniform(-0.005, 0.005), 6))),
            photo_timestamp=NOW - timedelta(hours=random.randint(1, 24)),
            expected_latitude=mine.latitude,
            expected_longitude=mine.longitude,
            distance_m=Decimal(str(round(random.uniform(200, 800), 2))),
            verification_status=PhotoVerificationStatus.PENDING,
            context="Safety board compliance check",
        ))

        photos.append(PhotoEvidence(
            mine_id=mine.id,
            filename=f"equipment_{mine.code}_003.jpg",
            object_key=f"photos/{uuid.uuid4()}.jpg",
            photo_latitude=None,
            photo_longitude=None,
            photo_timestamp=None,
            expected_latitude=mine.latitude,
            expected_longitude=mine.longitude,
            distance_m=None,
            verification_status=PhotoVerificationStatus.PENDING,
            verification_notes="No EXIF GPS data found",
            context="Equipment condition report",
        ))

    for p in photos:
        session.add(p)

    print(f"  Seeded {len(photos)} photo evidence records")


def main():
    print("Seeding Tier-4 innovation data...")
    with Session(engine) as session:
        mines = _get_mines(session)
        if not mines:
            print("ERROR: No mines found. Run the base seed script first.")
            sys.exit(1)
        print(f"  Found {len(mines)} mines")

        seed_meeting_actions(session, mines)
        seed_knowledge_entries(session, mines)
        seed_safety_incidents(session, mines)
        seed_photo_evidence(session, mines)

        session.commit()
        print("Done! Tier-4 seed data committed.")


if __name__ == "__main__":
    main()
