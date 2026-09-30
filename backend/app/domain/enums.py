from enum import Enum


class ShiftNumber(str, Enum):
    FIRST = "first"
    SECOND = "second"
    THIRD = "third"


class EntryStatus(str, Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    SYNCED = "synced"
    UNDER_REVIEW = "under_review"
    RETURNED = "returned"
    APPROVED = "approved"
    REJECTED = "rejected"


class ApprovalAction(str, Enum):
    APPROVE = "approve"
    RETURN = "return"
    ESCALATE = "escalate"
    WITHDRAW = "withdraw"


class ReportStatus(str, Enum):
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    RETURNED = "returned"
    FINALIZED = "finalized"


class ReportPeriod(str, Enum):
    SHIFT = "shift"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    HALF_YEARLY = "half_yearly"
    ANNUAL = "annual"


class TargetPeriod(str, Enum):
    ANNUAL = "annual"
    HALF_YEARLY = "half_yearly"
    QUARTERLY = "quarterly"
    MONTHLY = "monthly"
    WEEKLY = "weekly"
    DAILY = "daily"
    SHIFT = "shift"


class ConflictResolution(str, Enum):
    UNRESOLVED = "unresolved"
    ACCEPT_PRIMARY = "accept_primary"
    ACCEPT_SECONDARY = "accept_secondary"
    CORRECTED = "corrected"


class DocumentCategory(str, Enum):
    GEOLOGICAL = "geological"
    PRODUCTION = "production"
    EQUIPMENT = "equipment"
    SAFETY = "safety"
    ENVIRONMENTAL = "environmental"
    PLANNING = "planning"
    FINANCIAL = "financial"
    HISTORICAL = "historical"
    OTHER = "other"


class DocumentType(str, Enum):
    PDF = "pdf"
    IMAGE = "image"
    EXCEL = "excel"
    CSV = "csv"
    WORD = "word"
    POWERPOINT = "powerpoint"
    OTHER = "other"


class IngestionStatus(str, Enum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    OCR_COMPLETE = "ocr_complete"
    STRUCTURED = "structured"
    EMBEDDED = "embedded"
    INDEXED = "indexed"
    REVIEW_PENDING = "review_pending"
    REVIEWED = "reviewed"
    FAILED = "failed"


class AnomalyStatus(str, Enum):
    FLAGGED = "flagged"
    ACKNOWLEDGED = "acknowledged"
    DISMISSED = "dismissed"
    LINKED_TO_CAUSE = "linked_to_cause"


class RecoveryPlanStatus(str, Enum):
    PROPOSED = "proposed"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    MODIFIED = "modified"


class QueryRouteType(str, Enum):
    NUMERIC = "numeric"
    CONTEXTUAL = "contextual"
    HYBRID = "hybrid"
    PLANNING = "planning"
    OUT_OF_SCOPE = "out_of_scope"


class CauseType(str, Enum):
    RAIN_WEATHER = "rain_weather"
    EQUIPMENT_FAILURE = "equipment_failure"
    FIRE_MAJOR_INCIDENT = "fire_major_incident"
    LABOUR_DISRUPTION = "labour_disruption"
    SUPPLY = "supply"
    POWER_FAILURE = "power_failure"
    BLASTING_DELAY = "blasting_delay"
    OTHER = "other"


class ApprovalRuleType(str, Enum):
    ANY_OF = "any_of"
    ALL_OF = "all_of"


class OrgUnitType(str, Enum):
    ORGANISATION = "organisation"
    SUBSIDIARY = "subsidiary"
    AREA = "area"
    MINE = "mine"
    DIVISION = "division"


class AuditAction(str, Enum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    APPROVE = "approve"
    RETURN = "return"
    ESCALATE = "escalate"
    SUBMIT = "submit"
    SYNC = "sync"
    LOGIN = "login"
    RESOLVE_CONFLICT = "resolve_conflict"
    GENERATE_REPORT = "generate_report"
    VERIFY_CHAIN = "verify_chain"
    ACCEPT_PLAN = "accept_plan"
    REJECT_PLAN = "reject_plan"


class StagingReviewStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    EDITED = "edited"
    REJECTED = "rejected"


class MetricName(str, Enum):
    PRODUCTION_TONNES = "production_tonnes"
    OVERBURDEN_M3 = "overburden_m3"
    STRIPPING_RATIO = "stripping_ratio"
    OB_COAL_RATIO = "ob_coal_ratio"
    OPERATING_HOURS = "operating_hours"
    DOWNTIME_HOURS = "downtime_hours"
    EQUIPMENT_AVAILABILITY = "equipment_availability"
    DISPATCH_TONNES = "dispatch_tonnes"
    WORKERS_PRESENT = "workers_present"
