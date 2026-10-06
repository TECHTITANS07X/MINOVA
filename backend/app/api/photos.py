from __future__ import annotations

import math
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import CurrentUser
from app.domain.enums import PhotoVerificationStatus
from app.domain.models import Mine, PhotoEvidence

router = APIRouter()


class VerificationOut(BaseModel):
    id: uuid.UUID
    mine_id: uuid.UUID
    bench_id: uuid.UUID | None
    filename: str
    object_key: str
    photo_latitude: Decimal | None
    photo_longitude: Decimal | None
    photo_timestamp: datetime | None
    expected_latitude: Decimal | None
    expected_longitude: Decimal | None
    distance_m: Decimal | None
    verification_status: PhotoVerificationStatus
    verification_notes: str
    context: str
    created_at: datetime

    model_config = {"from_attributes": True}


class VerifyRequest(BaseModel):
    status: PhotoVerificationStatus
    notes: str = ""


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6_371_000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _extract_exif_gps(data: bytes) -> tuple[float | None, float | None, datetime | None]:
    try:
        from PIL import Image
        from PIL.ExifTags import TAGS, GPSTAGS
        import io

        img = Image.open(io.BytesIO(data))
        exif = img._getexif()
        if not exif:
            return None, None, None

        gps_info = {}
        timestamp = None
        for tag_id, value in exif.items():
            tag = TAGS.get(tag_id, tag_id)
            if tag == "GPSInfo":
                for gps_tag_id, gps_value in value.items():
                    gps_tag = GPSTAGS.get(gps_tag_id, gps_tag_id)
                    gps_info[gps_tag] = gps_value
            elif tag == "DateTimeOriginal":
                try:
                    timestamp = datetime.strptime(value, "%Y:%m:%d %H:%M:%S").replace(tzinfo=timezone.utc)
                except (ValueError, TypeError):
                    pass

        lat = lon = None
        if "GPSLatitude" in gps_info and "GPSLatitudeRef" in gps_info:
            d, m, s = gps_info["GPSLatitude"]
            lat = float(d) + float(m) / 60 + float(s) / 3600
            if gps_info["GPSLatitudeRef"] == "S":
                lat = -lat
        if "GPSLongitude" in gps_info and "GPSLongitudeRef" in gps_info:
            d, m, s = gps_info["GPSLongitude"]
            lon = float(d) + float(m) / 60 + float(s) / 3600
            if gps_info["GPSLongitudeRef"] == "W":
                lon = -lon

        return lat, lon, timestamp
    except Exception:
        return None, None, None


@router.get("/verifications", response_model=list[VerificationOut])
async def list_verifications(
    mine_id: uuid.UUID | None = None,
    status: PhotoVerificationStatus | None = None,
    user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
):
    q = select(PhotoEvidence).order_by(PhotoEvidence.created_at.desc())
    if mine_id:
        q = q.where(PhotoEvidence.mine_id == mine_id)
    if status:
        q = q.where(PhotoEvidence.verification_status == status)
    rows = (await db.execute(q)).scalars().all()
    return [VerificationOut.model_validate(r) for r in rows]


@router.post("/upload", response_model=VerificationOut, status_code=201)
async def upload_photo(
    mine_id: uuid.UUID = Form(...),
    bench_id: uuid.UUID | None = Form(None),
    context: str = Form(""),
    file: UploadFile = File(...),
    user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
):
    mine_result = await db.execute(select(Mine).where(Mine.id == mine_id))
    mine = mine_result.scalar_one_or_none()
    if not mine:
        raise HTTPException(404, "Mine not found")

    data = await file.read()
    photo_lat, photo_lon, photo_ts = _extract_exif_gps(data)

    object_key = f"photos/{mine_id}/{uuid.uuid4()}/{file.filename}"

    expected_lat = float(mine.latitude) if mine.latitude else None
    expected_lon = float(mine.longitude) if mine.longitude else None

    distance = None
    if photo_lat is not None and photo_lon is not None and expected_lat is not None and expected_lon is not None:
        distance = Decimal(str(round(_haversine_m(photo_lat, photo_lon, expected_lat, expected_lon), 2)))

    record = PhotoEvidence(
        mine_id=mine_id,
        bench_id=bench_id,
        filename=file.filename or "unknown",
        object_key=object_key,
        photo_latitude=Decimal(str(round(photo_lat, 6))) if photo_lat is not None else None,
        photo_longitude=Decimal(str(round(photo_lon, 6))) if photo_lon is not None else None,
        photo_timestamp=photo_ts,
        expected_latitude=Decimal(str(expected_lat)) if expected_lat is not None else None,
        expected_longitude=Decimal(str(expected_lon)) if expected_lon is not None else None,
        distance_m=distance,
        context=context,
    )
    db.add(record)
    await db.flush()
    return VerificationOut.model_validate(record)


@router.post("/verifications/{verification_id}/verify")
async def verify_photo(
    verification_id: uuid.UUID,
    body: VerifyRequest,
    user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(PhotoEvidence).where(PhotoEvidence.id == verification_id))
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(404, "Photo evidence record not found")
    record.verification_status = body.status
    record.verification_notes = body.notes
    await db.flush()
    return {
        "id": str(record.id),
        "verification_status": record.verification_status.value,
        "verification_notes": record.verification_notes,
    }
