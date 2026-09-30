"""Seed database with demo data for MINOVA mining platform."""
from __future__ import annotations

import hashlib
import json
import random
import sys
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session

from app.domain.enums import (
    AnomalyStatus,
    ApprovalAction,
    ApprovalRuleType,
    AuditAction,
    CauseType,
    ConflictResolution,
    EntryStatus,
    MetricName,
    OrgUnitType,
    ReportPeriod,
    ShiftNumber,
    TargetPeriod,
)
from app.domain.models import (
    AnomalyFlag,
    AppUser,
    ApprovalChain,
    ApprovalLevel,
    AuditEvent,
    Base,
    Bench,
    ConflictFlag,
    EntryValue,
    Mine,
    OrgUnit,
    Permission,
    ReportTemplate,
    ReportTemplateVersion,
    Role,
    RolePermission,
    ShiftEntry,
    Target,
    UserRole,
    WeatherObservation,
)

DB_URL = "postgresql+psycopg2://minova_app:minova_dev@localhost:5433/minova"
engine = create_engine(DB_URL, echo=False)

random.seed(42)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def uid() -> uuid.UUID:
    return uuid.uuid4()


def make_hash(prev: str, payload: str) -> str:
    return hashlib.sha256(f"{prev}|{payload}".encode()).hexdigest()


def main() -> None:
    with Session(engine) as session:
        existing = session.scalar(select(text("count(*)")).select_from(OrgUnit.__table__))
        if existing and existing > 0:
            print(f"Database already has {existing} org units — skipping seed.")
            return

        print("Seeding MINOVA demo data...")

        # --- ORG UNITS ---
        hq_id = uid()
        ecl_id, bccl_id, ccl_id = uid(), uid(), uid()
        org_units = [
            OrgUnit(id=hq_id, name="Coal India Limited", unit_type=OrgUnitType.ORGANISATION, code="CIL"),
            OrgUnit(id=ecl_id, parent_id=hq_id, name="Eastern Coalfields Limited", unit_type=OrgUnitType.SUBSIDIARY, code="ECL"),
            OrgUnit(id=bccl_id, parent_id=hq_id, name="Bharat Coking Coal Limited", unit_type=OrgUnitType.SUBSIDIARY, code="BCCL"),
            OrgUnit(id=ccl_id, parent_id=hq_id, name="Central Coalfields Limited", unit_type=OrgUnitType.SUBSIDIARY, code="CCL"),
        ]
        session.add_all(org_units)
        session.flush()
        print(f"  Org units: {len(org_units)}")

        # --- MINES ---
        mine_defs = [
            (ecl_id, "Rajmahal OCP", "RAJMAHAL", Decimal("24.7137"), Decimal("87.8449")),
            (ecl_id, "Sonepur Bazari OCP", "SONEPUR", Decimal("23.6830"), Decimal("87.3547")),
            (bccl_id, "Jharia Mine", "JHARIA", Decimal("23.7413"), Decimal("86.4052")),
            (bccl_id, "Moonidih UG Mine", "MOONIDIH", Decimal("23.7571"), Decimal("86.3808")),
            (ccl_id, "Piparwar OCP", "PIPARWAR", Decimal("23.8451"), Decimal("84.0942")),
            (ccl_id, "Gevra OCP", "GEVRA", Decimal("22.3413"), Decimal("82.5802")),
        ]
        mine_ids = []
        mines = []
        for org_id, name, code, lat, lng in mine_defs:
            mid = uid()
            mine_ids.append(mid)
            mines.append(Mine(id=mid, org_unit_id=org_id, name=name, code=code, latitude=lat, longitude=lng))
        session.add_all(mines)
        session.flush()
        print(f"  Mines: {len(mines)}")

        # --- BENCHES ---
        bench_ids_by_mine: dict[uuid.UUID, list[uuid.UUID]] = {}
        all_benches = []
        for i, mid in enumerate(mine_ids):
            bench_ids_by_mine[mid] = []
            for lvl in range(1, 4):
                bid = uid()
                bench_ids_by_mine[mid].append(bid)
                all_benches.append(Bench(
                    id=bid, mine_id=mid,
                    name=f"Bench {lvl} - {mines[i].code}",
                    bench_level=f"RL-{100 + lvl * 15}",
                    elevation_m=Decimal(str(100 + lvl * 15)),
                ))
        session.add_all(all_benches)
        session.flush()
        print(f"  Benches: {len(all_benches)}")

        # --- ROLES ---
        role_defs = [
            ("admin", "System Administrator", 100, True),
            ("hq_viewer", "HQ Viewer", 90, True),
            ("subsidiary_gm", "Subsidiary General Manager", 80, False),
            ("mine_manager", "Mine Manager", 60, False),
            ("shift_supervisor", "Shift Supervisor", 40, False),
            ("data_entry_operator", "Data Entry Operator", 20, False),
            ("auditor", "Auditor", 70, False),
            ("geologist", "Geologist", 50, False),
        ]
        role_ids: dict[str, uuid.UUID] = {}
        roles = []
        for name, display, level, is_sys in role_defs:
            rid = uid()
            role_ids[name] = rid
            roles.append(Role(id=rid, name=name, display_name=display, level=level, is_system=is_sys))
        session.add_all(roles)
        session.flush()
        print(f"  Roles: {len(roles)}")

        # --- PERMISSIONS ---
        resources = ["shift_entry", "report", "approval", "conflict", "document", "anomaly", "weather", "admin", "chat", "lineage"]
        actions = ["create", "read", "update", "delete", "approve", "export"]
        perm_ids: dict[str, uuid.UUID] = {}
        perms = []
        for res in resources:
            for act in actions:
                pid = uid()
                perm_ids[f"{res}:{act}"] = pid
                perms.append(Permission(id=pid, resource=res, action=act, description=f"Can {act} {res}"))
        session.add_all(perms)
        session.flush()
        print(f"  Permissions: {len(perms)}")

        # --- ROLE-PERMISSION ASSIGNMENTS ---
        role_perms_map = {
            "admin": [f"{r}:{a}" for r in resources for a in actions],
            "hq_viewer": [f"{r}:read" for r in resources] + [f"{r}:export" for r in resources],
            "subsidiary_gm": [f"{r}:read" for r in resources] + [f"{r}:export" for r in resources]
                + ["shift_entry:approve", "report:approve", "approval:approve", "conflict:update"],
            "mine_manager": ["shift_entry:read", "shift_entry:approve", "report:read", "report:create", "report:export",
                "approval:read", "approval:approve", "conflict:read", "conflict:update",
                "document:read", "document:create", "anomaly:read", "anomaly:update",
                "weather:read", "chat:read", "chat:create", "lineage:read"],
            "shift_supervisor": ["shift_entry:read", "shift_entry:approve", "report:read",
                "approval:read", "approval:approve", "conflict:read",
                "document:read", "anomaly:read", "weather:read", "chat:read", "chat:create", "lineage:read"],
            "data_entry_operator": ["shift_entry:create", "shift_entry:read", "shift_entry:update",
                "document:create", "document:read", "chat:read", "chat:create", "weather:read"],
            "auditor": [f"{r}:read" for r in resources] + ["lineage:export", "report:export"],
            "geologist": ["document:read", "document:create", "chat:read", "chat:create",
                "weather:read", "anomaly:read", "lineage:read", "report:read"],
        }
        role_perm_links = []
        for role_name, perm_keys in role_perms_map.items():
            for pk in perm_keys:
                if pk in perm_ids and role_name in role_ids:
                    role_perm_links.append(RolePermission(role_id=role_ids[role_name], permission_id=perm_ids[pk]))
        session.add_all(role_perm_links)
        session.flush()
        print(f"  Role-Permission links: {len(role_perm_links)}")

        # --- USERS ---
        user_defs = [
            ("hq_admin", "Arvind Kumar", "arvind.kumar@cil.in", None, "admin", "IT", "CTO"),
            ("ecl_gm", "Priya Sharma", "priya.sharma@ecl.in", mine_ids[0], "subsidiary_gm", "Management", "General Manager"),
            ("bccl_gm", "Rajesh Patel", "rajesh.patel@bccl.in", mine_ids[2], "subsidiary_gm", "Management", "General Manager"),
            ("ccl_gm", "Meera Reddy", "meera.reddy@ccl.in", mine_ids[4], "subsidiary_gm", "Management", "General Manager"),
            ("mine_manager_1", "Sanjay Verma", "sanjay.verma@ecl.in", mine_ids[0], "mine_manager", "Production", "Mine Manager"),
            ("mine_manager_2", "Anil Gupta", "anil.gupta@ecl.in", mine_ids[1], "mine_manager", "Production", "Mine Manager"),
            ("mine_manager_3", "Deepak Singh", "deepak.singh@bccl.in", mine_ids[2], "mine_manager", "Production", "Mine Manager"),
            ("mine_manager_4", "Kavita Nair", "kavita.nair@ccl.in", mine_ids[4], "mine_manager", "Production", "Mine Manager"),
            ("shift_sup_1", "Ramesh Yadav", "ramesh.yadav@ecl.in", mine_ids[0], "shift_supervisor", "Operations", "Shift Supervisor"),
            ("shift_sup_2", "Sunil Das", "sunil.das@bccl.in", mine_ids[2], "shift_supervisor", "Operations", "Shift Supervisor"),
            ("shift_sup_3", "Vikas Tiwari", "vikas.tiwari@ccl.in", mine_ids[4], "shift_supervisor", "Operations", "Shift Supervisor"),
            ("data_entry_1", "Pooja Kumari", "pooja.kumari@ecl.in", mine_ids[0], "data_entry_operator", "Operations", "Data Entry Operator"),
        ]
        user_ids: dict[str, uuid.UUID] = {}
        users = []
        for username, full_name, email, mine_id, role_name, dept, desig in user_defs:
            u_id = uid()
            user_ids[username] = u_id
            kc_sub = str(uid())
            users.append(AppUser(
                id=u_id, keycloak_id=kc_sub, username=username, full_name=full_name,
                email=email, mine_id=mine_id, department=dept, designation=desig,
            ))
        session.add_all(users)
        session.flush()
        print(f"  Users: {len(users)}")

        # User-Role assignments
        user_role_links = []
        for username, _, _, _, role_name, _, _ in user_defs:
            user_role_links.append(UserRole(user_id=user_ids[username], role_id=role_ids[role_name]))
        session.add_all(user_role_links)
        session.flush()
        print(f"  User-Role links: {len(user_role_links)}")

        # --- APPROVAL CHAINS ---
        chains = []
        levels = []
        for i, mid in enumerate(mine_ids):
            cid = uid()
            chains.append(ApprovalChain(
                id=cid, name=f"{mines[i].name} Production Approval",
                report_type="shift_entry", mine_id=mid,
            ))
            levels.extend([
                ApprovalLevel(chain_id=cid, sequence=1, role_name="shift_supervisor",
                    rule=ApprovalRuleType.ANY_OF, sla_hours=8),
                ApprovalLevel(chain_id=cid, sequence=2, role_name="mine_manager",
                    rule=ApprovalRuleType.ANY_OF, sla_hours=24,
                    escalation_role="subsidiary_gm"),
                ApprovalLevel(chain_id=cid, sequence=3, role_name="subsidiary_gm",
                    rule=ApprovalRuleType.ANY_OF, sla_hours=48, can_skip=True),
            ])
        session.add_all(chains)
        session.add_all(levels)
        session.flush()
        print(f"  Approval chains: {len(chains)}, levels: {len(levels)}")

        # --- REPORT TEMPLATES ---
        templates = []
        versions = []
        for period_name, period_val in [("Daily", ReportPeriod.DAILY), ("Weekly", ReportPeriod.WEEKLY), ("Monthly", ReportPeriod.MONTHLY)]:
            tid = uid()
            templates.append(ReportTemplate(id=tid, name=f"{period_name} Production Report", report_type="production", period=period_val))
            versions.append(ReportTemplateVersion(
                template_id=tid, version=1,
                definition={
                    "sections": [
                        {"name": "production", "metrics": ["production_tonnes", "overburden_m3", "stripping_ratio"]},
                        {"name": "operations", "metrics": ["operating_hours", "downtime_hours", "equipment_availability"]},
                        {"name": "dispatch", "metrics": ["dispatch_tonnes"]},
                        {"name": "workforce", "metrics": ["workers_present"]},
                    ],
                    "aggregation": period_name.lower(),
                },
            ))
        session.add_all(templates)
        session.add_all(versions)
        session.flush()
        print(f"  Report templates: {len(templates)}")

        # --- TARGETS ---
        fy_start = datetime(2026, 4, 1, tzinfo=timezone.utc)
        fy_end = datetime(2027, 3, 31, 23, 59, 59, tzinfo=timezone.utc)
        annual_targets_tonnes = [
            Decimal("3500000"), Decimal("2800000"), Decimal("4200000"),
            Decimal("1800000"), Decimal("5000000"), Decimal("6500000"),
        ]
        targets = []
        for i, mid in enumerate(mine_ids):
            annual_tid = uid()
            targets.append(Target(
                id=annual_tid, mine_id=mid, period=TargetPeriod.ANNUAL,
                metric=MetricName.PRODUCTION_TONNES, value=annual_targets_tonnes[i],
                unit="tonnes", period_start=fy_start, period_end=fy_end,
            ))
            quarterly_value = (annual_targets_tonnes[i] / 4).quantize(Decimal("0.0001"))
            for q in range(4):
                q_start = fy_start + timedelta(days=q * 91)
                q_end = q_start + timedelta(days=90)
                if q_end > fy_end:
                    q_end = fy_end
                targets.append(Target(
                    mine_id=mid, period=TargetPeriod.QUARTERLY,
                    metric=MetricName.PRODUCTION_TONNES, value=quarterly_value,
                    unit="tonnes", period_start=q_start, period_end=q_end,
                    parent_target_id=annual_tid, weight=Decimal("0.2500"),
                ))
        session.add_all(targets)
        session.flush()
        print(f"  Targets: {len(targets)}")

        # --- SHIFT ENTRIES (7 days for mine_1) ---
        mine_1 = mine_ids[0]
        submitter = user_ids["data_entry_1"]
        supervisor = user_ids["shift_sup_1"]
        today = date(2026, 9, 30)
        entries = []
        entry_values = []
        shifts = [ShiftNumber.FIRST, ShiftNumber.SECOND, ShiftNumber.THIRD]

        for day_offset in range(7):
            d = today - timedelta(days=day_offset + 1)
            shift_dt = datetime(d.year, d.month, d.day, tzinfo=timezone.utc)
            for shift in shifts:
                eid = uid()
                production = Decimal(str(random.randint(2800, 3500)))
                ob_volume = Decimal(str(random.randint(5000, 8000)))
                op_hours = Decimal(str(round(random.uniform(6.0, 8.0), 1)))
                workers = Decimal(str(random.randint(45, 80)))

                entries.append(ShiftEntry(
                    id=eid, mine_id=mine_1, bench_id=bench_ids_by_mine[mine_1][day_offset % 3],
                    shift_date=shift_dt, shift_number=shift, status=EntryStatus.APPROVED,
                    submitted_by=submitter, submitted_at=shift_dt + timedelta(hours=9),
                    version=1, remarks=f"Normal operations - {d.isoformat()}",
                ))
                entry_values.extend([
                    EntryValue(shift_entry_id=eid, metric=MetricName.PRODUCTION_TONNES, value=production, unit="tonnes"),
                    EntryValue(shift_entry_id=eid, metric=MetricName.OVERBURDEN_M3, value=ob_volume, unit="m3"),
                    EntryValue(shift_entry_id=eid, metric=MetricName.OPERATING_HOURS, value=op_hours, unit="hours"),
                    EntryValue(shift_entry_id=eid, metric=MetricName.WORKERS_PRESENT, value=workers, unit="count"),
                ])
        session.add_all(entries)
        session.add_all(entry_values)
        session.flush()
        print(f"  Shift entries: {len(entries)}, values: {len(entry_values)}")

        # --- SAMPLE CONFLICT ---
        conflict_entry = entries[0]
        conflict = ConflictFlag(
            entity_type="shift_entry", entity_id=conflict_entry.id,
            metric="production_tonnes",
            value_a=Decimal("3150.0000"), source_a="shift_entry",
            value_b=Decimal("3280.0000"), source_b="weighbridge",
            tolerance_pct=Decimal("2.0000"),
            resolution=ConflictResolution.UNRESOLVED,
        )
        session.add(conflict)
        session.flush()
        print("  Conflict: 1 unresolved")

        # --- AUDIT EVENTS (hash-chained) ---
        prev_hash = "0" * 64
        audits = []
        audit_payloads = [
            (AuditAction.CREATE, "mine", str(mine_1), user_ids["hq_admin"], {"name": "Rajmahal OCP"}),
            (AuditAction.CREATE, "shift_entry", str(entries[0].id), submitter, {"shift": "first", "date": str(today - timedelta(days=1))}),
            (AuditAction.SUBMIT, "shift_entry", str(entries[0].id), submitter, {"status": "submitted"}),
            (AuditAction.APPROVE, "shift_entry", str(entries[0].id), supervisor, {"status": "approved", "level": 1}),
            (AuditAction.CREATE, "conflict_flag", str(conflict.id), None, {"metric": "production_tonnes", "diff_pct": "4.13"}),
        ]
        for action, etype, eid_str, u_id, details in audit_payloads:
            payload = json.dumps({"action": action.value, "entity_type": etype, "entity_id": eid_str, "details": details}, sort_keys=True)
            cur_hash = make_hash(prev_hash, payload)
            audits.append(AuditEvent(
                action=action, entity_type=etype, entity_id=eid_str,
                user_id=u_id, details=details,
                previous_hash=prev_hash, current_hash=cur_hash,
            ))
            prev_hash = cur_hash
        session.add_all(audits)
        session.flush()
        print(f"  Audit events: {len(audits)} (hash-chained)")

        # --- WEATHER OBSERVATIONS ---
        weather = []
        for day_offset in range(7):
            d = today - timedelta(days=day_offset + 1)
            obs_dt = datetime(d.year, d.month, d.day, 6, 0, tzinfo=timezone.utc)
            weather.append(WeatherObservation(
                mine_id=mine_1, observation_date=obs_dt,
                temperature_max=Decimal(str(round(random.uniform(28.0, 38.0), 1))),
                temperature_min=Decimal(str(round(random.uniform(18.0, 25.0), 1))),
                precipitation_mm=Decimal(str(round(random.choice([0, 0, 0, 0, 2.5, 5.0, 12.0, 25.0, 0, 0]), 1))),
                wind_speed_kmh=Decimal(str(round(random.uniform(5.0, 25.0), 1))),
                humidity_pct=Decimal(str(round(random.uniform(40.0, 85.0), 1))),
                weather_code=random.choice([0, 1, 2, 3, 51, 61, 80]),
                source="open-meteo",
            ))
        session.add_all(weather)
        session.flush()
        print(f"  Weather observations: {len(weather)}")

        session.commit()
        print("\nSeed complete!")
        print(f"  {len(org_units)} org units, {len(mines)} mines, {len(all_benches)} benches")
        print(f"  {len(roles)} roles, {len(perms)} permissions, {len(users)} users")
        print(f"  {len(entries)} shift entries, {len(entry_values)} values")
        print(f"  {len(targets)} targets, {len(chains)} approval chains")
        print(f"  {len(audits)} audit events, {len(weather)} weather obs, 1 conflict")


if __name__ == "__main__":
    main()
