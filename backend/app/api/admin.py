from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID
import hashlib

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, select, text, and_, case, literal_column
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import CurrentUser, require_role
from app.domain.models import (
    AnomalyFlag, AppUser, ApprovalChain, ApprovalLevel, ApprovalTask, AuditEvent, Bench,
    ConflictFlag, EntryValue, Mine, OrgUnit, Role, ShiftEntry, Target,
    ReportTemplate, ReportTemplateVersion,
)
from app.domain.enums import (
    AnomalyStatus, ApprovalRuleType, ConflictResolution, EntryStatus, OrgUnitType, TargetPeriod,
)

router = APIRouter()


# --- Mines ---

class MineCreate(BaseModel):
    org_unit_id: UUID
    name: str
    code: str
    latitude: Decimal | None = None
    longitude: Decimal | None = None
    timezone: str = "Asia/Kolkata"
    shift_count: int = 3


class MineOut(BaseModel):
    id: UUID
    org_unit_id: UUID
    name: str
    code: str
    latitude: Decimal | None
    longitude: Decimal | None
    timezone: str
    shift_count: int
    is_active: bool
    model_config = {"from_attributes": True}


@router.get("/mines")
async def list_mines(db: AsyncSession = Depends(get_db), user: CurrentUser = None) -> list[MineOut]:
    result = await db.execute(select(Mine).where(Mine.is_active == True).order_by(Mine.name))
    return [MineOut.model_validate(m) for m in result.scalars().all()]


@router.post("/mines", status_code=201)
async def create_mine(data: MineCreate, db: AsyncSession = Depends(get_db), user: CurrentUser = None) -> MineOut:
    mine = Mine(**data.model_dump())
    db.add(mine)
    await db.flush()
    return MineOut.model_validate(mine)


# --- Users ---

@router.get("/users")
async def list_users(
    mine_id: UUID | None = None,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = None,
):
    from sqlalchemy.orm import selectinload
    stmt = select(AppUser).options(selectinload(AppUser.roles))
    if mine_id:
        stmt = stmt.where(AppUser.mine_id == mine_id)
    stmt = stmt.order_by(AppUser.username)
    result = await db.execute(stmt)
    users = result.scalars().unique().all()
    return [
        {
            "id": str(u.id),
            "username": u.username,
            "full_name": u.full_name,
            "email": u.email,
            "mine_id": str(u.mine_id) if u.mine_id else None,
            "department": u.department,
            "designation": u.designation,
            "is_active": u.is_active,
            "roles": [r.name for r in u.roles],
        }
        for u in users
    ]


# --- Benches ---

class BenchCreate(BaseModel):
    mine_id: UUID
    name: str
    bench_level: str
    elevation_m: Decimal | None = None


class BenchOut(BaseModel):
    id: UUID
    mine_id: UUID
    name: str
    bench_level: str
    elevation_m: Decimal | None
    is_active: bool
    model_config = {"from_attributes": True}


@router.get("/benches/{mine_id}")
async def list_benches(mine_id: UUID, db: AsyncSession = Depends(get_db), user: CurrentUser = None) -> list[BenchOut]:
    result = await db.execute(select(Bench).where(Bench.mine_id == mine_id, Bench.is_active == True))
    return [BenchOut.model_validate(b) for b in result.scalars().all()]


@router.post("/benches", status_code=201)
async def create_bench(data: BenchCreate, db: AsyncSession = Depends(get_db), user: CurrentUser = None) -> BenchOut:
    bench = Bench(**data.model_dump())
    db.add(bench)
    await db.flush()
    return BenchOut.model_validate(bench)


# --- Approval chains ---

class ApprovalLevelCreate(BaseModel):
    sequence: int
    role_name: str
    rule: ApprovalRuleType
    sla_hours: int = 24
    escalation_role: str | None = None
    can_skip: bool = False


class ApprovalChainCreate(BaseModel):
    name: str
    report_type: str
    mine_id: UUID | None = None
    levels: list[ApprovalLevelCreate]


class ApprovalChainOut(BaseModel):
    id: UUID
    name: str
    report_type: str
    mine_id: UUID | None
    is_active: bool
    model_config = {"from_attributes": True}


@router.get("/approval-chains")
async def list_approval_chains(
    mine_id: UUID | None = None,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = None,
) -> list[ApprovalChainOut]:
    stmt = select(ApprovalChain).where(ApprovalChain.is_active == True)
    if mine_id:
        stmt = stmt.where(ApprovalChain.mine_id == mine_id)
    result = await db.execute(stmt)
    return [ApprovalChainOut.model_validate(c) for c in result.scalars().all()]


@router.post("/approval-chains", status_code=201)
async def create_approval_chain(
    data: ApprovalChainCreate,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = None,
) -> ApprovalChainOut:
    chain = ApprovalChain(name=data.name, report_type=data.report_type, mine_id=data.mine_id)
    db.add(chain)
    await db.flush()
    for lvl_data in data.levels:
        lvl = ApprovalLevel(chain_id=chain.id, **lvl_data.model_dump())
        db.add(lvl)
    await db.flush()
    return ApprovalChainOut.model_validate(chain)


# --- Targets ---

class TargetCreate(BaseModel):
    mine_id: UUID
    bench_id: UUID | None = None
    period: TargetPeriod
    metric: str
    value: Decimal
    unit: str
    period_start: datetime
    period_end: datetime
    parent_target_id: UUID | None = None
    weight: Decimal = Decimal("1")


@router.post("/targets", status_code=201)
async def create_target(data: TargetCreate, db: AsyncSession = Depends(get_db), user: CurrentUser = None):
    from app.domain.models import Target
    target = Target(**data.model_dump())
    db.add(target)
    await db.flush()
    return {"id": str(target.id), "status": "created"}


# --- Report templates ---

class TemplateVersionCreate(BaseModel):
    template_id: UUID
    definition: dict


@router.get("/report-templates")
async def list_templates(db: AsyncSession = Depends(get_db), user: CurrentUser = None):
    result = await db.execute(select(ReportTemplate).where(ReportTemplate.is_active == True))
    templates = result.scalars().all()
    return [{"id": str(t.id), "name": t.name, "report_type": t.report_type, "period": t.period.value} for t in templates]


@router.post("/report-templates/versions", status_code=201)
async def create_template_version(
    data: TemplateVersionCreate,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = None,
):
    max_ver = await db.execute(
        select(func.max(ReportTemplateVersion.version)).where(
            ReportTemplateVersion.template_id == data.template_id
        )
    )
    current_max = max_ver.scalar() or 0
    ver = ReportTemplateVersion(
        template_id=data.template_id,
        version=current_max + 1,
        definition=data.definition,
        is_current=True,
    )
    db.add(ver)
    await db.flush()
    return {"id": str(ver.id), "version": ver.version}


# --- Audit chain verify ---

@router.post("/audit/verify-chain")
async def verify_audit_chain(
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = None,
):
    result = await db.execute(
        select(AuditEvent).order_by(AuditEvent.created_at)
    )
    events = result.scalars().all()
    if not events:
        return {"valid": True, "checked": 0, "message": "No audit events"}

    broken_at = None
    prev_hash = ""
    for i, evt in enumerate(events):
        if evt.previous_hash != prev_hash:
            broken_at = i
            break
        prev_hash = evt.current_hash

    return {
        "valid": broken_at is None,
        "checked": len(events),
        "broken_at_index": broken_at,
        "message": "Chain intact" if broken_at is None else f"Chain broken at event index {broken_at}",
    }


# --- System health ---

@router.get("/health")
async def system_health(db: AsyncSession = Depends(get_db)):
    checks = {}
    try:
        await db.execute(text("SELECT 1"))
        checks["database"] = True
    except Exception:
        checks["database"] = False

    try:
        await db.execute(text("SELECT extname FROM pg_extension WHERE extname = 'pgvector'"))
        checks["pgvector"] = True
    except Exception:
        checks["pgvector"] = False

    return {"status": "ok" if all(checks.values()) else "degraded", "checks": checks}


# ── Dashboard Summary ───────────────────────────────────────────────────────

@router.get("/dashboard")
async def dashboard_summary(
    mine_id: UUID | None = None,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = None,
):
    today = date.today()
    week_ago = today - timedelta(days=7)
    month_start = today.replace(day=1)

    mine_filter = ShiftEntry.mine_id == mine_id if mine_id else literal_column("TRUE")

    approved_statuses = [EntryStatus.APPROVED, EntryStatus.SUBMITTED, EntryStatus.SYNCED]
    prod_q = (
        select(func.coalesce(func.sum(EntryValue.value), 0))
        .join(ShiftEntry, ShiftEntry.id == EntryValue.shift_entry_id)
        .where(
            mine_filter,
            ShiftEntry.shift_date >= datetime.combine(today, datetime.min.time()),
            ShiftEntry.status.in_(approved_statuses),
            EntryValue.metric == "production_tonnes",
        )
    )
    today_production = float((await db.execute(prod_q)).scalar() or 0)

    monthly_prod_q = (
        select(func.coalesce(func.sum(EntryValue.value), 0))
        .join(ShiftEntry, ShiftEntry.id == EntryValue.shift_entry_id)
        .where(
            mine_filter,
            ShiftEntry.shift_date >= datetime.combine(month_start, datetime.min.time()),
            ShiftEntry.status.in_(approved_statuses),
            EntryValue.metric == "production_tonnes",
        )
    )
    monthly_production = float((await db.execute(monthly_prod_q)).scalar() or 0)

    monthly_target_q = (
        select(func.coalesce(func.sum(Target.value), 0))
        .where(
            Target.metric == "production_tonnes",
            Target.period == TargetPeriod.MONTHLY,
            Target.period_start >= datetime.combine(month_start, datetime.min.time()),
            Target.period_end <= datetime.combine(today, datetime.max.time()),
        )
    )
    if mine_id:
        monthly_target_q = monthly_target_q.where(Target.mine_id == mine_id)
    monthly_target = float((await db.execute(monthly_target_q)).scalar() or 0)
    target_pct = round(monthly_production / monthly_target * 100, 1) if monthly_target > 0 else 0.0

    pending_q = select(func.count()).select_from(ApprovalTask).where(ApprovalTask.action == None)
    pending_approvals = (await db.execute(pending_q)).scalar() or 0

    anomaly_q = select(func.count()).select_from(AnomalyFlag).where(AnomalyFlag.status == AnomalyStatus.FLAGGED)
    if mine_id:
        anomaly_q = anomaly_q.where(AnomalyFlag.mine_id == mine_id)
    active_anomalies = (await db.execute(anomaly_q)).scalar() or 0

    weekly = []
    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        day_prod_q = (
            select(func.coalesce(func.sum(EntryValue.value), 0))
            .join(ShiftEntry, ShiftEntry.id == EntryValue.shift_entry_id)
            .where(
                mine_filter,
                func.date(ShiftEntry.shift_date) == d,
                ShiftEntry.status.in_(approved_statuses),
                EntryValue.metric == "production_tonnes",
            )
        )
        day_val = float((await db.execute(day_prod_q)).scalar() or 0)
        day_target_q = (
            select(func.coalesce(func.sum(Target.value), 0))
            .where(
                Target.metric == "production_tonnes",
                Target.period == TargetPeriod.DAILY,
                func.date(Target.period_start) == d,
            )
        )
        if mine_id:
            day_target_q = day_target_q.where(Target.mine_id == mine_id)
        day_tgt = float((await db.execute(day_target_q)).scalar() or 0)
        weekly.append({"day": d.strftime("%a"), "date": d.isoformat(), "actual": day_val, "target": day_tgt})

    activity_q = (
        select(AuditEvent)
        .order_by(AuditEvent.created_at.desc())
        .limit(8)
    )
    activity_rows = (await db.execute(activity_q)).scalars().all()
    recent_activity = []
    for evt in activity_rows:
        recent_activity.append({
            "id": str(evt.id),
            "action": evt.action,
            "entity_type": evt.entity_type,
            "details": evt.details if isinstance(evt.details, dict) else {},
            "time": evt.created_at.isoformat(),
        })

    return {
        "today_production": today_production,
        "monthly_production": monthly_production,
        "monthly_target": monthly_target,
        "target_achievement_pct": target_pct,
        "pending_approvals": pending_approvals,
        "active_anomalies": active_anomalies,
        "weekly_production": weekly,
        "recent_activity": recent_activity,
    }


# ── Audit Events List ──────────────────────────────────────────────────────

@router.get("/audit")
async def list_audit_events(
    action: str | None = None,
    actor: str | None = None,
    entity_type: str | None = None,
    limit: int = Query(default=50, le=500),
    cursor: str | None = None,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = None,
):
    q = select(AuditEvent)
    if action:
        q = q.where(AuditEvent.action == action)
    if entity_type:
        q = q.where(AuditEvent.entity_type == entity_type)
    if actor:
        q = q.where(func.cast(AuditEvent.user_id, text("TEXT")).ilike(f"%{actor}%"))
    if cursor:
        q = q.where(AuditEvent.id < UUID(cursor))
    q = q.order_by(AuditEvent.created_at.desc()).limit(limit + 1)
    rows = (await db.execute(q)).scalars().all()
    has_more = len(rows) > limit
    items = rows[:limit]
    return {
        "items": [
            {
                "id": str(e.id),
                "ts": e.created_at.isoformat(),
                "actor": str(e.user_id) if e.user_id else "system",
                "action": e.action,
                "entity_type": e.entity_type,
                "entity_id": e.entity_id,
                "details": e.details if isinstance(e.details, dict) else {},
                "prev_hash": e.previous_hash or "",
                "event_hash": e.current_hash or "",
            }
            for e in items
        ],
        "has_more": has_more,
        "cursor": str(items[-1].id) if items else None,
    }


# ── Notifications Feed ──────────────────────────────────────────────────────

@router.get("/notifications")
async def notifications_feed(
    mine_id: UUID | None = None,
    limit: int = Query(default=20, le=100),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = None,
):
    notifications = []

    approval_q = (
        select(ApprovalTask)
        .where(ApprovalTask.action == None)
        .order_by(ApprovalTask.created_at.desc())
        .limit(5)
    )
    for task in (await db.execute(approval_q)).scalars().all():
        overdue = task.sla_deadline and task.sla_deadline < datetime.now(timezone.utc)
        notifications.append({
            "id": f"approval-{task.id}",
            "type": "approval",
            "title": "Approval Required" + (" (OVERDUE)" if overdue else ""),
            "body": f"{task.entity_type} {str(task.entity_id)[:8]}... pending Level {task.current_level} approval",
            "time": task.created_at.isoformat(),
            "read": False,
            "severity": "high" if overdue else "medium",
        })

    anomaly_q = (
        select(AnomalyFlag)
        .where(AnomalyFlag.status == AnomalyStatus.FLAGGED)
        .order_by(AnomalyFlag.created_at.desc())
        .limit(5)
    )
    if mine_id:
        anomaly_q = anomaly_q.where(AnomalyFlag.mine_id == mine_id)
    for flag in (await db.execute(anomaly_q)).scalars().all():
        notifications.append({
            "id": f"anomaly-{flag.id}",
            "type": "anomaly",
            "title": "Anomaly Detected",
            "body": f"{flag.metric}: expected {float(flag.expected_value):.0f}, got {float(flag.actual_value):.0f} (score {float(flag.anomaly_score):.0%})",
            "time": flag.created_at.isoformat(),
            "read": False,
            "severity": "high" if float(flag.anomaly_score) > 0.8 else "medium",
        })

    conflict_q = (
        select(ConflictFlag)
        .where(ConflictFlag.resolution == ConflictResolution.UNRESOLVED)
        .order_by(ConflictFlag.created_at.desc())
        .limit(5)
    )
    for cf in (await db.execute(conflict_q)).scalars().all():
        notifications.append({
            "id": f"conflict-{cf.id}",
            "type": "conflict",
            "title": "Conflict Flagged",
            "body": f"{cf.metric}: {float(cf.value_a):.0f} ({cf.source_a}) vs {float(cf.value_b):.0f} ({cf.source_b})",
            "time": cf.created_at.isoformat(),
            "read": False,
            "severity": "medium",
        })

    recent_events_q = (
        select(AuditEvent)
        .where(AuditEvent.entity_type.in_(["calc_run", "report"]))
        .order_by(AuditEvent.created_at.desc())
        .limit(3)
    )
    for evt in (await db.execute(recent_events_q)).scalars().all():
        action_label = str(evt.action).replace(".", " ").replace("_", " ").title()
        notifications.append({
            "id": f"system-{evt.id}",
            "type": "system" if evt.entity_type == "calc_run" else "report",
            "title": action_label,
            "body": f"{evt.entity_type} — {evt.details.get('description', evt.action) if isinstance(evt.details, dict) else evt.action}",
            "time": evt.created_at.isoformat(),
            "read": True,
            "severity": "low",
        })

    notifications.sort(key=lambda n: n["time"], reverse=True)
    return notifications[:limit]


# ── Insights / Trends ───────────────────────────────────────────────────────

@router.get("/insights")
async def insights_data(
    mine_id: UUID | None = None,
    months: int = Query(default=6, le=12),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = None,
):
    today = date.today()
    mine_filter = ShiftEntry.mine_id == mine_id if mine_id else literal_column("TRUE")
    approved_statuses = [EntryStatus.APPROVED, EntryStatus.SUBMITTED, EntryStatus.SYNCED]

    monthly_data = []
    for i in range(months - 1, -1, -1):
        m_start = (today.replace(day=1) - timedelta(days=i * 30)).replace(day=1)
        if m_start.month == 12:
            m_end = m_start.replace(year=m_start.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            m_end = m_start.replace(month=m_start.month + 1, day=1) - timedelta(days=1)

        prod_q = (
            select(func.coalesce(func.sum(EntryValue.value), 0))
            .join(ShiftEntry, ShiftEntry.id == EntryValue.shift_entry_id)
            .where(
                mine_filter,
                ShiftEntry.shift_date >= datetime.combine(m_start, datetime.min.time()),
                ShiftEntry.shift_date <= datetime.combine(m_end, datetime.max.time()),
                ShiftEntry.status.in_(approved_statuses),
                EntryValue.metric == "production_tonnes",
            )
        )
        actual = float((await db.execute(prod_q)).scalar() or 0)

        tgt_q = (
            select(func.coalesce(func.sum(Target.value), 0))
            .where(
                Target.metric == "production_tonnes",
                Target.period == TargetPeriod.MONTHLY,
                Target.period_start >= datetime.combine(m_start, datetime.min.time()),
                Target.period_end <= datetime.combine(m_end, datetime.max.time()),
            )
        )
        if mine_id:
            tgt_q = tgt_q.where(Target.mine_id == mine_id)
        target = float((await db.execute(tgt_q)).scalar() or 0)

        monthly_data.append({
            "month": m_start.strftime("%b"),
            "month_start": m_start.isoformat(),
            "target": target,
            "actual": actual,
        })

    days_back = 30
    daily_trend = []
    for i in range(days_back - 1, -1, -1):
        d = today - timedelta(days=i)
        prod_q = (
            select(func.coalesce(func.sum(EntryValue.value), 0))
            .join(ShiftEntry, ShiftEntry.id == EntryValue.shift_entry_id)
            .where(
                mine_filter,
                func.date(ShiftEntry.shift_date) == d,
                ShiftEntry.status.in_(approved_statuses),
                EntryValue.metric == "production_tonnes",
            )
        )
        ob_q = (
            select(func.coalesce(func.sum(EntryValue.value), 0))
            .join(ShiftEntry, ShiftEntry.id == EntryValue.shift_entry_id)
            .where(
                mine_filter,
                func.date(ShiftEntry.shift_date) == d,
                ShiftEntry.status.in_(approved_statuses),
                EntryValue.metric == "OVERBURDEN_M3",
            )
        )
        production = float((await db.execute(prod_q)).scalar() or 0)
        ob = float((await db.execute(ob_q)).scalar() or 0)
        daily_trend.append({"day": d.day, "date": d.isoformat(), "production": production, "ob": ob})

    from app.domain.models import Topic, TopicTerm
    topics_q = select(Topic).order_by(Topic.created_at.desc()).limit(10)
    topic_rows = (await db.execute(topics_q)).scalars().all()
    topics = []
    for t in topic_rows:
        terms_q = select(TopicTerm).where(TopicTerm.topic_id == t.id).order_by(TopicTerm.weight.desc()).limit(5)
        terms = (await db.execute(terms_q)).scalars().all()
        topics.append({
            "id": str(t.id),
            "label": t.label or f"Topic {t.id}",
            "doc_count": t.document_count,
            "weight": float(t.coherence_score) if t.coherence_score else 0.0,
            "terms": [{"term": tt.term, "weight": float(tt.weight)} for tt in terms],
        })

    word_freq: dict[str, int] = {}
    for t in topics:
        for term_info in t["terms"]:
            word = term_info["term"]
            word_freq[word] = word_freq.get(word, 0) + int(term_info["weight"] * 100)

    word_cloud = [
        {"text": w, "size": min(50, max(14, count))}
        for w, count in sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:20]
    ]

    return {
        "monthly_data": monthly_data,
        "daily_trend": daily_trend,
        "topics": topics,
        "word_cloud": word_cloud,
    }
