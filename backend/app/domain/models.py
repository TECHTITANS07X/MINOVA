from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import TSVECTOR, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.domain.enums import (
    AnomalyStatus,
    ApprovalAction,
    ApprovalRuleType,
    AuditAction,
    CauseType,
    ComplianceAuthority,
    ComplianceFrequency,
    ConflictResolution,
    DeviationSeverity,
    DocumentCategory,
    DocumentType,
    EntryStatus,
    EvidencePackStatus,
    ExplosiveFlag,
    FilingStatus,
    IncidentCategory,
    IncidentSeverity,
    IngestionStatus,
    KnowledgeCategory,
    LossRecoveryStatus,
    LossSourceType,
    MeetingActionStatus,
    MeetingType,
    MetricName,
    OrgUnitType,
    PhotoVerificationStatus,
    PQCategory,
    PQHouse,
    PQTriggerType,
    QueryRouteType,
    QualityPredictionStatus,
    QualityRisk,
    RecoveryPlanStatus,
    ReportPeriod,
    ReportStatus,
    ShiftNumber,
    StagingReviewStatus,
    TargetPeriod,
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _new_id() -> uuid.UUID:
    return uuid.uuid4()


class OrgUnit(Base):
    __tablename__ = "org_unit"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_new_id)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("org_unit.id"))
    name: Mapped[str] = mapped_column(String(255))
    unit_type: Mapped[OrgUnitType] = mapped_column(SAEnum(OrgUnitType, name="org_unit_type"))
    code: Mapped[str] = mapped_column(String(50), unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    children: Mapped[list[OrgUnit]] = relationship("OrgUnit", back_populates="parent")
    parent: Mapped[OrgUnit | None] = relationship("OrgUnit", back_populates="children", remote_side="OrgUnit.id")
    mines: Mapped[list[Mine]] = relationship("Mine", back_populates="org_unit")


class Mine(Base):
    __tablename__ = "mine"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_new_id)
    org_unit_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("org_unit.id"))
    name: Mapped[str] = mapped_column(String(255))
    code: Mapped[str] = mapped_column(String(50), unique=True)
    latitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 6))
    longitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 6))
    timezone: Mapped[str] = mapped_column(String(50), default="Asia/Kolkata")
    shift_count: Mapped[int] = mapped_column(Integer, default=3)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    org_unit: Mapped[OrgUnit] = relationship("OrgUnit", back_populates="mines")
    benches: Mapped[list[Bench]] = relationship("Bench", back_populates="mine")
    shift_entries: Mapped[list[ShiftEntry]] = relationship("ShiftEntry", back_populates="mine")
    targets: Mapped[list[Target]] = relationship("Target", back_populates="mine")


class Bench(Base):
    __tablename__ = "bench"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_new_id)
    mine_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("mine.id"))
    name: Mapped[str] = mapped_column(String(255))
    bench_level: Mapped[str] = mapped_column(String(50))
    geom = mapped_column(JSON, nullable=True, comment="GeoJSON polygon, srid=4326")
    elevation_m: Mapped[Decimal | None] = mapped_column(Numeric(8, 2))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    mine: Mapped[Mine] = relationship("Mine", back_populates="benches")


class AppUser(Base):
    __tablename__ = "app_user"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_new_id)
    keycloak_id: Mapped[str] = mapped_column(String(255), unique=True)
    username: Mapped[str] = mapped_column(String(255), unique=True)
    full_name: Mapped[str] = mapped_column(String(255))
    email: Mapped[str] = mapped_column(String(255))
    mine_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("mine.id"))
    department: Mapped[str | None] = mapped_column(String(100))
    designation: Mapped[str | None] = mapped_column(String(100))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    roles: Mapped[list[Role]] = relationship("Role", secondary="user_role", back_populates="users")


class Role(Base):
    __tablename__ = "role"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_new_id)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    display_name: Mapped[str] = mapped_column(String(255))
    level: Mapped[int] = mapped_column(Integer, default=0)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False)

    users: Mapped[list[AppUser]] = relationship("AppUser", secondary="user_role", back_populates="roles")
    permissions: Mapped[list[Permission]] = relationship("Permission", secondary="role_permission", back_populates="roles")


class UserRole(Base):
    __tablename__ = "user_role"
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("app_user.id"), primary_key=True)
    role_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("role.id"), primary_key=True)


class Permission(Base):
    __tablename__ = "permission"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_new_id)
    resource: Mapped[str] = mapped_column(String(100))
    action: Mapped[str] = mapped_column(String(50))
    description: Mapped[str] = mapped_column(String(255), default="")

    roles: Mapped[list[Role]] = relationship("Role", secondary="role_permission", back_populates="permissions")

    __table_args__ = (UniqueConstraint("resource", "action"),)


class RolePermission(Base):
    __tablename__ = "role_permission"
    role_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("role.id"), primary_key=True)
    permission_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("permission.id"), primary_key=True)


class ApprovalChain(Base):
    __tablename__ = "approval_chain"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_new_id)
    name: Mapped[str] = mapped_column(String(255))
    report_type: Mapped[str] = mapped_column(String(100))
    mine_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("mine.id"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    levels: Mapped[list[ApprovalLevel]] = relationship("ApprovalLevel", back_populates="chain", order_by="ApprovalLevel.sequence")


class ApprovalLevel(Base):
    __tablename__ = "approval_level"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_new_id)
    chain_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("approval_chain.id"))
    sequence: Mapped[int] = mapped_column(Integer)
    role_name: Mapped[str] = mapped_column(String(100))
    rule: Mapped[ApprovalRuleType] = mapped_column(SAEnum(ApprovalRuleType, name="approval_rule_type"))
    sla_hours: Mapped[int] = mapped_column(Integer, default=24)
    escalation_role: Mapped[str | None] = mapped_column(String(100))
    can_skip: Mapped[bool] = mapped_column(Boolean, default=False)

    chain: Mapped[ApprovalChain] = relationship("ApprovalChain", back_populates="levels")


class ReportTemplate(Base):
    __tablename__ = "report_template"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_new_id)
    name: Mapped[str] = mapped_column(String(255))
    report_type: Mapped[str] = mapped_column(String(100))
    period: Mapped[ReportPeriod] = mapped_column(SAEnum(ReportPeriod, name="report_period"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    versions: Mapped[list[ReportTemplateVersion]] = relationship("ReportTemplateVersion", back_populates="template")


class ReportTemplateVersion(Base):
    __tablename__ = "report_template_version"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_new_id)
    template_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("report_template.id"))
    version: Mapped[int] = mapped_column(Integer)
    definition: Mapped[dict] = mapped_column(JSON)
    is_current: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    template: Mapped[ReportTemplate] = relationship("ReportTemplate", back_populates="versions")

    __table_args__ = (UniqueConstraint("template_id", "version"),)


class ShiftEntry(Base):
    __tablename__ = "shift_entry"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_new_id)
    mine_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("mine.id"))
    bench_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("bench.id"))
    shift_date: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    shift_number: Mapped[ShiftNumber] = mapped_column(SAEnum(ShiftNumber, name="shift_number"))
    status: Mapped[EntryStatus] = mapped_column(SAEnum(EntryStatus, name="entry_status"), default=EntryStatus.DRAFT)
    submitted_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("app_user.id"))
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    version: Mapped[int] = mapped_column(Integer, default=1)
    previous_version_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("shift_entry.id"))
    sync_batch_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("sync_batch.id"))
    remarks: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    mine: Mapped[Mine] = relationship("Mine", back_populates="shift_entries")
    values: Mapped[list[EntryValue]] = relationship("EntryValue", back_populates="shift_entry")
    attachments: Mapped[list[EntryAttachment]] = relationship("EntryAttachment", back_populates="shift_entry")
    cause_records: Mapped[list[CauseRecord]] = relationship("CauseRecord", back_populates="shift_entry")

    __table_args__ = (
        Index("ix_shift_entry_mine_date", "mine_id", "shift_date", "shift_number"),
    )


class EntryValue(Base):
    __tablename__ = "entry_value"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_new_id)
    shift_entry_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("shift_entry.id"))
    metric: Mapped[MetricName] = mapped_column(SAEnum(MetricName, name="metric_name"))
    value: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    unit: Mapped[str] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    shift_entry: Mapped[ShiftEntry] = relationship("ShiftEntry", back_populates="values")


class EntryAttachment(Base):
    __tablename__ = "entry_attachment"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_new_id)
    shift_entry_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("shift_entry.id"))
    filename: Mapped[str] = mapped_column(String(512))
    content_type: Mapped[str] = mapped_column(String(100))
    object_key: Mapped[str] = mapped_column(String(512))
    size_bytes: Mapped[int] = mapped_column(Integer)
    checksum_sha256: Mapped[str] = mapped_column(String(64))
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    shift_entry: Mapped[ShiftEntry] = relationship("ShiftEntry", back_populates="attachments")


class Target(Base):
    __tablename__ = "target"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_new_id)
    mine_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("mine.id"))
    bench_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("bench.id"))
    period: Mapped[TargetPeriod] = mapped_column(SAEnum(TargetPeriod, name="target_period"))
    metric: Mapped[MetricName] = mapped_column(SAEnum(MetricName, name="target_metric_name", create_constraint=False))
    value: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    unit: Mapped[str] = mapped_column(String(20))
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    parent_target_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("target.id"))
    weight: Mapped[Decimal] = mapped_column(Numeric(8, 4), default=Decimal("1"))
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    mine: Mapped[Mine] = relationship("Mine", back_populates="targets")


class CauseRecord(Base):
    __tablename__ = "cause_record"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_new_id)
    shift_entry_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("shift_entry.id"))
    cause_type: Mapped[CauseType] = mapped_column(SAEnum(CauseType, name="cause_type"))
    description: Mapped[str] = mapped_column(Text)
    hours_lost: Mapped[Decimal] = mapped_column(Numeric(8, 2), default=Decimal("0"))
    evidence_attachment_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("entry_attachment.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    shift_entry: Mapped[ShiftEntry] = relationship("ShiftEntry", back_populates="cause_records")


class Report(Base):
    __tablename__ = "report"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_new_id)
    mine_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("mine.id"))
    template_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("report_template.id"))
    period: Mapped[ReportPeriod] = mapped_column(SAEnum(ReportPeriod, name="report_report_period", create_constraint=False))
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[ReportStatus] = mapped_column(SAEnum(ReportStatus, name="report_status"), default=ReportStatus.DRAFT)
    generated_description: Mapped[str] = mapped_column(Text, default="")
    edited_description: Mapped[str | None] = mapped_column(Text)
    generated_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("app_user.id"))
    calc_run_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("calc_run.id"))
    export_path: Mapped[str | None] = mapped_column(String(512))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    finalized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    values: Mapped[list[ReportValue]] = relationship("ReportValue", back_populates="report")


class ReportValue(Base):
    __tablename__ = "report_value"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_new_id)
    report_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("report.id"))
    metric: Mapped[str] = mapped_column(String(100))
    value: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    unit: Mapped[str] = mapped_column(String(20))
    section: Mapped[str] = mapped_column(String(100), default="")
    row_key: Mapped[str] = mapped_column(String(200), default="")
    calc_run_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("calc_run.id"))

    report: Mapped[Report] = relationship("Report", back_populates="values")
    lineage_edges: Mapped[list[LineageEdge]] = relationship("LineageEdge", back_populates="report_value")


class CalcRun(Base):
    __tablename__ = "calc_run"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_new_id)
    formula_id: Mapped[str] = mapped_column(String(100))
    formula_version: Mapped[int] = mapped_column(Integer)
    input_ids: Mapped[dict] = mapped_column(JSON)
    output_value: Mapped[str] = mapped_column(String(100))
    input_hash: Mapped[str] = mapped_column(String(64), index=True)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class LineageEdge(Base):
    __tablename__ = "lineage_edge"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_new_id)
    report_value_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("report_value.id"))
    source_type: Mapped[str] = mapped_column(String(50))
    source_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    relationship_type: Mapped[str] = mapped_column(String(50), default="input")

    report_value: Mapped[ReportValue] = relationship("ReportValue", back_populates="lineage_edges")

    __table_args__ = (
        Index("ix_lineage_source", "source_type", "source_id"),
    )


class ApprovalTask(Base):
    __tablename__ = "approval_task"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_new_id)
    entity_type: Mapped[str] = mapped_column(String(50))
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    chain_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("approval_chain.id"))
    current_level: Mapped[int] = mapped_column(Integer, default=0)
    action: Mapped[ApprovalAction | None] = mapped_column(SAEnum(ApprovalAction, name="approval_action_type"))
    acted_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("app_user.id"))
    comment: Mapped[str] = mapped_column(Text, default="")
    temporal_workflow_id: Mapped[str | None] = mapped_column(String(255))
    sla_deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AuditEvent(Base):
    __tablename__ = "audit_event"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_new_id)
    action: Mapped[AuditAction] = mapped_column(SAEnum(AuditAction, name="audit_action"))
    entity_type: Mapped[str] = mapped_column(String(100))
    entity_id: Mapped[str] = mapped_column(String(255))
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("app_user.id"))
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    previous_hash: Mapped[str] = mapped_column(String(64), default="")
    current_hash: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    __table_args__ = (
        Index("ix_audit_entity", "entity_type", "entity_id"),
        Index("ix_audit_created", "created_at"),
    )


class ConflictFlag(Base):
    __tablename__ = "conflict_flag"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_new_id)
    entity_type: Mapped[str] = mapped_column(String(100))
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    metric: Mapped[str] = mapped_column(String(100))
    value_a: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    source_a: Mapped[str] = mapped_column(String(255))
    value_b: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    source_b: Mapped[str] = mapped_column(String(255))
    tolerance_pct: Mapped[Decimal] = mapped_column(Numeric(8, 4))
    resolution: Mapped[ConflictResolution] = mapped_column(
        SAEnum(ConflictResolution, name="conflict_resolution"), default=ConflictResolution.UNRESOLVED
    )
    resolved_value: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    resolved_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("app_user.id"))
    resolution_reason: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Document(Base):
    __tablename__ = "document"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_new_id)
    filename: Mapped[str] = mapped_column(String(512))
    doc_type: Mapped[DocumentType] = mapped_column(SAEnum(DocumentType, name="document_type"))
    category: Mapped[DocumentCategory] = mapped_column(SAEnum(DocumentCategory, name="document_category"))
    mine_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("mine.id"))
    period_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    object_key: Mapped[str] = mapped_column(String(512))
    size_bytes: Mapped[int] = mapped_column(Integer)
    checksum_sha256: Mapped[str] = mapped_column(String(64))
    ingestion_status: Mapped[IngestionStatus] = mapped_column(
        SAEnum(IngestionStatus, name="ingestion_status"), default=IngestionStatus.UPLOADED
    )
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    uploaded_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("app_user.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    pages: Mapped[list[DocumentPage]] = relationship("DocumentPage", back_populates="document")
    chunks: Mapped[list[DocChunk]] = relationship("DocChunk", back_populates="document")


class DocumentPage(Base):
    __tablename__ = "document_page"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_new_id)
    document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("document.id"))
    page_number: Mapped[int] = mapped_column(Integer)
    text_content: Mapped[str] = mapped_column(Text, default="")
    ocr_confidence: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    image_key: Mapped[str | None] = mapped_column(String(512))

    document: Mapped[Document] = relationship("Document", back_populates="pages")


class DocChunk(Base):
    __tablename__ = "doc_chunk"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_new_id)
    document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("document.id"))
    page_number: Mapped[int | None] = mapped_column(Integer)
    chunk_index: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)
    embedding = mapped_column(JSON, nullable=True, comment="1024-dim float[] for BGE-M3")
    tsv = mapped_column(TSVECTOR, nullable=True)
    bbox: Mapped[dict | None] = mapped_column(JSON)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    document: Mapped[Document] = relationship("Document", back_populates="chunks")

    __table_args__ = (
        Index("ix_doc_chunk_tsv", "tsv", postgresql_using="gin"),  # vector search done in Python (no pgvector)
    )


class ExtractedTable(Base):
    __tablename__ = "extracted_table"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_new_id)
    document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("document.id"))
    page_number: Mapped[int] = mapped_column(Integer)
    table_data: Mapped[dict] = mapped_column(JSON)
    bbox: Mapped[dict | None] = mapped_column(JSON)
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class ExtractedValueStaging(Base):
    __tablename__ = "extracted_value_staging"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_new_id)
    document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("document.id"))
    metric: Mapped[str] = mapped_column(String(100))
    value: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    unit: Mapped[str] = mapped_column(String(20), default="")
    confidence: Mapped[Decimal] = mapped_column(Numeric(5, 2))
    source_page: Mapped[int | None] = mapped_column(Integer)
    source_bbox: Mapped[dict | None] = mapped_column(JSON)
    review_status: Mapped[StagingReviewStatus] = mapped_column(
        SAEnum(StagingReviewStatus, name="staging_review_status"), default=StagingReviewStatus.PENDING
    )
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("app_user.id"))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    accepted_value: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class AnomalyFlag(Base):
    __tablename__ = "anomaly_flag"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_new_id)
    mine_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("mine.id"))
    bench_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("bench.id"))
    flag_date: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    metric: Mapped[str] = mapped_column(String(100))
    expected_value: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    actual_value: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    anomaly_score: Mapped[Decimal] = mapped_column(Numeric(8, 4))
    contributing_features: Mapped[dict] = mapped_column(JSON, default=dict)
    explanation: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[AnomalyStatus] = mapped_column(SAEnum(AnomalyStatus, name="anomaly_status"), default=AnomalyStatus.FLAGGED)
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("app_user.id"))
    review_reason: Mapped[str] = mapped_column(Text, default="")
    linked_cause_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("cause_record.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class WeatherObservation(Base):
    __tablename__ = "weather_observation"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_new_id)
    mine_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("mine.id"))
    observation_date: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    temperature_max: Mapped[Decimal | None] = mapped_column(Numeric(5, 1))
    temperature_min: Mapped[Decimal | None] = mapped_column(Numeric(5, 1))
    precipitation_mm: Mapped[Decimal] = mapped_column(Numeric(8, 2), default=Decimal("0"))
    wind_speed_kmh: Mapped[Decimal | None] = mapped_column(Numeric(6, 1))
    humidity_pct: Mapped[Decimal | None] = mapped_column(Numeric(5, 1))
    weather_code: Mapped[int | None] = mapped_column(Integer)
    source: Mapped[str] = mapped_column(String(50), default="open-meteo")
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    __table_args__ = (
        UniqueConstraint("mine_id", "observation_date", "source"),
    )


class WeatherForecast(Base):
    __tablename__ = "weather_forecast"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_new_id)
    mine_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("mine.id"))
    forecast_date: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    precipitation_mm: Mapped[Decimal] = mapped_column(Numeric(8, 2), default=Decimal("0"))
    temperature_max: Mapped[Decimal | None] = mapped_column(Numeric(5, 1))
    weather_code: Mapped[int | None] = mapped_column(Integer)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class RecoveryPlan(Base):
    __tablename__ = "recovery_plan"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_new_id)
    mine_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("mine.id"))
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    gap_tonnes: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    proposed_daily_targets: Mapped[dict] = mapped_column(JSON)
    rationale: Mapped[str] = mapped_column(Text, default="")
    historical_evidence: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[RecoveryPlanStatus] = mapped_column(
        SAEnum(RecoveryPlanStatus, name="recovery_plan_status"), default=RecoveryPlanStatus.PROPOSED
    )
    decided_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("app_user.id"))
    decision_reason: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ChatSession(Base):
    __tablename__ = "chat_session"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_new_id)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("app_user.id"))
    title: Mapped[str] = mapped_column(String(255), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    messages: Mapped[list[ChatMessage]] = relationship("ChatMessage", back_populates="session")


class ChatMessage(Base):
    __tablename__ = "chat_message"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_new_id)
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("chat_session.id"))
    role: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text)
    route_type: Mapped[QueryRouteType | None] = mapped_column(SAEnum(QueryRouteType, name="query_route_type"))
    citations: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    session: Mapped[ChatSession] = relationship("ChatSession", back_populates="messages")


class SyncBatch(Base):
    __tablename__ = "sync_batch"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_new_id)
    device_id: Mapped[str] = mapped_column(String(255))
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("app_user.id"))
    entries_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(50), default="received")
    idempotency_key: Mapped[str] = mapped_column(String(255), unique=True)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Topic(Base):
    __tablename__ = "topic"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_new_id)
    label: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text, default="")
    mine_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("mine.id"))
    period_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    document_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    terms: Mapped[list[TopicTerm]] = relationship("TopicTerm", back_populates="topic")


class TopicTerm(Base):
    __tablename__ = "topic_term"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_new_id)
    topic_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("topic.id"))
    term: Mapped[str] = mapped_column(String(255))
    weight: Mapped[Decimal] = mapped_column(Numeric(8, 4))
    language: Mapped[str] = mapped_column(String(10), default="en")

    topic: Mapped[TopicTerm | None] = relationship("Topic", back_populates="terms")


# ── Parliamentary Question Engine ────────────────────────────────────────────


class QuestionPattern(Base):
    __tablename__ = "question_pattern"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_new_id)
    code: Mapped[str] = mapped_column(String(50), unique=True)
    title: Mapped[str] = mapped_column(String(500))
    category: Mapped[PQCategory] = mapped_column(SAEnum(PQCategory, name="pq_category"))
    trigger_type: Mapped[PQTriggerType] = mapped_column(SAEnum(PQTriggerType, name="pq_trigger_type"))
    historical_frequency_10y: Mapped[int] = mapped_column(Integer, default=0)
    typical_months: Mapped[list] = mapped_column(JSON, default=list, comment="Months 1-12 in which this pattern historically peaks")
    trigger_conditions: Mapped[dict] = mapped_column(JSON, default=dict, comment="e.g. {metric: production_tonnes, drop_pct: 15} or {authority: dgms}")
    sample_questions: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class ParliamentaryQuestion(Base):
    __tablename__ = "parliamentary_question"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_new_id)
    house: Mapped[PQHouse] = mapped_column(SAEnum(PQHouse, name="pq_house"))
    question_number: Mapped[str] = mapped_column(String(50))
    asked_on: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    session_name: Mapped[str] = mapped_column(String(100), default="")
    member_name: Mapped[str] = mapped_column(String(255))
    constituency: Mapped[str] = mapped_column(String(255), default="")
    ministry: Mapped[str] = mapped_column(String(255), default="Coal")
    subject: Mapped[str] = mapped_column(String(500))
    question_text: Mapped[str] = mapped_column(Text, default="")
    category: Mapped[PQCategory] = mapped_column(SAEnum(PQCategory, name="pq_category"))
    pattern_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("question_pattern.id"))
    days_to_answer: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


# ── Evidence Packs (pre-generated PQ answers) ─────────────────────────────────


class EvidencePack(Base):
    __tablename__ = "evidence_pack"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_new_id)
    pattern_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("question_pattern.id"))
    title: Mapped[str] = mapped_column(String(500))
    likelihood_score: Mapped[Decimal] = mapped_column(Numeric(6, 4), default=Decimal("0"))
    status: Mapped[EvidencePackStatus] = mapped_column(
        SAEnum(EvidencePackStatus, name="evidence_pack_status"), default=EvidencePackStatus.DRAFT
    )
    period_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    mine_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("mine.id"))
    summary: Mapped[str] = mapped_column(Text, default="")
    sections: Mapped[dict] = mapped_column(JSON, default=dict, comment="Named sections; figures carry lineage refs for Replay the Number")
    data_as_of: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    approved_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("app_user.id"))

    pattern: Mapped[QuestionPattern] = relationship("QuestionPattern")


# ── Quality-Dispatch Correlation ─────────────────────────────────────────────


class QualitySample(Base):
    __tablename__ = "quality_sample"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_new_id)
    mine_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("mine.id"))
    bench_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("bench.id"))
    sample_date: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    gcv_kcal: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    grade: Mapped[str] = mapped_column(String(20))
    source: Mapped[str] = mapped_column(String(50), default="uttam_lab")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    mine: Mapped[Mine] = relationship("Mine")


class QualityPrediction(Base):
    __tablename__ = "quality_prediction"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_new_id)
    mine_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("mine.id"))
    bench_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("bench.id"))
    prediction_date: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    baseline_gcv: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    predicted_gcv: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    declared_gcv: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    deviation_pct: Mapped[Decimal] = mapped_column(Numeric(8, 4), default=Decimal("0"))
    risk: Mapped[QualityRisk] = mapped_column(SAEnum(QualityRisk, name="quality_risk"), default=QualityRisk.LOW)
    status: Mapped[QualityPredictionStatus] = mapped_column(
        SAEnum(QualityPredictionStatus, name="quality_prediction_status"), default=QualityPredictionStatus.PENDING
    )
    basis: Mapped[dict] = mapped_column(JSON, default=dict, comment="Samples/months used for the baseline; evidence for Replay")
    lab_gcv: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    lab_confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    flagged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    mine: Mapped[Mine] = relationship("Mine")


# ── Production Loss Ledger / Recovery Debt ────────────────────────────────────


class LossLedgerEntry(Base):
    __tablename__ = "loss_ledger_entry"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_new_id)
    mine_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("mine.id"))
    loss_date: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    cause_type: Mapped[CauseType] = mapped_column(SAEnum(CauseType, name="loss_cause_type"))
    description: Mapped[str] = mapped_column(Text, default="")
    tonnes_lost: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    hours_lost: Mapped[Decimal] = mapped_column(Numeric(8, 2), default=Decimal("0"))
    source_type: Mapped[LossSourceType] = mapped_column(SAEnum(LossSourceType, name="loss_source_type"))
    source_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    recovery_status: Mapped[LossRecoveryStatus] = mapped_column(
        SAEnum(LossRecoveryStatus, name="loss_recovery_status"), default=LossRecoveryStatus.OPEN
    )
    recovered_tonnes: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=Decimal("0"))
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("app_user.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    mine: Mapped[Mine] = relationship("Mine")


# ── Shift Handover Intelligence ──────────────────────────────────────────────


class ShiftHandover(Base):
    __tablename__ = "shift_handover"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_new_id)
    mine_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("mine.id"))
    shift_date: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    outgoing_shift: Mapped[ShiftNumber] = mapped_column(SAEnum(ShiftNumber, name="handover_outgoing_shift"))
    brief: Mapped[dict] = mapped_column(JSON, default=dict, comment="production, pending, equipment, safety, weather, notes sections")
    critical_items: Mapped[list] = mapped_column(JSON, default=list)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    acknowledged_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("app_user.id"))
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    mine: Mapped[Mine] = relationship("Mine")


# ── Statutory Compliance Sentinel ────────────────────────────────────────────


class ComplianceObligation(Base):
    __tablename__ = "compliance_obligation"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_new_id)
    mine_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("mine.id"), comment="NULL = applies to all mines")
    authority: Mapped[ComplianceAuthority] = mapped_column(SAEnum(ComplianceAuthority, name="compliance_authority"))
    title: Mapped[str] = mapped_column(String(500))
    description: Mapped[str] = mapped_column(Text, default="")
    frequency: Mapped[ComplianceFrequency] = mapped_column(SAEnum(ComplianceFrequency, name="compliance_frequency"))
    due_day: Mapped[int] = mapped_column(Integer, default=10, comment="Day of month the filing is due")
    required_metrics: Mapped[list] = mapped_column(JSON, default=list, comment="MetricNames that must be present for the period")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class ComplianceFiling(Base):
    __tablename__ = "compliance_filing"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_new_id)
    obligation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("compliance_obligation.id"))
    mine_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("mine.id"))
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    due_date: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[FilingStatus] = mapped_column(SAEnum(FilingStatus, name="filing_status"), default=FilingStatus.NOT_STARTED)
    completion_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("0"))
    missing_metrics: Mapped[list] = mapped_column(JSON, default=list)
    report_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("report.id"))
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    submitted_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("app_user.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    obligation: Mapped[ComplianceObligation] = relationship("ComplianceObligation")


# ── Explosive-to-Output Correlation ──────────────────────────────────────────


class ExplosiveLog(Base):
    __tablename__ = "explosive_log"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_new_id)
    mine_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("mine.id"))
    bench_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("bench.id"))
    log_date: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    explosives_kg: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    ob_m3: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    coal_tonnes: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))
    kg_per_m3: Mapped[Decimal] = mapped_column(Numeric(8, 4), default=Decimal("0"))
    baseline_kg_per_m3: Mapped[Decimal] = mapped_column(Numeric(8, 4), default=Decimal("0"))
    deviation_pct: Mapped[Decimal] = mapped_column(Numeric(8, 4), default=Decimal("0"))
    flag: Mapped[ExplosiveFlag] = mapped_column(SAEnum(ExplosiveFlag, name="explosive_flag"), default=ExplosiveFlag.NORMAL)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    mine: Mapped[Mine] = relationship("Mine")


# ── Geological Deviation Learning Loop ───────────────────────────────────────


class GeologicalPrediction(Base):
    __tablename__ = "geological_prediction"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_new_id)
    mine_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("mine.id"))
    bench_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("bench.id"))
    seam_name: Mapped[str] = mapped_column(String(100))
    predicted_thickness_m: Mapped[Decimal] = mapped_column(Numeric(8, 2))
    predicted_gcv: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    tolerance_pct: Mapped[Decimal] = mapped_column(Numeric(6, 3), default=Decimal("10.000"))
    source: Mapped[str] = mapped_column(String(100), default="CMPDI")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    mine: Mapped[Mine] = relationship("Mine")
    observations: Mapped[list[GeologicalObservation]] = relationship("GeologicalObservation", back_populates="prediction")


class GeologicalObservation(Base):
    __tablename__ = "geological_observation"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_new_id)
    prediction_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("geological_prediction.id"))
    observed_date: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    actual_thickness_m: Mapped[Decimal] = mapped_column(Numeric(8, 2))
    actual_gcv: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    thickness_dev_pct: Mapped[Decimal] = mapped_column(Numeric(8, 4), default=Decimal("0"))
    gcv_dev_pct: Mapped[Decimal] = mapped_column(Numeric(8, 4), default=Decimal("0"))
    severity: Mapped[DeviationSeverity] = mapped_column(
        SAEnum(DeviationSeverity, name="deviation_severity"), default=DeviationSeverity.WITHIN_TOLERANCE
    )
    notes: Mapped[str] = mapped_column(Text, default="")
    recorded_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("app_user.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    prediction: Mapped[GeologicalPrediction] = relationship("GeologicalPrediction", back_populates="observations")


# ── Meeting Action Tracker ──────────────────────────────────────────────────

class MeetingAction(Base):
    __tablename__ = "meeting_action"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_new_id)
    mine_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("mine.id"))
    meeting_type: Mapped[MeetingType] = mapped_column(SAEnum(MeetingType, name="meeting_type"))
    meeting_date: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    title: Mapped[str] = mapped_column(String(500))
    description: Mapped[str] = mapped_column(Text, default="")
    assigned_to: Mapped[str] = mapped_column(String(255))
    assigned_role: Mapped[str] = mapped_column(String(100), default="")
    due_date: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[MeetingActionStatus] = mapped_column(SAEnum(MeetingActionStatus, name="meeting_action_status"), default=MeetingActionStatus.OPEN)
    completion_notes: Mapped[str] = mapped_column(Text, default="")
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("app_user.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    mine: Mapped[Mine] = relationship("Mine")


# ── Institutional Knowledge Preservation ────────────────────────────────────

class KnowledgeEntry(Base):
    __tablename__ = "knowledge_entry"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_new_id)
    mine_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("mine.id"))
    category: Mapped[KnowledgeCategory] = mapped_column(SAEnum(KnowledgeCategory, name="knowledge_category"))
    title: Mapped[str] = mapped_column(String(500))
    content: Mapped[str] = mapped_column(Text)
    author_name: Mapped[str] = mapped_column(String(255))
    author_designation: Mapped[str] = mapped_column(String(255), default="")
    years_experience: Mapped[int] = mapped_column(Integer, default=0)
    tags: Mapped[list] = mapped_column(JSON, default=list)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    verified_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("app_user.id"))
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("app_user.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    mine: Mapped[Mine | None] = relationship("Mine")


# ── Safety Incident Pattern Detector ────────────────────────────────────────

class SafetyIncident(Base):
    __tablename__ = "safety_incident"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_new_id)
    mine_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("mine.id"))
    bench_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("bench.id"))
    incident_date: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    category: Mapped[IncidentCategory] = mapped_column(SAEnum(IncidentCategory, name="incident_category"))
    severity: Mapped[IncidentSeverity] = mapped_column(SAEnum(IncidentSeverity, name="incident_severity"))
    description: Mapped[str] = mapped_column(Text)
    location_description: Mapped[str] = mapped_column(String(500), default="")
    workers_involved: Mapped[int] = mapped_column(Integer, default=0)
    injuries: Mapped[int] = mapped_column(Integer, default=0)
    root_cause: Mapped[str] = mapped_column(Text, default="")
    corrective_actions: Mapped[str] = mapped_column(Text, default="")
    reported_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("app_user.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    mine: Mapped[Mine] = relationship("Mine")

    __table_args__ = (
        Index("ix_safety_incident_mine_date", "mine_id", "incident_date"),
    )


class SafetyPattern(Base):
    __tablename__ = "safety_pattern"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_new_id)
    mine_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("mine.id"))
    pattern_name: Mapped[str] = mapped_column(String(500))
    category: Mapped[IncidentCategory] = mapped_column(SAEnum(IncidentCategory, name="safety_pattern_category", create_constraint=False))
    description: Mapped[str] = mapped_column(Text)
    incident_count: Mapped[int] = mapped_column(Integer, default=0)
    confidence: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("0"))
    contributing_factors: Mapped[list] = mapped_column(JSON, default=list)
    recommendations: Mapped[list] = mapped_column(JSON, default=list)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    mine: Mapped[Mine | None] = relationship("Mine")


# ── Photo-Evidence Geo-Verification ─────────────────────────────────────────

class PhotoEvidence(Base):
    __tablename__ = "photo_evidence"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_new_id)
    mine_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("mine.id"))
    bench_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("bench.id"))
    filename: Mapped[str] = mapped_column(String(512))
    object_key: Mapped[str] = mapped_column(String(512))
    photo_latitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 6))
    photo_longitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 6))
    photo_timestamp: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expected_latitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 6))
    expected_longitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 6))
    distance_m: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    verification_status: Mapped[PhotoVerificationStatus] = mapped_column(
        SAEnum(PhotoVerificationStatus, name="photo_verification_status"), default=PhotoVerificationStatus.PENDING
    )
    verification_notes: Mapped[str] = mapped_column(Text, default="")
    context: Mapped[str] = mapped_column(String(255), default="")
    uploaded_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("app_user.id"))
    verified_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("app_user.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    mine: Mapped[Mine] = relationship("Mine")
