from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import CurrentUser
from app.domain.enums import EvidencePackStatus, PQCategory, PQHouse
from app.domain.models import EvidencePack, Mine, ParliamentaryQuestion, QuestionPattern
from app.services import pq_engine

router = APIRouter()


class QuestionPatternOut(BaseModel):
    id: uuid.UUID
    code: str
    title: str
    category: PQCategory
    trigger_type: str
    historical_frequency_10y: int
    typical_months: list
    sample_questions: list
    likelihood_score: Decimal | None = None
    likelihood_reasons: list[str] | None = None

    model_config = {"from_attributes": True}


class EvidencePackOut(BaseModel):
    id: uuid.UUID
    pattern_id: uuid.UUID
    title: str
    likelihood_score: Decimal
    status: EvidencePackStatus
    summary: str
    sections: dict
    period_start: datetime | None
    period_end: datetime | None
    data_as_of: datetime
    generated_at: datetime

    model_config = {"from_attributes": True}


class ParliamentaryQuestionOut(BaseModel):
    id: uuid.UUID
    house: PQHouse
    question_number: str
    asked_on: datetime
    member_name: str
    subject: str
    question_text: str
    category: PQCategory
    days_to_answer: int | None

    model_config = {"from_attributes": True}


class GeneratePacksRequest(BaseModel):
    limit: int = 5


@router.get("/patterns", response_model=list[QuestionPatternOut])
async def list_patterns(
    user: CurrentUser,
    category: PQCategory | None = None,
    db: AsyncSession = Depends(get_db),
):
    """All known question patterns with computed likelihood (ranked)."""
    q = select(QuestionPattern)
    if category:
        q = q.where(QuestionPattern.category == category)
    patterns = (await db.execute(q)).scalars().all()
    now = datetime.now(timezone.utc)

    scored = []
    for p in patterns:
        lik = await pq_engine.compute_pattern_likelihood(db, p, now)
        out = QuestionPatternOut.model_validate(p)
        out.likelihood_score = lik["score"]
        out.likelihood_reasons = lik["reasons"]
        scored.append(out)
    scored.sort(key=lambda x: -(x.likelihood_score or 0))
    return scored


@router.post("/packs/generate", response_model=list[EvidencePackOut])
async def generate_packs(
    body: GeneratePacksRequest,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """Pre-generate evidence packs for the most likely questions BEFORE parliament asks."""
    now = datetime.now(timezone.utc)
    patterns = (await db.execute(select(QuestionPattern))).scalars().all()

    ranked = []
    for p in patterns:
        lik = await pq_engine.compute_pattern_likelihood(db, p, now)
        ranked.append((lik["score"], p, lik))
    ranked.sort(key=lambda t: -t[0])
    top = ranked[: max(1, min(body.limit, 20))]

    created = []
    for score, pattern, lik in top:
        pack_data = await pq_engine.generate_evidence_pack(db, pattern, lik, now)
        pack = EvidencePack(
            pattern_id=pattern.id,
            title=pack_data["title"],
            likelihood_score=pack_data["likelihood_score"],
            status=pack_data["status"],
            period_start=pack_data["period_start"],
            period_end=pack_data["period_end"],
            summary=pack_data["summary"],
            sections=pack_data["sections"],
            data_as_of=pack_data["data_as_of"],
            generated_at=now,
        )
        db.add(pack)
        created.append(pack)
    await db.flush()
    return created


@router.get("/packs", response_model=list[EvidencePackOut])
async def list_packs(
    user: CurrentUser,
    status: EvidencePackStatus | None = None,
    limit: int = Query(default=20, le=100),
    db: AsyncSession = Depends(get_db),
):
    q = select(EvidencePack).order_by(EvidencePack.likelihood_score.desc()).limit(limit)
    if status:
        q = q.where(EvidencePack.status == status)
    packs = (await db.execute(q)).scalars().all()
    return [EvidencePackOut.model_validate(p) for p in packs]


@router.get("/packs/{pack_id}", response_model=EvidencePackOut)
async def get_pack(pack_id: uuid.UUID, user: CurrentUser, db: AsyncSession = Depends(get_db)):
    pack = await db.get(EvidencePack, pack_id)
    if pack is None:
        raise HTTPException(404, "Evidence pack not found")
    return pack


@router.get("/questions", response_model=list[ParliamentaryQuestionOut])
async def list_questions(
    user: CurrentUser,
    category: PQCategory | None = None,
    house: PQHouse | None = None,
    limit: int = Query(default=50, le=200),
    db: AsyncSession = Depends(get_db),
):
    """Historical parliamentary questions (pattern corpus)."""
    q = select(ParliamentaryQuestion).order_by(ParliamentaryQuestion.asked_on.desc()).limit(limit)
    if category:
        q = q.where(ParliamentaryQuestion.category == category)
    if house:
        q = q.where(ParliamentaryQuestion.house == house)
    rows = (await db.execute(q)).scalars().all()
    return [ParliamentaryQuestionOut.model_validate(r) for r in rows]
