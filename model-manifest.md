# MINOVA Model Manifest

| Model | Purpose | Location | Size | Status |
|-------|---------|----------|------|--------|
| Qwen3:8b (Q4_K_M) | Grounded descriptions, RAG, AI assistant | Ollama model store (`OLLAMA_MODELS`) | 5.2 GB | Ready |
| Qwen3:1.7b | Test/fallback model | Ollama (same path) | 1.4 GB | Ready |
| BGE-M3 (BAAI/bge-m3) | 1024-dim embeddings for hybrid retrieval | HuggingFace cache (`HF_HOME`) | ~2.2 GB | Lazy-loaded |
| PaddleOCR (en) | English text + table extraction | PaddlePaddle models cache | ~150 MB | Pending |
| PaddleOCR (hi) | Hindi/Devanagari text extraction | PaddlePaddle models cache | ~150 MB | Pending |

**Note (innovation features):** the 8 plan innovations added in Phase 13 (PQ engine, quality correlation,
loss ledger, handover, compliance sentinel, explosives, geology loop, anomaly narratives) are deliberately
**deterministic-only** — they use fixed formulas/aggregations over stored data, NOT any model. This is the
"LLM never calculates statutory numbers" safety principle from the plan. The LLM (Qwen3:8b) remains available
for narrative polish via the existing chat/RAG stack.

## Ollama Configuration
- Endpoint: configurable via `OLLAMA_URL` (default `http://localhost:11434`)
- Models directory: configurable via `OLLAMA_MODELS` (Ollama default `~/.ollama/models`)
- Reference hardware: consumer GPU with 6 GB VRAM fits Qwen3:8b Q4_K_M within budget

## Embedding Configuration
- Model: BAAI/bge-m3
- Dimensions: 1024
- Index: pgvector HNSW (cosine)
- Retrieval: Reciprocal Rank Fusion (dense + keyword via pg_trgm)

## OCR Configuration
- Engine: PaddleOCR
- Languages: English (en), Hindi/Devanagari (hi)
- Features: Layout analysis, table extraction, text detection + recognition
