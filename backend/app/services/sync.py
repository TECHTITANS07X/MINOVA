from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

import structlog

logger = structlog.get_logger()


@dataclass
class SyncBatchInput:
    mine_id: str
    device_id: str
    entries: list[dict]
    client_timestamp: str


@dataclass
class SyncResult:
    accepted: int
    rejected: int
    conflicts: list[dict] = field(default_factory=list)
    server_timestamp: str = ""


@dataclass
class DeltaPackage:
    entries: list[dict]
    targets: list[dict]
    templates: list[dict]
    cursor: str
    has_more: bool = False


@dataclass
class ConflictResult:
    has_conflict: bool
    field_name: str = ""
    local_value: str = ""
    remote_value: str = ""


def process_push_batch(batch: SyncBatchInput, existing_entries: dict[str, dict]) -> SyncResult:
    accepted = 0
    rejected = 0
    conflicts = []
    now = datetime.now(timezone.utc).isoformat()

    for entry in batch.entries:
        entry_id = entry.get("id", "")
        if not entry_id:
            rejected += 1
            continue

        if entry_id in existing_entries:
            existing = existing_entries[entry_id]
            conflict = detect_conflict(entry, existing)
            if conflict.has_conflict:
                conflicts.append({
                    "entry_id": entry_id,
                    "field": conflict.field_name,
                    "local": conflict.local_value,
                    "remote": conflict.remote_value,
                    "resolution": "unresolved",
                })
                rejected += 1
                continue

            if entry.get("updated_at", "") <= existing.get("updated_at", ""):
                rejected += 1
                continue

        accepted += 1

    return SyncResult(accepted=accepted, rejected=rejected, conflicts=conflicts, server_timestamp=now)


def detect_conflict(local: dict, remote: dict) -> ConflictResult:
    check_fields = ["production_tonnes", "ob_volume_m3", "operating_hours", "workers_present"]
    for f in check_fields:
        local_val = str(local.get(f, ""))
        remote_val = str(remote.get(f, ""))
        if local_val and remote_val and local_val != remote_val:
            return ConflictResult(has_conflict=True, field_name=f, local_value=local_val, remote_value=remote_val)
    return ConflictResult(has_conflict=False)


def generate_delta(
    entries: list[dict],
    targets: list[dict],
    templates: list[dict],
    cursor: str | None,
    limit: int = 100,
) -> DeltaPackage:
    if cursor:
        entries = [e for e in entries if e.get("updated_at", "") > cursor]
        targets = [t for t in targets if t.get("updated_at", "") > cursor]

    now = datetime.now(timezone.utc).isoformat()
    has_more = len(entries) > limit

    return DeltaPackage(
        entries=entries[:limit],
        targets=targets,
        templates=templates,
        cursor=now,
        has_more=has_more,
    )
