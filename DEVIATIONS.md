# MINOVA Build Deviations

Documented deviations from the original build specification.

## 1. MinIO S3 Storage → Filesystem Adapter
**Reason**: MinIO open-source project archived. All download URLs (dl.min.io) return HTTP 410 Gone as of 2026-09-30.
**Mitigation**: Filesystem-backed StorageService with S3-compatible API interface. Transparent fallback — code tries MinIO first, falls back to filesystem. Same bucket/key abstraction, presigned URLs route to internal API endpoints.
**Impact**: No functional difference for demo. Production would need commercial MinIO or alternative S3-compatible storage (e.g., Cloudflare R2, AWS S3).

## 2. PostGIS → GeoJSON in JSON Column
**Reason**: EDB portable PostgreSQL zip does not include PostGIS extension. Prebuilt PostGIS DLLs for PG 16 on Windows not available via simple download.
**Mitigation**: Bench geometry stored as GeoJSON in a JSON column with `comment="GeoJSON polygon, srid=4326"`. Spatial queries done in application layer. Leaflet renders GeoJSON natively.
**Impact**: No spatial index (ST_Within, ST_DWithin not available). Acceptable for demo with 18 benches. Production should use PostGIS-enabled PostgreSQL.

## 3. pgvector → NumPy Cosine Similarity
**Reason**: pgvector extension requires compiled C library not bundled with portable PG. Prebuilt pgvector.dll for PG 16/Windows returned 404.
**Mitigation**: Embeddings stored as JSON arrays (1024-dim float[]). Vector search performed in Python using numpy dot product + norm. Results are equivalent; just done in application memory instead of database.
**Impact**: Vector search scales linearly O(n) instead of ANN O(log n). Fine for <100K chunks in demo. Production should use pgvector with HNSW index.

## 4. PostgreSQL Port 5432 → 5433
**Reason**: System PostgreSQL already running on port 5432 with unknown credentials.
**Mitigation**: Portable PG configured on port 5433. All configs (.env, alembic.ini, scripts) updated to use 5433.
**Impact**: None — port is configurable.

## 5. ML Models Lazy-Loaded
**Reason**: BGE-M3 (~2GB) and PaddleOCR models (~1GB) are large downloads. Loaded on first use to avoid blocking startup.
**Mitigation**: `_get_ocr()` and `_get_embed_model()` pattern — singleton lazy initialization with ImportError fallback.
**Impact**: First OCR/embedding request has latency. Subsequent requests use cached model. Zero-vector fallback if models unavailable.

## 6. SQLCipher → Standard SQLite (Flutter)
**Reason**: SQLCipher requires native compilation setup. Standard sqflite package used for offline storage.
**Mitigation**: Using sqflite with standard SQLite. Sensitive tokens stored via flutter_secure_storage (OS keychain).
**Impact**: Local database not encrypted at rest. Acceptable for demo. Production should use sqflite_sqlcipher package.

## 7. Docker Compose → Native Services
**Reason**: Docker Desktop not installed. WSL2 Ubuntu available but stopped.
**Mitigation**: All services run natively: portable PostgreSQL, Keycloak standalone, Temporal CLI dev-server, Ollama system install.
**Impact**: No container isolation. Services managed via PowerShell scripts. Functionally equivalent for development.
