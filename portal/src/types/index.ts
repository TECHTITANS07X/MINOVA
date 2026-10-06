export interface Mine {
  id: string;
  org_unit_id: string;
  name: string;
  code: string;
  latitude: number | null;
  longitude: number | null;
  timezone: string;
  shift_count: number;
  is_active: boolean;
}

export interface Bench {
  id: string;
  mine_id: string;
  name: string;
  bench_level: string;
  elevation_m: number | null;
  is_active: boolean;
}

export interface ShiftEntry {
  id: string;
  mine_id: string;
  bench_id: string | null;
  shift_date: string;
  shift_number: 'first' | 'second' | 'third';
  status: EntryStatus;
  submitted_by: string | null;
  submitted_at: string | null;
  version: number;
  remarks: string;
  values: EntryValue[];
  attachments: EntryAttachment[];
  cause_records: CauseRecord[];
  created_at: string;
}

export type EntryStatus = 'draft' | 'submitted' | 'synced' | 'under_review' | 'returned' | 'approved' | 'rejected';

export interface EntryValue {
  id: string;
  metric: string;
  value: number;
  unit: string;
}

export interface EntryAttachment {
  id: string;
  filename: string;
  content_type: string;
  size_bytes: number;
}

export interface CauseRecord {
  id: string;
  cause_type: string;
  description: string;
  hours_lost: number;
}

export interface Report {
  id: string;
  mine_id: string;
  period: string;
  period_start: string;
  period_end: string;
  status: string;
  generated_description: string;
  values: ReportValue[];
  created_at: string;
}

export interface ReportValue {
  id: string;
  metric: string;
  value: number;
  unit: string;
  section: string;
  row_key: string;
}

export interface ConflictFlag {
  id: string;
  entity_type: string;
  entity_id: string;
  metric: string;
  value_a: number;
  source_a: string;
  value_b: number;
  source_b: string;
  resolution: string;
  resolved_value: number | null;
  resolution_reason: string;
  created_at: string;
}

export interface LineageNode {
  source_type: string;
  source_id: string;
  relationship_type: string;
  label: string;
  value: number | null;
  unit?: string;
  timestamp?: string;
  children: LineageNode[];
}

export interface AnomalyFlag {
  id: string;
  mine_id: string;
  flag_date: string;
  metric: string;
  expected_value: number;
  actual_value: number;
  anomaly_score: number;
  explanation: string;
  status: string;
  contributing_features: Record<string, number>;
}

export interface ApprovalTask {
  id: string;
  entity_type: string;
  entity_id: string;
  current_level: number;
  action: string | null;
  comment: string;
  sla_deadline: string | null;
  created_at: string;
}

export interface Document {
  id: string;
  filename: string;
  doc_type: string;
  category: string;
  mine_id: string | null;
  ingestion_status: string;
  created_at: string;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  route_type: string | null;
  citations: Citation[] | null;
  created_at: string;
}

export interface Citation {
  type: string;
  id: string;
  label: string;
  page?: number;
  value?: number;
}

export interface WeatherObservation {
  id: string;
  mine_id: string;
  observation_date: string;
  temperature_max: number | null;
  precipitation_mm: number;
  weather_code: number | null;
}

export interface RecoveryPlan {
  id: string;
  mine_id: string;
  gap_tonnes: number;
  proposed_daily_targets: Record<string, number>;
  rationale: string;
  status: string;
  created_at: string;
}

export interface TargetComparison {
  target: number;
  actual: number;
  absolute_diff: number;
  percentage_diff: number;
  achievement_pct: number;
}

export interface User {
  sub: string;
  email: string;
  name: string;
  roles: string[];
  mine_id: string | null;
  department: string | null;
}
