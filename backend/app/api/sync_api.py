from datetime import datetime
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import CurrentUser
from app.domain.models import (
    EntryAttachment, EntryValue, ShiftEntry, SyncBatch,
)
from app.domain.enums import EntryStatus, MetricName, ShiftNumber

router = APIRouter()


class EntryValueIn(BaseModel):
    metric: str
    value: Decimal
    unit: str


class CauseRecordIn(BaseModel):
    cause_type: str
    description: str
    hours_lost: Decimal = Decimal("0")


class ShiftEntryIn(BaseModel):
    id: UUID
    mine_id: UUID
    bench_id: UUID | None = None
    shift_date: datetime
    shift_number: str
    values: list[EntryValueIn] = []
    causes: list[CauseRecordIn] = []
    remarks: str = ""


class SyncPushRequest(BaseModel):
    device_id: str
    idempotency_key: str
    entries: list[ShiftEntryIn]


class SyncPushResponse(BaseModel):
    batch_id: UUID
    accepted: int
    duplicates: int
    errors: list[str]


@router.post("/push")
async def sync_push(
    req: SyncPushRequest,
    user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
) -> SyncPushResponse:
    existing = await db.execute(
        select(SyncBatch).where(SyncBatch.idempotency_key == req.idempotency_key)
    )
    if existing.scalar_one_or_none():
        batch = existing.scalar_one_or_none()
        return SyncPushResponse(
            batch_id=batch.id if batch else UUID(int=0),
            accepted=0,
            duplicates=len(req.entries),
            errors=[],
        )

    batch = SyncBatch(
        device_id=req.device_id,
        idempotency_key=req.idempotency_key,
        entries_count=len(req.entries),
        status="received",
    )
    # user_id would come from the authenticated user
    db.add(batch)
    await db.flush()

    accepted = 0
    errors = []

    for entry_data in req.entries:
        try:
            existing_entry = await db.get(ShiftEntry, entry_data.id)
            if existing_entry and existing_entry.status in (EntryStatus.APPROVED,):
                errors.append(f"Entry {entry_data.id}: already approved, cannot overwrite")
                continue

            if existing_entry:
                existing_entry.remarks = entry_data.remarks
                existing_entry.updated_at = datetime.utcnow()
            else:
                entry = ShiftEntry(
                    id=entry_data.id,
                    mine_id=entry_data.mine_id,
                    bench_id=entry_data.bench_id,
                    shift_date=entry_data.shift_date,
                    shift_number=ShiftNumber(entry_data.shift_number),
                    status=EntryStatus.SYNCED,
                    remarks=entry_data.remarks,
                    sync_batch_id=batch.id,
                )
                db.add(entry)
                await db.flush()

                for val_data in entry_data.values:
                    ev = EntryValue(
                        shift_entry_id=entry.id,
                        metric=MetricName(val_data.metric),
                        value=val_data.value,
                        unit=val_data.unit,
                    )
                    db.add(ev)

            accepted += 1
        except Exception as e:
            errors.append(f"Entry {entry_data.id}: {str(e)}")

    batch.status = "processed"
    batch.processed_at = datetime.utcnow()
    await db.flush()

    return SyncPushResponse(
        batch_id=batch.id,
        accepted=accepted,
        duplicates=len(req.entries) - accepted - len(errors),
        errors=errors,
    )


class DeltaPullResponse(BaseModel):
    entries: list[dict]
    next_cursor: str | None
    has_more: bool


@router.get("/pull")
async def sync_pull(
    mine_id: UUID,
    cursor: str | None = Query(None),
    limit: int = Query(50, le=200),
    user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
) -> DeltaPullResponse:
    stmt = select(ShiftEntry).where(ShiftEntry.mine_id == mine_id)

    if cursor:
        stmt = stmt.where(ShiftEntry.updated_at > datetime.fromisoformat(cursor))

    stmt = stmt.order_by(ShiftEntry.updated_at).limit(limit + 1)
    result = await db.execute(stmt)
    entries = result.scalars().all()

    has_more = len(entries) > limit
    if has_more:
        entries = entries[:limit]

    entry_dicts = []
    for e in entries:
        entry_dicts.append({
            "id": str(e.id),
            "mine_id": str(e.mine_id),
            "bench_id": str(e.bench_id) if e.bench_id else None,
            "shift_date": e.shift_date.isoformat(),
            "shift_number": e.shift_number.value,
            "status": e.status.value,
            "remarks": e.remarks,
            "updated_at": e.updated_at.isoformat(),
        })

    next_cursor = entries[-1].updated_at.isoformat() if entries else None

    return DeltaPullResponse(
        entries=entry_dicts,
        next_cursor=next_cursor,
        has_more=has_more,
    )


@router.post("/presigned-upload")
async def get_presigned_upload(
    filename: str,
    content_type: str = "application/octet-stream",
    user: CurrentUser = None,
):
    from minio import Minio
    from app.core.config import settings

    client = Minio(
        settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=settings.minio_secure,
    )
    import uuid
    object_key = f"uploads/{uuid.uuid4()}/{filename}"
    url = client.presigned_put_object(settings.minio_bucket_attachments, object_key, expires=3600)
    return {"upload_url": url, "object_key": object_key}


@router.get("/form-schemas")
async def get_form_schemas(user: CurrentUser = None):
    return {
        "version": 1,
        "schemas": {
            "production": {
                "fields": [
                    {"name": "production_tonnes", "type": "decimal", "unit": "t", "required": True, "min": 0},
                    {"name": "overburden_m3", "type": "decimal", "unit": "m3", "required": True, "min": 0},
                    {"name": "operating_hours", "type": "decimal", "unit": "h", "required": True, "min": 0, "max": 8},
                    {"name": "downtime_hours", "type": "decimal", "unit": "h", "required": False, "min": 0, "max": 8},
                    {"name": "workers_present", "type": "integer", "required": True, "min": 0},
                ],
            },
            "dispatch": {
                "fields": [
                    {"name": "dispatch_tonnes", "type": "decimal", "unit": "t", "required": True, "min": 0},
                    {"name": "destination", "type": "string", "required": True},
                    {"name": "vehicle_count", "type": "integer", "required": True, "min": 0},
                ],
            },
            "equipment": {
                "fields": [
                    {"name": "equipment_type", "type": "enum", "options": ["dumper", "shovel", "dozer", "drill", "other"], "required": True},
                    {"name": "availability_hours", "type": "decimal", "unit": "h", "required": True},
                    {"name": "breakdown_hours", "type": "decimal", "unit": "h", "required": False},
                    {"name": "maintenance_hours", "type": "decimal", "unit": "h", "required": False},
                ],
            },
            "cause": {
                "fields": [
                    {"name": "cause_type", "type": "enum", "options": ["rain_weather", "equipment_failure", "fire_major_incident", "labour_disruption", "supply", "power_failure", "blasting_delay", "other"], "required": True},
                    {"name": "description", "type": "text", "required": True},
                    {"name": "hours_lost", "type": "decimal", "unit": "h", "required": True, "min": 0},
                ],
            },
        },
    }
