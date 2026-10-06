# MINOVA — AI-Powered Mining Reporting & Verification Platform

MINOVA is an end-to-end reporting platform for open-cast coal mines: shift-level
data capture, a deterministic calculation engine, multi-level approval, statutory
report generation (PDF/Excel/DOCX), full number-level lineage ("Replay the Number"),
document intelligence with grounded AI assistance, and operational intelligence
modules — wrapped in a React portal and an offline-first Flutter mobile app.

Built for **Smart India Hackathon 2026** (problem statement **SIH26023**) addressing
Coal India Limited's reporting and verification workflow.

**Core principle:** every statutory number is computed deterministically with
`Decimal` arithmetic and reproducible input hashes. The LLM never calculates
figures — it only narrates and answers from cited, verifiable data.

## Why MINOVA

Mine reporting today is fragmented: shifts record numbers in spreadsheets and
paper logbooks, monthly reports are assembled by hand, discrepancies between
sources surface late (or never), and nobody can answer *"where exactly did this
figure come from?"* once a report reaches headquarters.

MINOVA closes that loop:

- **One source of truth** — every shift entry flows through a deterministic
  calculation engine into daily, weekly, monthly and quarterly rollups.
- **Verification built in** — multi-level approval chains, automatic conflict
  detection between competing values, and a mandatory resolution reason.
- **Traceability to the source** — every number in a report carries lineage back
  to the shift entry, document page, or calculation run that produced it.
- **Grounded AI** — the assistant cites real database rows and uploaded
  documents instead of inventing numbers.

## Feature highlights

### Data capture & aggregation
- Shift production entries (tonnes, overburden m³, operating hours, manpower)
  per mine and bench, with resubmission replacing earlier values.
- Deterministic aggregation: shifts → daily → weekly → monthly → quarterly,
  using `Decimal` with `ROUND_HALF_EVEN` and a recorded input hash per run.
- Target cascade allocation from annual to quarterly with exact-sum rounding.

### Approval & governance ("Truth Gate")
- Configurable approval chains per mine (shift supervisor → mine manager → GM)
  driven by Keycloak realm roles.
- Approve / return / escalate actions with comments; unapproved values never
  reach statutory reports.
- Conflict detection across sources with side-by-side comparison in the portal.

### Reporting
- Monthly production reports and bulletins with Coal India–style cover,
  metrics tables and signatures, exportable to **PDF, Excel and DOCX**.
- **Generate Report from Document** — upload a mine document PDF; the platform
  extracts production figures (inline text *and* table layouts) with page-level
  provenance and produces a finalized report whose values trace to source pages.

### Replay the Number (lineage & audit)
- Lineage tree for any figure: shift entries, calculation runs, document pages
  (with text snippets), approvals and rollups as typed nodes.
- Verify recomputes a value from its inputs and reports MATCH/MISMATCH.
- Hash-chained audit trail of every state-changing event, explorable in the
  Audit Explorer with server-side filtering.

### Document intelligence
- Document upload, OCR (PaddleOCR), chunking and BGE-M3 embeddings with hybrid
  keyword + vector retrieval (application-layer cosine similarity fallback).
- Staging workflow for extracted values before they enter reports.

### AI assistance
- Ollama-hosted LLM (Qwen3) behind a query router (numeric / descriptive /
  hybrid) with hard grounding: production questions are answered from live
  aggregates, anomaly questions from active flag rows — always with citations.

### Operational intelligence modules
- **Predictive Parliamentary Engine** — 10-year pattern corpus with
  deterministic likelihood scoring and pre-generated evidence packs.
- **Quality–Dispatch Correlation** — GCV baseline per mine with risk flags
  raised before lab confirmations.
- **Anomaly narratives** — IsolationForest detection plus cross-referenced
  causes, rainfall and similar historical events.
- **Production Loss Ledger** — recovery debt derived from approved cause
  records with recover/partial/waive flow.
- **Shift Handover briefs, Statutory Compliance Sentinel, Explosive-to-Output
  correlation, Geological Deviation learning loop.**
- **Tier-4 modules:** meeting action tracker, institutional knowledge base,
  safety incident pattern detection, photo geo-verification (EXIF GPS vs.
  registered mine coordinates).

### Mobile
- Flutter app (Android + Windows) with offline-first SQLite storage, secure
  token storage, push/pull sync and conflict detection.

## Architecture

| Layer | Technology |
|---|---|
| Portal | React 19, TypeScript, MUI v7, TanStack Query/Router, Keycloak JS (OIDC + PKCE), Vite |
| API | FastAPI (Python), Pydantic v2, structlog |
| Database | PostgreSQL 16 (SQLAlchemy 2.0 async, Alembic migrations) |
| Workflow | Temporal (approval, rollup, ingestion workflows + worker) |
| Identity | Keycloak 26 (realm import, role-based approval levels, JIT user provisioning) |
| Documents | PaddleOCR, BGE-M3 embeddings, hybrid retrieval, pypdf extraction |
| AI | Ollama (Qwen3) — grounded chat with citations, no invented numbers |
| Reports | ReportLab (PDF), openpyxl (Excel), python-docx (DOCX) |
| Mobile | Flutter (Android + Windows), offline-first SQLite sync |
| Storage | S3-compatible (MinIO) with filesystem fallback |

```
Portal (5173) ──► API (8000) ──► PostgreSQL (5433)
                     │  ▲
                     ▼  │
 Keycloak (8081)   Temporal (7233) ◄── Worker (workflows + activities)
                     │
                     ▼
              Ollama (11434) + OCR/embedding services
```

## API surface

All endpoints are versioned under `/api/v1`. Main groups:

| Group | Purpose |
|---|---|
| `/entries` | Shift entry CRUD, submit for approval |
| `/approval` | Inbox, approve / return / escalate with comments |
| `/conflicts` | Conflict list, detail, resolve (mandatory reason) |
| `/lineage` | Lineage tree, `/verify` recomputation, replay |
| `/reports` | Generate, list, preview, export (PDF/Excel/DOCX), generate-from-document |
| `/documents` | Upload (multipart), OCR ingestion, staging review, search |
| `/chat` | Grounded assistant with citations |
| `/anomalies` | Detection, narratives, recovery plans |
| `/weather` | Forecast, weather impact, recovery plans |
| `/pq`, `/quality`, `/compliance`, `/safety`, `/photos`, `/meetings`, `/knowledge`, `/loss-ledger`, `/handover`, `/explosives`, `/geology` | Intelligence & governance modules |
| `/admin` | Users, mines, approval chains, dashboard, audit, notifications, system health |
| `/sync` | Mobile offline sync |

Interactive docs: FastAPI serves OpenAPI at `/docs` when the backend runs.

## Repository layout

```
backend/
  app/api/          FastAPI routers (one per domain group above)
  app/domain/       SQLAlchemy 2.0 models (38 tables) + enums
  app/services/     Calculation engine, report engine, domain services
  app/workflows/    Temporal workflows, activities and worker
  app/rag/          Embedder, retriever, query router, LLM client
  app/ml/           Anomaly detection (IsolationForest + z-score fallback)
  migrations/       Alembic migrations (49 tables at head)
  scripts/          Seed scripts (base data, innovations, tier-4)
  tests/            Calculation engine test suite (36 tests)
portal/
  src/pages/        25 feature pages (Dashboard … Photo Verification)
  src/api/          Typed API client + TanStack Query hooks
mobile/             Flutter app (lib/, android/, windows/)
infra/              docker-compose reference, Keycloak realm, portable-service scripts
samples/            Sample mine documents + generator script
seed/               Seed datasets
docs/               Additional documentation
```

## Getting started

Prerequisites: Python 3.11+, Node.js 20+, Flutter 3.x, PostgreSQL 16, Keycloak 26,
Temporal, and Ollama. `infra/native-services.ps1 start` boots the portable service
stack on Windows; `infra/docker-compose.yml` documents the container equivalent.

```bash
# 1. Infrastructure (Windows portable stack, or docker compose -f infra/docker-compose.yml up)
powershell -File infra/native-services.ps1 start

# 2. Backend
cd backend
python -m venv .venv && .venv/Scripts/activate     # Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env                             # adjust DATABASE_URL etc. if needed
alembic upgrade head
python scripts/seed.py                             # demo org, mines, users, 7 days of shifts
python scripts/seed_innovations.py                 # intelligence-module demo data
python scripts/seed_tier4.py                       # tier-4 module demo data

# 3. Temporal worker (separate shell)
cd backend
python -m app.workflows.worker

# 4. API
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000

# 5. Portal
cd portal
npm install
npm run dev                                        # http://localhost:5173

# 6. Mobile (optional)
cd mobile
flutter pub get
flutter run
```

### Demo walkthrough

1. Sign in at the portal (`supervisor1 / pass123` — shift supervisor; `manager1 /
   pass123` — mine manager; `admin / admin123` — GM). These are development-only
   users seeded in the bundled Keycloak realm.
2. **Data Entry** — record shift production and overburden removal; submit for
   approval.
3. **Approvals** — approve through the configured chain (supervisor → manager →
   GM). Approved values roll up into daily/period totals.
4. **Reports** — generate monthly reports and export to PDF/Excel/DOCX.
5. **Documents → Generate Report from Document** — upload a mine document PDF
   (see `samples/`); the platform extracts production figures with page-level
   provenance and produces a finalized report whose every value traces back to
   the source page.
6. **Replay the Number** — trace any figure to its origin, verify recomputation,
   and inspect the full lineage tree.
7. **Assistant** — ask production/anomaly questions; answers cite live database
   rows and documents rather than inventing numbers.

## Quality & verification

```bash
cd backend && pytest tests -q          # calculation engine: 36/36 pass
cd portal && npm run build             # tsc clean + production bundle
```

Continuous Integration runs both jobs on every push and PR to `main`
(see [.github/workflows/ci.yml](.github/workflows/ci.yml)).

## Documentation

- [PROGRESS.md](PROGRESS.md) — phase-by-phase build record and verification results.
- [DEVIATIONS.md](DEVIATIONS.md) — documented engineering trade-offs (storage
  adapter, geometry handling, vector search) and the production upgrade path for each.
- [model-manifest.md](model-manifest.md) — models used (LLM, embeddings, OCR)
  and configuration.
- [backend/.env.example](backend/.env.example) — every configuration variable.

## Production notes

- Swap the filesystem storage adapter for a managed S3-compatible service
  (interface-compatible; see `DEVIATIONS.md`).
- Enable PostGIS and pgvector on a full PostgreSQL install for spatial indexes
  and ANN vector search (application-layer fallbacks are in place).
- Configure TLS, strong secrets, and externalized Keycloak/Postgres credentials
  via environment variables before any real deployment.
- All seed/demo figures are synthetic and clearly marked; no real CIL
  production data is included.

## License

Proprietary — © 2026 Team TECH TITANS. All rights reserved.
