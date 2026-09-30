"""
Temporal worker process — registers all workflows and activities.
Run with: python -m app.workflows.worker
"""
from __future__ import annotations

import asyncio

from temporalio.client import Client
from temporalio.worker import Worker

from app.workflows.approval_workflow import (
    ApprovalWorkflow,
    escalate_to_role,
    fetch_chain_levels,
    finalize_approval,
    notify_approver,
    record_decision,
    update_task_level,
)
from app.workflows.rollup_workflow import (
    DailyRollupWorkflow,
    PeriodRollupWorkflow,
    compute_daily_rollup,
    compute_period_rollup,
    gather_approved_entries,
    gather_daily_values,
    persist_rollup,
)
from app.workflows.ingestion_workflow import (
    IngestionWorkflow,
    download_document,
    run_ocr,
    chunk_and_embed,
    index_chunks,
    update_ingestion_status,
)

TASK_QUEUE = "minova-main"


async def main() -> None:
    client = await Client.connect("localhost:7233")

    worker = Worker(
        client,
        task_queue=TASK_QUEUE,
        workflows=[
            ApprovalWorkflow,
            DailyRollupWorkflow,
            PeriodRollupWorkflow,
            IngestionWorkflow,
        ],
        activities=[
            fetch_chain_levels,
            update_task_level,
            record_decision,
            notify_approver,
            escalate_to_role,
            finalize_approval,
            gather_approved_entries,
            compute_daily_rollup,
            persist_rollup,
            gather_daily_values,
            compute_period_rollup,
            download_document,
            run_ocr,
            chunk_and_embed,
            index_chunks,
            update_ingestion_status,
        ],
    )

    print(f"Temporal worker started on queue: {TASK_QUEUE}")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
