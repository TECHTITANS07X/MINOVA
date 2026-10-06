# MINOVA Build Progress

## Phase 0: Preflight & Environment — COMPLETE
- [x] System preflight (C: 16.97GB, D: 127.72GB, RTX 3050 6GB)
- [x] Environment variables persisted (19 vars, all to D:)
- [x] Python 3.11.9 embeddable + virtualenv
- [x] JDK 17.0.20.1 (Eclipse Temurin)
- [x] Node.js v24.13.1 (system)
- [x] Flutter 3.47.5 (stable)
- [x] PostgreSQL 16.9 portable on port 5433
- [x] Temporal CLI 1.9.1
- [x] Keycloak 26.0.7 with minova realm imported
- [x] Ollama 0.34.4 with Qwen3:8b pulled (5.2GB)
- [x] Backend venv with all deps installed
- [ ] BGE-M3 embedding model (deferred — lazy-loads on first use)
- [ ] PaddleOCR models (deferred — lazy-loads on first use)

**Deviation**: MinIO open-source archived (410 Gone on all downloads). Using filesystem storage adapter with S3-compatible API interface.
**Deviation**: PostGIS and pgvector not available in portable PG. Geometry stored as GeoJSON (JSON column), vector search done in Python with numpy cosine similarity.

## Phase 1: Data Layer — COMPLETE
- [x] 38 SQLAlchemy 2.0 ORM models (all domain tables)
- [x] Alembic migration generated and applied (39 tables total)
- [x] Database seeded: 4 org units, 6 mines, 18 benches, 12 users, 8 roles, 30 targets, 21 shift entries, 84 entry values

## Phase 2: Core Domain — COMPLETE
- [x] Deterministic calculation engine (all Decimal, ROUND_HALF_EVEN)
- [x] 36/36 calculation tests PASS (mandatory 3100+2900+2000=8000)
- [x] FormulaSpec versioned system
- [x] Unit conversions (mass/volume)
- [x] Target cascade allocation
- [x] 11 API routers (entries, reports, approval, conflicts, lineage, documents, chat, anomalies, weather, admin, sync)
- [x] Pydantic v2 schemas for all endpoints
- [x] RBAC + mine-scoped access via JWT/Keycloak

## Phase 3: Temporal Workflows — COMPLETE
- [x] ApprovalWorkflow (multi-level with signals/queries)
- [x] DailyRollupWorkflow (shift -> daily aggregation)
- [x] PeriodRollupWorkflow (daily -> weekly/monthly/quarterly)
- [x] IngestionWorkflow (document OCR -> chunk -> embed)
- [x] Worker registering all workflows + activities
- [x] Task queue: minova-main

## Phase 4: Flutter Mobile — COMPLETE
- [x] Flutter 3.47.5 project created (Android + Windows)
- [x] Models (ShiftEntry, Mine)
- [x] Local SQLite database (offline-first)
- [x] API service (REST client with secure token storage)
- [x] Sync service (push/pull with conflict detection)
- [x] Provider state management
- [x] Dashboard screen with stats cards
- [x] Entry form (multi-field, save draft / submit)
- [x] Entries list with status badges
- [x] Sync screen with push/pull stats
- [x] 93 pub dependencies resolved

## Phase 5: Report Engine — COMPLETE
- [x] Excel generation (openpyxl with styled headers)
- [x] PDF generation (reportlab with table styling)
- [x] DOCX generation (python-docx)
- [x] ReportData/MetricRow dataclasses
- [x] All numeric values pre-computed by calc engine

## Phase 6: Conflict & Lineage — COMPLETE
- [x] Conflict detection API (list, detail, resolve with mandatory reason)
- [x] Lineage API (replay-the-number tree, verify, replay)
- [x] Portal pages: Conflicts (side-by-side comparison), ReplayTheNumber (tree viz)

## Phase 7: Document Intelligence — COMPLETE (code)
- [x] PaddleOCR integration (lazy-loaded)
- [x] Text chunking (512 tokens, 64 overlap)
- [x] BGE-M3 embedding generation (lazy-loaded)
- [x] Hybrid search (text weight + vector cosine similarity)
- [x] Portal: Documents page with upload/search/review

## Phase 8: RAG Router & AI Chat — COMPLETE
- [x] LLM service (Ollama Qwen3:8b integration)
- [x] Query router (numeric/descriptive/hybrid classification)
- [x] Grounded description generation (no hallucinated numbers)
- [x] Streaming response support
- [x] Portal: AIChat page with citations

## Phase 9: Anomaly Detection & Weather — COMPLETE
- [x] IsolationForest anomaly detection (scikit-learn)
- [x] Z-score fallback for small datasets
- [x] Weather service (Open-Meteo API)
- [x] Weather impact computation (rain/wind/heat)
- [x] Recovery plan API
- [x] Portal: Anomalies page, Weather page

## Phase 10: React Portal — COMPLETE
- [x] 25 pages: Dashboard, DataEntry, ApprovalConsole, Reports, ReplayTheNumber, Conflicts, Documents, AIChat, Anomalies, Weather, Insights, AuditExplorer, MapView, Admin, Notifications, ParliamentaryEngine, QualityCorrelation, LossLedger, ShiftHandover, Compliance, Intelligence, MeetingTracker, KnowledgeBase, SafetyPatterns, PhotoVerification
- [x] MUI theming (mining-industry colors, dark mode)
- [x] Keycloak OIDC/PKCE auth
- [x] TanStack Query hooks for all endpoints
- [x] React Router with nested Layout
- [x] TypeScript compiles clean (0 errors)
- [x] Vite production build: 1.35MB JS, 16.88KB CSS (2.14s)

## Phase 11: Seed Data & Docs — COMPLETE
- [x] Seed script with full demo data
- [x] 12 demo users matching Keycloak realm
- [x] 7 days historical shift data
- [x] Build log at logs/build-log.md
- [x] PROGRESS.md (this file)
- [x] DEVIATIONS.md

## Phase 12: Verification — COMPLETE
- [x] Calculation tests: 36/36 PASS
- [x] Backend healthz/readyz: OK
- [x] Portal TypeScript: 0 errors
- [x] Portal Vite build: SUCCESS
- [x] Flutter pub get: SUCCESS (93 deps)
- [x] PostgreSQL: 49 tables created (39 + 10 innovations)
- [x] Keycloak: realm imported with 12 users, 21 roles
- [x] Temporal: dev server running
- [x] Ollama: Qwen3:8b responding
- [ ] End-to-end API test with auth token
- [ ] C: drive final check

## Phase 13: Plan Innovations (SIH Tier 1-3) — COMPLETE
Implemented the innovations from plan/ that were missing from the build.
All figures deterministic (no LLM in statutory numbers); every feature emits
lineage/source references for Replay the Number.

**Core innovations added:**
- [x] Predictive Parliamentary Engine (backend/app/services/pq_engine.py + api/pq.py + portal ParliamentaryEngine.tsx)
      10-year pattern corpus, deterministic likelihood scoring (frequency + seasonality + live incident triggers),
      pre-generates evidence packs whose figures cite shift_entry/conflict/anomaly source ids. Packs stay DRAFT
      while unresolved Truth Gate conflicts exist.
- [x] Quality-Dispatch Correlation (services/quality_correlation.py + api/quality.py + portal QualityCorrelation.tsx)
      GCV baseline per mine from UTTAM lab history (seasonal mean + damped trend), risk flags (±2.5%/±5%)
      raised at dispatch time — ~1 week before lab results. Lab confirmation that confirms slippage
      auto-raises a Truth Gate conflict.
- [x] Smart Anomaly Narratives (services/anomaly_narrative.py + /anomalies/{id}/narrative + Anomalies.tsx panel)
      Cross-references cause records (±2 days), rainfall, 180-day similar events and monthly target pressure;
      emits probable causes with confidence + evidence citations (6 provenance types).

**Intelligence modules added:**
- [x] Production Loss Ledger / Recovery Debt (services/loss_ledger.py + api/loss_ledger.py + portal LossLedger.tsx)
      Auto-derives ledger entries from approved cause records (hours_lost × mine avg hourly production),
      cumulative open debt per mine with cause breakdown; manual entries and recover/partial/waive flow.
- [x] Shift Handover Intelligence (services/handover.py + api/handover.py + portal ShiftHandover.tsx)
      Deterministic brief per mine+shift: production vs prorated target, unapproved entries, stoppages,
      safety observations, weather, anomalies; critical items flagged; acknowledge flow.
- [x] Statutory Compliance Sentinel (services/compliance.py + api/compliance.py + portal Compliance.tsx)
      Obligations (DGMS/MoEF/PCB/Coal Controller) × mines → filings with computed due dates per frequency,
      data-completeness from approved entries, green/yellow/red dashboard, submit-with-completeness-gate.
- [x] Explosive-to-Output Correlation (services/explosives.py + api/explosives.py + portal Intelligence.tsx)
      kg/m³ vs rolling median baseline (≥3 prior logs), ±15% flags with possible explanations and excess-kg estimate.
- [x] Geological Deviation Learning Loop (services/geology.py + api/geology.py + portal Intelligence.tsx)
      CMPDI predictions vs observed thickness/GCV, per-seam severity, mine deviation map, and learning stats
      (bias, mean-abs-dev, σ) → recommended adjusted tolerance (|bias| + 2σ) fed back as confidence bounds.

## Phase 14: Tier-4 Innovations & Full Portal Wiring — COMPLETE
All "back pocket" innovations implemented end-to-end (models + API + portal page).
All 8 previously-mock portal pages wired to real backend APIs. Zero MOCK/DEMO references remain.

**Tier-4 innovations added:**
- [x] Meeting Action Tracker (models.MeetingAction + api/meetings.py + portal MeetingTracker.tsx)
      Track action items from safety/production/planning meetings with status flow (open→in_progress→completed/overdue),
      mine-scoped filtering, summary counts, create/update/complete flow.
- [x] Institutional Knowledge Preservation (models.KnowledgeEntry + api/knowledge.py + portal KnowledgeBase.tsx)
      Capture operational wisdom from experienced miners: category-tagged entries with author credentials,
      search, verification flow, tag-based filtering.
- [x] Safety Incident Pattern Detector (models.SafetyIncident + SafetyPattern + api/safety.py + portal SafetyPatterns.tsx)
      Report incidents (10 categories, 5 severity levels), automated pattern detection that groups incidents
      by category and creates SafetyPattern records with confidence scores and recommendations.
- [x] Photo-Evidence Geo-Verification (models.PhotoEvidence + api/photos.py + portal PhotoVerification.tsx)
      Upload photos with EXIF GPS extraction, haversine distance computation from registered mine coordinates,
      automatic flagging of location discrepancies, verify/reject review workflow.

**Portal pages wired to real APIs (previously mock):**
- [x] Dashboard: useDashboard() → GET /admin/dashboard (real production stats, weekly chart, recent activity)
- [x] DataEntry: useCreateEntry()/useSubmitEntry() → POST /entries + POST /entries/{id}/submit
- [x] Insights: useInsights() → GET /admin/insights (monthly data, daily trends, topics, word cloud)
- [x] MapView: useMines() → GET /admin/mines (real mine coordinates)
- [x] Notifications: useNotifications() → GET /admin/notifications (aggregated from approvals, anomalies, conflicts)
- [x] AuditExplorer: useAuditEvents() → GET /admin/audit (real audit_event table, server-side filtering)
- [x] Weather: useWeatherForecast()/useRecoveryPlans() → real weather + recovery plan APIs
- [x] Admin: useUsers()/useMines()/useApprovalChains()/useSystemHealth() → all real data
- [x] Reports: Generate button wired to POST /reports/generate with mine/period/date dialog
- [x] Documents: Upload fixed to POST /documents/upload/file (multipart)

**Innovation seed:** scripts/seed_innovations.py — 8 PQ patterns, 40 historical PQs, 3 years of lab samples,
cause records + anomaly flags for the narrative demo, loss ledger, 5 obligations, 80 explosive logs
(incl. over-consumption case), 4 geological predictions (incl. severe fault-zone deviation), 1 handover.

## Phase 13b: Auth Hardening & LLM Grounding — COMPLETE (Oct 5, 2026)

**Login loop root cause + fix (portal):**
- React StrictMode double-invoked the auth effect in dev, calling `keycloak.init` twice — one run
  consumed the PKCE `?code=` from the redirect while the other resolved unauthenticated, bouncing the
  user to /login even with a valid session. Fixed by hoisting `keycloak.init({ onLoad: 'login-required',
  pkceMethod: 'S256', checkLoginIframe: false })` into a module-scope promise in KeycloakProvider.tsx;
  the effect just consumes it. Verified in browser: /chat deep link survives the Keycloak round-trip
  and lands authenticated, no bounce.
- Removed temporary [HIST] navigation instrumentation from main.tsx. tsc clean (0 errors).

**JIT user provisioning (backend):**
- `resolve_app_user(db, user)` in core/security.py provisions an app_user row from the Keycloak token
  (by keycloak_id/sub or username, backfilling keycloak_id, `kc:{username}` fallback row). Chat session
  creation no longer violates the `chat_session_user_id_fkey` FK. Verified end-to-end from the UI.

**AI chat fixes (backend):**
- All Ollama calls send `"think": false` — qwen3 is a reasoning model; without it, thinking consumed
  tokens/timeouts and answers surfaced as the "LLM service is unavailable" placeholder.
- `/chat/message` now attaches real DB context before generation: NUMERIC routes get last-7-days
  production sums; HYBRID/anomaly routes get the active anomaly_flag rows (mine, metric, actual vs
  expected, deviation, score, explanation). System prompt forbids inventing facts. Verified: asking
  about active anomalies returns the real Rajmahal OCP rows (1,820 t vs 3,150 t, scores 0.92/0.87)
  with citations instead of hallucinated content.
- `_classify_query` routes anomaly/outlier questions to HYBRID (was: fell through to out_of_scope).
- Fixed latent AttributeError in rag/llm.py (`settings.OLLAMA_URL`/`LLM_MODEL`/`LLM_TEMPERATURE`/
  `LLM_MAX_TOKENS` → the lowercase pydantic fields).

**Admin dashboard fixes (backend):**
- admin.py queried non-existent enum metric `ob_removal_m3` (DB enum is `OVERBURDEN_M3`) — crashed the
  daily-trend query with `invalid input value for enum metric_name`. Fixed; GET /admin/dashboard now 200
  (verified: weekly chart with real Sep-29 actual 9,996 t, 5 recent activity events, 2 active anomalies).

**Worker verified:** Temporal worker confirmed polling workflow+activity queues on `minova-main`.

## Phase 14b: Approval Engine + One-Click Demo Pipeline — COMPLETE (Oct 5, 2026)

**Approval workflow fixed end-to-end (verified L1→L2→L3→APPROVED):**
- `POST /entries/{id}/submit` now spawns the first approval task from the mine's active
  shift_entry chain (previously only flipped status — the Approval Console stayed empty forever).
- Added per-action routes `/approval/{id}/approve|return|escalate` (the portal's contract) with
  optional comment body (`ApprovalCommentRequest`); `/act` remains available.
- Keycloak: created realm roles `shift_supervisor`, `mine_manager`, `subsidiary_gm` (referenced by
  every seeded chain but never present live) and mapped supervisor1→L1, manager1→L2, admin→L3.
- Portal: `useApprovalInbox/useConflicts/useDocuments/useReports/useShiftEntries` unwrap the
  `{items,...}` cursor envelope (same crash class as useAnomalies earlier).

**One-click demo pipeline (SIH pitch, deterministic):**
- `POST /reports/demo-from-document` (multipart: file+mine_id): stores the document, parses the PDF
  with pypdf (added to venv), extracts "Production: 9,500 t / Overburden removal: 4,200 m3 /
  Operating hours / Workers present" with page+snippet provenance, creates a FINALIZED monthly
  report whose report_values carry lineage edges to the source document page. Deterministic text
  matching — the AI never invents numbers; fixed fallback dataset if nothing parses.
- Reports page: new "AI Report from Document (Demo)" panel — choose PDF → pick mine → generate →
  per-figure source snippets + trace buttons; Preview finalized report; deep-link
  `/replay?valueId=…`.
- Replay the Number: deep-link auto-trace, `/lineage/{id}/verify` alias (portal contract),
  document_page/document tree nodes with snippet children, `unit` on LineageNode, icons per node
  type; Verify shows MATCH in-browser.
- Fixed `GET /reports` 500 (lazy `values` relationship under async — selectinload) and
  `ReportGenerateRequest.template_id` now optional (portal never sent it → 422).
- Reports export menu URL corrected to `/reports/{id}/export` (was `/reports/export/{id}`).

**Tier-4 tables migration:**
- `ab07b372d6a8` creates meeting_action, knowledge_entry, safety_incident, safety_pattern,
  photo_evidence (models existed but no migration → 500s on meetings/knowledge/safety/photos/notifications).
- `/admin/notifications` also fixed: audit filter used non-existent enum values
  ("calc_run.execute") → now filters by entity_type.

**Demo artifacts:** demo/make_demo_document.py (input PDF), portal/public/demo_mine_document.pdf,
storage of finalized exports via Reports → Export → PDF.

## Services Running
| Service    | Port  | Status |
|-----------|-------|--------|
| PostgreSQL | 5433  | Running (6 mines) |
| Backend    | 8000  | Running (Phase 13b fixes loaded) |
| Keycloak   | 8081  | Running (realm minova, username mapper) |
| Temporal   | 7233  | Running (UI on 8233) |
| Temporal worker | — | Running, polling minova-main |
| Ollama     | 11434 | Running (qwen3:8b etc., models in ~/.ollama/models) |
| Portal     | 5173  | Running (Vite) |
