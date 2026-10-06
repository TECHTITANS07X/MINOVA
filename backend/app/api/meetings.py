from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import CurrentUser
from app.domain.enums import MeetingActionStatus, MeetingType
from app.domain.models import MeetingAction

router = APIRouter()


class ActionCreate(BaseModel):
    mine_id: uuid.UUID
    meeting_type: MeetingType
    meeting_date: datetime
    title: str
    description: str = ""
    assigned_to: str
    assigned_role: str = ""
    due_date: datetime


class ActionUpdate(BaseModel):
    status: MeetingActionStatus | None = None
    completion_notes: str | None = None
    completed_at: datetime | None = None


class ActionOut(BaseModel):
    id: uuid.UUID
    mine_id: uuid.UUID
    meeting_type: MeetingType
    meeting_date: datetime
    title: str
    description: str
    assigned_to: str
    assigned_role: str
    due_date: datetime
    status: MeetingActionStatus
    completion_notes: str
    completed_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


@router.get("/actions", response_model=list[ActionOut])
async def list_actions(
    mine_id: uuid.UUID | None = None,
    status: MeetingActionStatus | None = None,
    user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
):
    q = select(MeetingAction).order_by(MeetingAction.due_date)
    if mine_id:
        q = q.where(MeetingAction.mine_id == mine_id)
    if status:
        q = q.where(MeetingAction.status == status)
    rows = (await db.execute(q)).scalars().all()
    return [ActionOut.model_validate(r) for r in rows]


@router.post("/actions", response_model=ActionOut, status_code=201)
async def create_action(
    body: ActionCreate,
    user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
):
    action = MeetingAction(**body.model_dump())
    db.add(action)
    await db.flush()
    return ActionOut.model_validate(action)


@router.patch("/actions/{action_id}", response_model=ActionOut)
async def update_action(
    action_id: uuid.UUID,
    body: ActionUpdate,
    user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(MeetingAction).where(MeetingAction.id == action_id))
    action = result.scalar_one_or_none()
    if not action:
        raise HTTPException(404, "Action not found")
    if body.status is not None:
        action.status = body.status
    if body.completion_notes is not None:
        action.completion_notes = body.completion_notes
    if body.completed_at is not None:
        action.completed_at = body.completed_at
    await db.flush()
    return ActionOut.model_validate(action)


@router.get("/actions/summary")
async def action_summary(
    mine_id: uuid.UUID | None = None,
    user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
):
    q = select(MeetingAction.status, func.count()).group_by(MeetingAction.status)
    if mine_id:
        q = q.where(MeetingAction.mine_id == mine_id)
    rows = (await db.execute(q)).all()
    return {row[0].value: row[1] for row in rows}
