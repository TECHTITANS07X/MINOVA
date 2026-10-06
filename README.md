# MINOVA — AI-Powered Mining Reporting & Verification Platform

MINOVA is an end-to-end reporting platform for open-cast coal mines: shift-level
data capture, a deterministic calculation engine, multi-level approval, statutory
report generation (PDF/Excel/DOCX), full number-level lineage ("Replay the Number"),
document intelligence with grounded AI assistance, and operational intelligence
modules — wrapped in a React portal and an offline-first Flutter mobile app.

**Core principle:** every statutory number is computed deterministically with
`Decimal` arithmetic and reproducible hashes. The LLM never calculates figures —
it only narrates and answers from cited, verifiable data.

## Architecture

| Layer | Technology |
|---|---|
| Portal | React 19, TypeScript, MUI v7, TanStack Query/Router, Keycloak JS (OIDC + PKCE), Vite |
| API | FastAPI (Python), Pydantic v2, structlog |
| Database | PostgreSQL 16 (SQLAlchemy 2.0 async, Alembic) |
| Workflow | Temporal (approval, rollup, ingestion workflows + worker) |
| Identity | Keycloak 26 (realm import, role-based approval levels) |
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

## Repository layout

```
backend/     FastAPI app, domain models, services, workflows, migrations, tests
portal/      React web portal (25 feature pages)
mobile/      Flutter app (Android + Windows)
infra/       docker-compose reference, Keycloak realm, portable-service scripts
samples/     Sample mine documents and the generator script (samples/make_sample_documents.py)
scripts/     Repository-level helpers
seed/        Seed datasets
```

## Quickstart (development)

Prerequisites: Python 3.11+, Node.js 20+, Flutter 3.x, a running PostgreSQL 16,
Keycloak 26, Temporal, and Ollama. `infra/native-services.ps1 start` boots the
portable service stack on Windows; `infra/docker-compose.yml` documents the
container equivalent.

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

## Demo walkthrough

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

- `PROGRESS.md` — phase-by-phase build record and verification results.
- `DEVIATIONS.md` — documented engineering trade-offs (storage adapter, geometry
  handling, vector search) and the production upgrades for each.
- `model-manifest.md` — models used (LLM, embeddings, OCR) and configuration.

## Production notes

- Swap the filesystem storage adapter for a managed S3-compatible service
  (interface-compatible; see `DEVIATIONS.md`).
- Enable PostGIS and pgvector on a full PostgreSQL install for spatial indexes
  and ANN vector search (application-layer fallbacks are in place).
- Configure TLS, strong secrets, and externalized Keycloak/Postgres credentials
  via environment variables before any real deployment.

## License

Proprietary — © 2026 Team TECH TITANS. All rights reserved.
