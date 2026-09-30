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
- [x] 15 pages: Dashboard, DataEntry, ApprovalConsole, Reports, ReplayTheNumber, Conflicts, Documents, AIChat, Anomalies, Weather, Insights, AuditExplorer, MapView, Admin, Notifications
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

## Phase 12: Verification — IN PROGRESS
- [x] Calculation tests: 36/36 PASS
- [x] Backend healthz/readyz: OK
- [x] Portal TypeScript: 0 errors
- [x] Portal Vite build: SUCCESS
- [x] Flutter pub get: SUCCESS (93 deps)
- [x] PostgreSQL: 39 tables created
- [x] Keycloak: realm imported with 12 users, 21 roles
- [x] Temporal: dev server running
- [x] Ollama: Qwen3:8b responding
- [ ] End-to-end API test with auth token
- [ ] C: drive final check

## Services Running
| Service    | Port  | Status |
|-----------|-------|--------|
| PostgreSQL | 5433  | Running |
| Keycloak   | 8081  | Running |
| Temporal   | 7233  | Running |
| Ollama     | 11434 | Running |
| Backend    | 8000  | Running |
