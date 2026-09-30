from datetime import datetime
from decimal import Decimal
from uuid import UUID
import hashlib

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import CurrentUser, require_role
from app.domain.models import (
    AppUser, ApprovalChain, ApprovalLevel, AuditEvent, Bench, Mine, OrgUnit, Role, Target,
    ReportTemplate, ReportTemplateVersion,
)
from app.domain.enums import ApprovalRuleType, OrgUnitType, TargetPeriod

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
