from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import ApprovalActionRequest, ApprovalCommentRequest, ApprovalTaskOut, Page, StatusResponse
from app.core.database import get_db
from app.core.security import CurrentUser
from app.domain.enums import ApprovalAction, AuditAction, EntryStatus
from app.domain.models import ApprovalChain, ApprovalLevel, ApprovalTask, AuditEvent, ShiftEntry

router = APIRouter()


async def _append_audit(
    db: AsyncSession,
    action: AuditAction,
    entity_type: str,
    entity_id: str,
    user_id: uuid.UUID | None,
    details: dict,
):
    last = (
        await db.execute(
            select(AuditEvent).order_by(AuditEvent.created_at.desc()).limit(1)
        )
    ).scalar_one_or_none()
    prev_hash = last.current_hash if last else ""
    payload = json.dumps(
        {"prev": prev_hash, "action": action.value, "entity": entity_type, "eid": entity_id, **details},
        sort_keys=True,
    )
    cur_hash = hashlib.sha256(payload.encode()).hexdigest()
    db.add(AuditEvent(
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        user_id=user_id,
        details=details,
        previous_hash=prev_hash,
        current_hash=cur_hash,
    ))


@router.get("/inbox", response_model=Page)
async def approval_inbox(
    user: CurrentUser,
    entity_type: str | None = None,
    cursor: str | None = None,
    limit: int = Query(default=50, le=200),
    db: AsyncSession = Depends(get_db),
):
    q = select(ApprovalTask).where(ApprovalTask.completed_at.is_(None))
    if entity_type:
        q = q.where(ApprovalTask.entity_type == entity_type)

    user_roles = set(user.roles)
    chain_ids_q = (
        select(ApprovalLevel.chain_id)
        .where(ApprovalLevel.role_name.in_(user_roles))
    )
    chain_ids = (await db.execute(chain_ids_q)).scalars().all()
    if chain_ids:
        q = q.where(ApprovalTask.chain_id.in_(chain_ids))

    if cursor:
        q = q.where(ApprovalTask.id > uuid.UUID(cursor))
    q = q.order_by(ApprovalTask.created_at.desc()).limit(limit + 1)

    rows = (await db.execute(q)).scalars().all()
    has_more = len(rows) > limit
    items = rows[:limit]
    return Page(
        items=[ApprovalTaskOut.model_validate(t) for t in items],
        total=len(items),
        cursor=str(items[-1].id) if items else None,
        has_more=has_more,
    )


@router.post("/{task_id}/act", response_model=StatusResponse)
async def act_on_task(
    task_id: uuid.UUID,
    body: ApprovalActionRequest,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(ApprovalTask).where(ApprovalTask.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(404, "Approval task not found")
    if task.completed_at:
        raise HTTPException(400, "Task already completed")

    chain_result = await db.execute(
        select(ApprovalLevel).where(
            ApprovalLevel.chain_id == task.chain_id,
            ApprovalLevel.sequence == task.current_level,
        )
    )
    level = chain_result.scalar_one_or_none()
    if level and level.role_name not in user.roles:
        raise HTTPException(403, f"Requires role {level.role_name}")

    now = datetime.now(timezone.utc)

    if body.action == ApprovalAction.APPROVE:
        next_level_q = await db.execute(
            select(ApprovalLevel).where(
                ApprovalLevel.chain_id == task.chain_id,
                ApprovalLevel.sequence > task.current_level,
            ).order_by(ApprovalLevel.sequence).limit(1)
        )
        next_level = next_level_q.scalar_one_or_none()

        if next_level:
            task.current_level = next_level.sequence
            task.action = None
            task.comment = ""
            await _append_audit(db, AuditAction.APPROVE, task.entity_type, str(task.entity_id), None, {
                "level": task.current_level - 1, "comment": body.comment,
            })
            return StatusResponse(status="advanced", message=f"Advanced to level {next_level.sequence}")
        else:
            task.action = ApprovalAction.APPROVE
            task.acted_by = None
            task.comment = body.comment
            task.completed_at = now

            if task.entity_type == "shift_entry":
                entry_r = await db.execute(select(ShiftEntry).where(ShiftEntry.id == task.entity_id))
                entry = entry_r.scalar_one_or_none()
                if entry:
                    entry.status = EntryStatus.APPROVED

            await _append_audit(db, AuditAction.APPROVE, task.entity_type, str(task.entity_id), None, {
                "final": True, "comment": body.comment,
            })
            return StatusResponse(status="approved", message="Fully approved")

    elif body.action == ApprovalAction.RETURN:
        if not body.comment.strip():
            raise HTTPException(400, "Return requires a comment")
        task.action = ApprovalAction.RETURN
        task.comment = body.comment
        task.completed_at = now

        if task.entity_type == "shift_entry":
            entry_r = await db.execute(select(ShiftEntry).where(ShiftEntry.id == task.entity_id))
            entry = entry_r.scalar_one_or_none()
            if entry:
                entry.status = EntryStatus.RETURNED

        await _append_audit(db, AuditAction.RETURN, task.entity_type, str(task.entity_id), None, {
            "comment": body.comment,
        })
        return StatusResponse(status="returned", message="Entry returned for revision")

    elif body.action == ApprovalAction.ESCALATE:
        if level and level.escalation_role:
            task.current_level += 1
            await _append_audit(db, AuditAction.ESCALATE, task.entity_type, str(task.entity_id), None, {
                "escalated_to": level.escalation_role, "comment": body.comment,
            })
            return StatusResponse(status="escalated", message=f"Escalated to {level.escalation_role}")
        raise HTTPException(400, "No escalation target configured for this level")

    raise HTTPException(400, f"Unsupported action: {body.action}")


async def _act_on_task_impl(
    task_id: uuid.UUID,
    action: str,
    user: CurrentUser,
    db: AsyncSession,
    comment: str = "",
) -> StatusResponse:
    """Shared implementation for /act and the convenience per-action routes."""
    return await act_on_task(
        task_id,
        ApprovalActionRequest(action=action, comment=comment),
        user,
        db,
    )


@router.post("/{task_id}/approve", response_model=StatusResponse)
async def approve_task(
    task_id: uuid.UUID,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    body: ApprovalCommentRequest | None = None,
):
    return await _act_on_task_impl(task_id, "approve", user, db, body.comment if body else "")


@router.post("/{task_id}/return", response_model=StatusResponse)
async def return_task(
    task_id: uuid.UUID,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    body: ApprovalCommentRequest | None = None,
):
    return await _act_on_task_impl(task_id, "return", user, db, body.comment if body else "")


@router.post("/{task_id}/escalate", response_model=StatusResponse)
async def escalate_task(
    task_id: uuid.UUID,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    body: ApprovalCommentRequest | None = None,
):
    return await _act_on_task_impl(task_id, "escalate", user, db, body.comment if body else "")


@router.get("/history/{entity_type}/{entity_id}", response_model=list[ApprovalTaskOut])
async def approval_history(
    entity_type: str,
    entity_id: uuid.UUID,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ApprovalTask)
        .where(ApprovalTask.entity_type == entity_type, ApprovalTask.entity_id == entity_id)
        .order_by(ApprovalTask.created_at)
    )
    return result.scalars().all()
