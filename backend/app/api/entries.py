from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.schemas import (
    CauseRecordIn,
    CauseRecordOut,
    EntryValueIn,
    Page,
    ShiftEntryCreate,
    ShiftEntryOut,
    ShiftEntryUpdate,
    StatusResponse,
)
from app.core.database import get_db
from app.core.security import CurrentUser
from app.domain.enums import CauseType, EntryStatus, MetricName, ShiftNumber
from app.domain.models import (
    CauseRecord,
    EntryAttachment,
    EntryValue,
    ShiftEntry,
)

router = APIRouter()


def _load_opts():
    return [selectinload(ShiftEntry.values), selectinload(ShiftEntry.cause_records)]


@router.post("", response_model=ShiftEntryOut, status_code=status.HTTP_201_CREATED)
async def create_entry(
    body: ShiftEntryCreate,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    entry = ShiftEntry(
        id=body.id or uuid.uuid4(),
        mine_id=body.mine_id,
        bench_id=body.bench_id,
        shift_date=body.shift_date,
        shift_number=body.shift_number,
        status=EntryStatus.DRAFT,
        submitted_by=None,
        remarks=body.remarks,
    )
    db.add(entry)
    await db.flush()

    for v in body.values:
        db.add(EntryValue(
            shift_entry_id=entry.id,
            metric=v.metric,
            value=v.value,
            unit=v.unit,
        ))

    for c in body.cause_records:
        if not c.description.strip():
            raise HTTPException(400, "Cause record requires a description (evidence)")
        db.add(CauseRecord(
            shift_entry_id=entry.id,
            cause_type=c.cause_type,
            description=c.description,
            hours_lost=c.hours_lost,
            evidence_attachment_id=c.evidence_attachment_id,
        ))

    await db.flush()
    result = await db.execute(
        select(ShiftEntry).where(ShiftEntry.id == entry.id).options(*_load_opts())
    )
    return result.scalar_one()


@router.get("", response_model=Page)
async def list_entries(
    user: CurrentUser,
    mine_id: uuid.UUID | None = None,
    shift_number: ShiftNumber | None = None,
    entry_status: EntryStatus | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    cursor: str | None = None,
    limit: int = Query(default=50, le=200),
    db: AsyncSession = Depends(get_db),
):
    q = select(ShiftEntry).options(*_load_opts())

    if mine_id:
        q = q.where(ShiftEntry.mine_id == mine_id)
    elif user.mine_id:
        q = q.where(ShiftEntry.mine_id == uuid.UUID(user.mine_id))

    if shift_number:
        q = q.where(ShiftEntry.shift_number == shift_number)
    if entry_status:
        q = q.where(ShiftEntry.status == entry_status)
    if date_from:
        q = q.where(ShiftEntry.shift_date >= date_from)
    if date_to:
        q = q.where(ShiftEntry.shift_date <= date_to)
    if cursor:
        q = q.where(ShiftEntry.id > uuid.UUID(cursor))

    q = q.order_by(ShiftEntry.shift_date.desc(), ShiftEntry.id).limit(limit + 1)
    rows = (await db.execute(q)).scalars().all()

    has_more = len(rows) > limit
    items = rows[:limit]
    return Page(
        items=[ShiftEntryOut.model_validate(e) for e in items],
        total=len(items),
        cursor=str(items[-1].id) if items else None,
        has_more=has_more,
    )


@router.get("/{entry_id}", response_model=ShiftEntryOut)
async def get_entry(
    entry_id: uuid.UUID,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ShiftEntry).where(ShiftEntry.id == entry_id).options(*_load_opts())
    )
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(404, "Entry not found")
    return entry


@router.patch("/{entry_id}", response_model=ShiftEntryOut)
async def update_entry(
    entry_id: uuid.UUID,
    body: ShiftEntryUpdate,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ShiftEntry).where(ShiftEntry.id == entry_id).options(*_load_opts())
    )
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(404, "Entry not found")
    if entry.status not in (EntryStatus.DRAFT, EntryStatus.RETURNED):
        raise HTTPException(400, f"Cannot edit entry in status {entry.status}")

    if body.bench_id is not None:
        entry.bench_id = body.bench_id
    if body.remarks is not None:
        entry.remarks = body.remarks

    if body.values is not None:
        for old in entry.values:
            await db.delete(old)
        await db.flush()
        for v in body.values:
            db.add(EntryValue(
                shift_entry_id=entry.id,
                metric=v.metric,
                value=v.value,
                unit=v.unit,
            ))

    if body.cause_records is not None:
        for old in entry.cause_records:
            await db.delete(old)
        await db.flush()
        for c in body.cause_records:
            if not c.description.strip():
                raise HTTPException(400, "Cause record requires a description")
            db.add(CauseRecord(
                shift_entry_id=entry.id,
                cause_type=c.cause_type,
                description=c.description,
                hours_lost=c.hours_lost,
                evidence_attachment_id=c.evidence_attachment_id,
            ))

    entry.updated_at = datetime.now(timezone.utc)
    if entry.status == EntryStatus.RETURNED:
        entry.version += 1

    await db.flush()
    result = await db.execute(
        select(ShiftEntry).where(ShiftEntry.id == entry.id).options(*_load_opts())
    )
    return result.scalar_one()


@router.post("/{entry_id}/submit", response_model=StatusResponse)
async def submit_entry(
    entry_id: uuid.UUID,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(ShiftEntry).where(ShiftEntry.id == entry_id))
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(404, "Entry not found")
    if entry.status not in (EntryStatus.DRAFT, EntryStatus.RETURNED):
        raise HTTPException(400, f"Cannot submit entry in status {entry.status}")

    entry.status = EntryStatus.SUBMITTED
    entry.submitted_at = datetime.now(timezone.utc)
    return StatusResponse(status="submitted", message=f"Entry {entry_id} submitted for review")
