from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.domain.enums import (
    AnomalyStatus,
    ApprovalAction,
    ApprovalRuleType,
    CauseType,
    ConflictResolution,
    DocumentCategory,
    DocumentType,
    EntryStatus,
    IngestionStatus,
    MetricName,
    OrgUnitType,
    QueryRouteType,
    RecoveryPlanStatus,
    ReportPeriod,
    ReportStatus,
    ShiftNumber,
    StagingReviewStatus,
    TargetPeriod,
)


# ── Generic ──────────────────────────────────────────────────────────────────

class Page(BaseModel):
    items: list = []
    total: int = 0
    cursor: str | None = None
    has_more: bool = False


class IdResponse(BaseModel):
    id: uuid.UUID


class StatusResponse(BaseModel):
    status: str
    message: str = ""


# ── Shift Entries ────────────────────────────────────────────────────────────

class EntryValueIn(BaseModel):
    metric: MetricName
    value: Decimal
    unit: str = "t"


class CauseRecordIn(BaseModel):
    cause_type: CauseType
    description: str
    hours_lost: Decimal = Decimal("0")
    evidence_attachment_id: uuid.UUID | None = None


class ShiftEntryCreate(BaseModel):
    id: uuid.UUID | None = None
    mine_id: uuid.UUID
    bench_id: uuid.UUID | None = None
    shift_date: datetime
    shift_number: ShiftNumber
    remarks: str = ""
    values: list[EntryValueIn] = []
    cause_records: list[CauseRecordIn] = []


class ShiftEntryUpdate(BaseModel):
    bench_id: uuid.UUID | None = None
    remarks: str | None = None
    values: list[EntryValueIn] | None = None
    cause_records: list[CauseRecordIn] | None = None


class EntryValueOut(BaseModel):
    id: uuid.UUID
    metric: MetricName
    value: Decimal
    unit: str
    model_config = {"from_attributes": True}


class CauseRecordOut(BaseModel):
    id: uuid.UUID
    cause_type: CauseType
    description: str
    hours_lost: Decimal
    evidence_attachment_id: uuid.UUID | None
    model_config = {"from_attributes": True}


class ShiftEntryOut(BaseModel):
    id: uuid.UUID
    mine_id: uuid.UUID
    bench_id: uuid.UUID | None
    shift_date: datetime
    shift_number: ShiftNumber
    status: EntryStatus
    submitted_by: uuid.UUID | None
    submitted_at: datetime | None
    version: int
    remarks: str
    created_at: datetime
    values: list[EntryValueOut] = []
    cause_records: list[CauseRecordOut] = []
    model_config = {"from_attributes": True}


# ── Reports ──────────────────────────────────────────────────────────────────

class ReportGenerateRequest(BaseModel):
    mine_id: uuid.UUID
    template_id: uuid.UUID | None = None
    period: ReportPeriod
    period_start: datetime
    period_end: datetime


class ReportValueOut(BaseModel):
    id: uuid.UUID
    metric: str
    value: Decimal
    unit: str
    section: str
    row_key: str
    model_config = {"from_attributes": True}


class ReportOut(BaseModel):
    id: uuid.UUID
    mine_id: uuid.UUID
    template_id: uuid.UUID
    period: ReportPeriod
    period_start: datetime
    period_end: datetime
    status: ReportStatus
    generated_description: str
    edited_description: str | None
    created_at: datetime
    finalized_at: datetime | None
    values: list[ReportValueOut] = []
    model_config = {"from_attributes": True}


class ReportDescriptionEdit(BaseModel):
    edited_description: str


# ── Approval ─────────────────────────────────────────────────────────────────

class ApprovalActionRequest(BaseModel):
    action: ApprovalAction
    comment: str = ""


class ApprovalCommentRequest(BaseModel):
    """Body for the per-action convenience routes (/approve, /return, /escalate)
    where the action is already encoded in the URL path."""
    comment: str = ""


class ApprovalTaskOut(BaseModel):
    id: uuid.UUID
    entity_type: str
    entity_id: uuid.UUID
    chain_id: uuid.UUID
    current_level: int
    action: ApprovalAction | None
    acted_by: uuid.UUID | None
    comment: str
    temporal_workflow_id: str | None
    sla_deadline: datetime | None
    created_at: datetime
    completed_at: datetime | None
    model_config = {"from_attributes": True}


# ── Conflicts ────────────────────────────────────────────────────────────────

class ConflictResolveRequest(BaseModel):
    resolution: ConflictResolution
    resolved_value: Decimal | None = None
    reason: str


class ConflictOut(BaseModel):
    id: uuid.UUID
    entity_type: str
    entity_id: uuid.UUID
    metric: str
    value_a: Decimal
    source_a: str
    value_b: Decimal
    source_b: str
    tolerance_pct: Decimal
    resolution: ConflictResolution
    resolved_value: Decimal | None
    resolved_by: uuid.UUID | None
    resolution_reason: str
    created_at: datetime
    resolved_at: datetime | None
    model_config = {"from_attributes": True}


# ── Lineage ──────────────────────────────────────────────────────────────────

class ExtractedFigure(BaseModel):
    metric: str
    value: Decimal
    unit: str
    source_page: int
    source_snippet: str


class DocumentReportResponse(BaseModel):
    document_id: uuid.UUID
    document_filename: str
    pages_parsed: int
    extracted: list[ExtractedFigure]
    report_id: uuid.UUID
    report_status: str
    period_start: datetime
    period_end: datetime
    report_values: list[ReportValueOut]
    primary_value_id: uuid.UUID | None = None


class LineageNode(BaseModel):
    source_type: str
    source_id: uuid.UUID
    relationship_type: str
    value: Decimal | None = None
    unit: str = ""
    label: str = ""
    children: list[LineageNode] = []


class ReplayResult(BaseModel):
    report_value_id: uuid.UUID
    stored_value: Decimal
    recomputed_value: Decimal
    match: bool
    lineage_tree: LineageNode | None = None


# ── Documents ────────────────────────────────────────────────────────────────

class DocumentUploadRequest(BaseModel):
    filename: str
    doc_type: DocumentType
    category: DocumentCategory
    mine_id: uuid.UUID | None = None
    content_type: str = "application/pdf"
    size_bytes: int = 0


class PresignedUrlResponse(BaseModel):
    upload_url: str
    object_key: str
    document_id: uuid.UUID


class DocumentOut(BaseModel):
    id: uuid.UUID
    filename: str
    doc_type: DocumentType
    category: DocumentCategory
    mine_id: uuid.UUID | None
    ingestion_status: IngestionStatus
    size_bytes: int
    created_at: datetime
    model_config = {"from_attributes": True}


class SearchRequest(BaseModel):
    query: str
    mine_id: uuid.UUID | None = None
    category: DocumentCategory | None = None
    limit: int = 10


class SearchHit(BaseModel):
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    filename: str
    page_number: int | None
    text: str
    score: float
    bbox: dict | None = None


class StagingReviewRequest(BaseModel):
    status: StagingReviewStatus
    accepted_value: Decimal | None = None


class ExtractedValueOut(BaseModel):
    id: uuid.UUID
    document_id: uuid.UUID
    metric: str
    value: Decimal
    unit: str
    confidence: Decimal
    source_page: int | None
    review_status: StagingReviewStatus
    accepted_value: Decimal | None
    model_config = {"from_attributes": True}


# ── Chat / RAG ───────────────────────────────────────────────────────────────

class ChatSessionCreate(BaseModel):
    title: str = ""


class ChatMessageIn(BaseModel):
    content: str


class ChatSessionOut(BaseModel):
    id: uuid.UUID
    title: str
    created_at: datetime
    model_config = {"from_attributes": True}


class ChatMessageOut(BaseModel):
    id: uuid.UUID
    role: str
    content: str
    route_type: QueryRouteType | None
    citations: dict | None
    created_at: datetime
    model_config = {"from_attributes": True}


# ── Anomalies ────────────────────────────────────────────────────────────────

class AnomalyReviewRequest(BaseModel):
    status: AnomalyStatus
    reason: str = ""
    linked_cause_id: uuid.UUID | None = None


class AnomalyOut(BaseModel):
    id: uuid.UUID
    mine_id: uuid.UUID
    bench_id: uuid.UUID | None
    flag_date: datetime
    metric: str
    expected_value: Decimal
    actual_value: Decimal
    anomaly_score: Decimal
    contributing_features: dict
    explanation: str
    status: AnomalyStatus
    reviewed_by: uuid.UUID | None
    review_reason: str
    linked_cause_id: uuid.UUID | None
    created_at: datetime
    model_config = {"from_attributes": True}


# ── Weather ──────────────────────────────────────────────────────────────────

class WeatherOut(BaseModel):
    id: uuid.UUID
    mine_id: uuid.UUID
    observation_date: datetime
    temperature_max: Decimal | None
    temperature_min: Decimal | None
    precipitation_mm: Decimal
    wind_speed_kmh: Decimal | None
    humidity_pct: Decimal | None
    model_config = {"from_attributes": True}


class ForecastOut(BaseModel):
    id: uuid.UUID
    mine_id: uuid.UUID
    forecast_date: datetime
    precipitation_mm: Decimal
    temperature_max: Decimal | None
    weather_code: int | None
    model_config = {"from_attributes": True}


class RecoveryPlanOut(BaseModel):
    id: uuid.UUID
    mine_id: uuid.UUID
    period_start: datetime
    period_end: datetime
    gap_tonnes: Decimal
    proposed_daily_targets: dict
    rationale: str
    status: RecoveryPlanStatus
    decided_by: uuid.UUID | None
    decision_reason: str
    created_at: datetime
    decided_at: datetime | None
    model_config = {"from_attributes": True}


class RecoveryPlanDecision(BaseModel):
    status: RecoveryPlanStatus
    reason: str


# ── Admin ────────────────────────────────────────────────────────────────────

class MineCreate(BaseModel):
    org_unit_id: uuid.UUID
    name: str
    code: str
    latitude: Decimal | None = None
    longitude: Decimal | None = None
    timezone: str = "Asia/Kolkata"
    shift_count: int = 3


class MineOut(BaseModel):
    id: uuid.UUID
    org_unit_id: uuid.UUID
    name: str
    code: str
    latitude: Decimal | None
    longitude: Decimal | None
    timezone: str
    shift_count: int
    is_active: bool
    created_at: datetime
    model_config = {"from_attributes": True}


class BenchCreate(BaseModel):
    mine_id: uuid.UUID
    name: str
    bench_level: str
    elevation_m: Decimal | None = None
    geom_wkt: str | None = None


class BenchOut(BaseModel):
    id: uuid.UUID
    mine_id: uuid.UUID
    name: str
    bench_level: str
    elevation_m: Decimal | None
    is_active: bool
    model_config = {"from_attributes": True}


class OrgUnitCreate(BaseModel):
    parent_id: uuid.UUID | None = None
    name: str
    unit_type: OrgUnitType
    code: str


class OrgUnitOut(BaseModel):
    id: uuid.UUID
    parent_id: uuid.UUID | None
    name: str
    unit_type: OrgUnitType
    code: str
    is_active: bool
    model_config = {"from_attributes": True}


class ApprovalChainCreate(BaseModel):
    name: str
    report_type: str
    mine_id: uuid.UUID | None = None


class ApprovalLevelCreate(BaseModel):
    sequence: int
    role_name: str
    rule: ApprovalRuleType
    sla_hours: int = 24
    escalation_role: str | None = None
    can_skip: bool = False


class ApprovalChainOut(BaseModel):
    id: uuid.UUID
    name: str
    report_type: str
    mine_id: uuid.UUID | None
    is_active: bool
    model_config = {"from_attributes": True}


class TargetCreate(BaseModel):
    mine_id: uuid.UUID
    bench_id: uuid.UUID | None = None
    period: TargetPeriod
    metric: MetricName
    value: Decimal
    unit: str = "t"
    period_start: datetime
    period_end: datetime
    parent_target_id: uuid.UUID | None = None
    weight: Decimal = Decimal("1")


class TargetOut(BaseModel):
    id: uuid.UUID
    mine_id: uuid.UUID
    bench_id: uuid.UUID | None
    period: TargetPeriod
    metric: MetricName
    value: Decimal
    unit: str
    period_start: datetime
    period_end: datetime
    version: int
    model_config = {"from_attributes": True}


class TemplateCreate(BaseModel):
    name: str
    report_type: str
    period: ReportPeriod
    definition: dict


class TemplateOut(BaseModel):
    id: uuid.UUID
    name: str
    report_type: str
    period: ReportPeriod
    is_active: bool
    model_config = {"from_attributes": True}


class AuditEventOut(BaseModel):
    id: uuid.UUID
    action: str
    entity_type: str
    entity_id: str
    user_id: uuid.UUID | None
    details: dict
    previous_hash: str
    current_hash: str
    created_at: datetime
    model_config = {"from_attributes": True}


class AuditChainVerifyResult(BaseModel):
    total_events: int
    verified: int
    broken_at: uuid.UUID | None = None
    is_valid: bool


# ── Sync ─────────────────────────────────────────────────────────────────────

class SyncBatchRequest(BaseModel):
    device_id: str
    idempotency_key: str
    entries: list[ShiftEntryCreate]


class SyncBatchResponse(BaseModel):
    batch_id: uuid.UUID
    accepted: int
    duplicates: int
    errors: list[str] = []


class DeltaPullRequest(BaseModel):
    cursor: str | None = None
    mine_id: uuid.UUID | None = None
    limit: int = 100


class FormSchemaOut(BaseModel):
    schema_version: int
    report_type: str
    fields: list[dict]
