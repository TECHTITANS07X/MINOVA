"""
Temporal workflow for multi-level approval chains.
Each level waits for human decision with SLA timeout and auto-escalation.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import timedelta

from temporalio import activity, workflow

with workflow.unsafe.imports_passed_through():
    from sqlalchemy import select, update
    from app.core.database import async_session_factory
    from app.domain.enums import ApprovalAction
    from app.domain.models import ApprovalChain, ApprovalLevel, ApprovalTask, AuditEvent


@dataclass
class ApprovalRequest:
    task_id: str
    chain_id: str
    entity_type: str
    entity_id: str


@dataclass
class ApprovalDecision:
    action: str  # approve, return, escalate
    actor_id: str
    comment: str


@dataclass
class LevelSpec:
    sequence: int
    role_name: str
    sla_hours: int
    escalation_role: str | None
    can_skip: bool


@activity.defn
async def fetch_chain_levels(chain_id: str) -> list[dict]:
    async with async_session_factory() as db:
        result = await db.execute(
            select(ApprovalLevel)
            .where(ApprovalLevel.chain_id == uuid.UUID(chain_id))
            .order_by(ApprovalLevel.sequence)
        )
        levels = result.scalars().all()
        return [
            {
                "sequence": lv.sequence,
                "role_name": lv.role_name,
                "sla_hours": lv.sla_hours,
                "escalation_role": lv.escalation_role,
                "can_skip": lv.can_skip,
            }
            for lv in levels
        ]


@activity.defn
async def update_task_level(task_id: str, level: int) -> None:
    async with async_session_factory() as db:
        await db.execute(
            update(ApprovalTask)
            .where(ApprovalTask.id == uuid.UUID(task_id))
            .values(current_level=level)
        )
        await db.commit()


@activity.defn
async def record_decision(task_id: str, action: str, actor_id: str, comment: str) -> None:
    from datetime import datetime, timezone

    async with async_session_factory() as db:
        task = await db.get(ApprovalTask, uuid.UUID(task_id))
        if task:
            task.action = ApprovalAction[action.upper()]
            task.acted_by = uuid.UUID(actor_id)
            task.comment = comment
            task.completed_at = datetime.now(timezone.utc)
            await db.commit()


@activity.defn
async def notify_approver(role_name: str, entity_type: str, entity_id: str) -> None:
    pass


@activity.defn
async def escalate_to_role(escalation_role: str, task_id: str) -> None:
    pass


@activity.defn
async def finalize_approval(task_id: str, entity_type: str, entity_id: str, approved: bool) -> None:
    from datetime import datetime, timezone

    async with async_session_factory() as db:
        if entity_type == "ShiftEntry":
            from app.domain.models import ShiftEntry
            from app.domain.enums import EntryStatus
            entry = await db.get(ShiftEntry, uuid.UUID(entity_id))
            if entry:
                entry.status = EntryStatus.APPROVED if approved else EntryStatus.RETURNED
                entry.updated_at = datetime.now(timezone.utc)
        await db.commit()


@workflow.defn
class ApprovalWorkflow:
    def __init__(self) -> None:
        self._decision: ApprovalDecision | None = None

    @workflow.signal
    async def submit_decision(self, decision: ApprovalDecision) -> None:
        self._decision = decision

    @workflow.query
    def current_state(self) -> dict:
        return {"decision": self._decision}

    @workflow.run
    async def run(self, request: ApprovalRequest) -> dict:
        levels = await workflow.execute_activity(
            fetch_chain_levels,
            request.chain_id,
            start_to_close_timeout=timedelta(seconds=30),
        )

        if not levels:
            return {"status": "error", "reason": "no_levels_configured"}

        for level in levels:
            await workflow.execute_activity(
                update_task_level,
                args=[request.task_id, level["sequence"]],
                start_to_close_timeout=timedelta(seconds=30),
            )

            await workflow.execute_activity(
                notify_approver,
                args=[level["role_name"], request.entity_type, request.entity_id],
                start_to_close_timeout=timedelta(seconds=30),
            )

            self._decision = None
            sla_hours = level["sla_hours"] or 24

            try:
                await workflow.wait_condition(
                    lambda: self._decision is not None,
                    timeout=timedelta(hours=sla_hours),
                )
            except TimeoutError:
                if level["escalation_role"]:
                    await workflow.execute_activity(
                        escalate_to_role,
                        args=[level["escalation_role"], request.task_id],
                        start_to_close_timeout=timedelta(seconds=30),
                    )
                    try:
                        await workflow.wait_condition(
                            lambda: self._decision is not None,
                            timeout=timedelta(hours=sla_hours),
                        )
                    except TimeoutError:
                        return {"status": "sla_breached", "level": level["sequence"]}
                else:
                    return {"status": "sla_breached", "level": level["sequence"]}

            decision = self._decision
            assert decision is not None

            await workflow.execute_activity(
                record_decision,
                args=[request.task_id, decision.action, decision.actor_id, decision.comment],
                start_to_close_timeout=timedelta(seconds=30),
            )

            if decision.action == "return":
                await workflow.execute_activity(
                    finalize_approval,
                    args=[request.task_id, request.entity_type, request.entity_id, False],
                    start_to_close_timeout=timedelta(seconds=30),
                )
                return {"status": "returned", "level": level["sequence"], "comment": decision.comment}

        await workflow.execute_activity(
            finalize_approval,
            args=[request.task_id, request.entity_type, request.entity_id, True],
            start_to_close_timeout=timedelta(seconds=30),
        )
        return {"status": "approved"}
