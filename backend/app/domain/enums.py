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


# ── Parliamentary Question Engine ────────────────────────────────────────────

class PQHouse(str, Enum):
    LOK_SABHA = "lok_sabha"
    RAJYA_SABHA = "rajya_sabha"


class PQCategory(str, Enum):
    PRODUCTION = "production"
    SAFETY = "safety"
    ENVIRONMENT = "environment"
    FINANCE = "finance"
    LAND_DISPLACEMENT = "land_displacement"
    IMPORT_EXPORT = "import_export"
    PROCUREMENT = "procurement"
    EMPLOYEES = "employees"
    OTHER = "other"


class PQTriggerType(str, Enum):
    SEASONAL = "seasonal"
    INCIDENT = "incident"
    POLICY = "policy"
    BUDGET = "budget"


class EvidencePackStatus(str, Enum):
    DRAFT = "draft"
    READY = "ready"
    STALE = "stale"
    SUBMITTED = "submitted"


# ── Quality-Dispatch Correlation ─────────────────────────────────────────────

class QualityRisk(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class QualityPredictionStatus(str, Enum):
    PENDING = "pending"
    LAB_CONFIRMED = "lab_confirmed"
    SLIPPAGE_FLAGGED = "slippage_flagged"


# ── Production Loss Ledger ───────────────────────────────────────────────────

class LossSourceType(str, Enum):
    CAUSE_RECORD = "cause_record"
    ANOMALY = "anomaly"
    MANUAL = "manual"


class LossRecoveryStatus(str, Enum):
    OPEN = "open"
    PARTIAL = "partial"
    RECOVERED = "recovered"
    WAIVED = "waived"


# ── Statutory Compliance Sentinel ────────────────────────────────────────────

class ComplianceAuthority(str, Enum):
    DGMS = "dgms"
    MOEF = "moef"
    STATE_PCB = "state_pcb"
    COAL_CONTROLLER = "coal_controller"
    MINISTRY_OF_COAL = "ministry_of_coal"


class ComplianceFrequency(str, Enum):
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    HALF_YEARLY = "half_yearly"
    ANNUAL = "annual"


class FilingStatus(str, Enum):
    NOT_STARTED = "not_started"
    INCOMPLETE = "incomplete"
    READY = "ready"
    SUBMITTED = "submitted"
    LATE = "late"


# ── Geological Deviation Learning Loop ───────────────────────────────────────

class DeviationSeverity(str, Enum):
    WITHIN_TOLERANCE = "within_tolerance"
    MODERATE = "moderate"
    SEVERE = "severe"


# ── Explosive-to-Output Correlation ──────────────────────────────────────────

class ExplosiveFlag(str, Enum):
    NORMAL = "normal"
    OVER_CONSUMPTION = "over_consumption"
    UNDER_CONSUMPTION = "under_consumption"


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
    EXPLOSIVES_KG = "explosives_kg"
    DECLARED_GCV = "declared_gcv"


# ── Meeting Action Tracker ──────────────────────────────────────────────────

class MeetingActionStatus(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    OVERDUE = "overdue"

class MeetingType(str, Enum):
    SAFETY = "safety"
    PRODUCTION = "production"
    PLANNING = "planning"
    REVIEW = "review"
    EMERGENCY = "emergency"

# ── Institutional Knowledge ─────────────────────────────────────────────────

class KnowledgeCategory(str, Enum):
    GEOLOGICAL = "geological"
    OPERATIONAL = "operational"
    SAFETY = "safety"
    EQUIPMENT = "equipment"
    ENVIRONMENTAL = "environmental"
    REGULATORY = "regulatory"

# ── Safety Incident Pattern ─────────────────────────────────────────────────

class IncidentSeverity(str, Enum):
    NEAR_MISS = "near_miss"
    MINOR = "minor"
    MODERATE = "moderate"
    SERIOUS = "serious"
    FATAL = "fatal"

class IncidentCategory(str, Enum):
    ROOF_FALL = "roof_fall"
    SLOPE_FAILURE = "slope_failure"
    EQUIPMENT = "equipment"
    BLASTING = "blasting"
    ELECTRICAL = "electrical"
    TRANSPORT = "transport"
    FIRE = "fire"
    GAS = "gas"
    WATER_INRUSH = "water_inrush"
    OTHER = "other"

# ── Photo Evidence Geo-Verification ─────────────────────────────────────────

class PhotoVerificationStatus(str, Enum):
    PENDING = "pending"
    VERIFIED = "verified"
    REJECTED = "rejected"
    SUSPICIOUS = "suspicious"
