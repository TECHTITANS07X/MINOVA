# MINOVA Model Manifest

| Model | Purpose | Location | Size | Status |
|-------|---------|----------|------|--------|
| Qwen3:8b (Q4_K_M) | Grounded descriptions, RAG, AI assistant | Ollama (`D:\games and stuff\Opus - build\models\ollama`) | 5.2 GB | Ready |
| Qwen3:1.7b | Test/fallback model | Ollama (same path) | 1.4 GB | Ready |
| BGE-M3 (BAAI/bge-m3) | 1024-dim embeddings for hybrid retrieval | HuggingFace (`D:\games and stuff\Opus - build\models\huggingface`) | ~2.2 GB | Downloading |
| PaddleOCR (en) | English text + table extraction | PaddlePaddle models cache | ~150 MB | Pending |
| PaddleOCR (hi) | Hindi/Devanagari text extraction | PaddlePaddle models cache | ~150 MB | Pending |

## Ollama Configuration
- Endpoint: `http://localhost:11434`
- Models directory: `D:\games and stuff\Opus - build\models\ollama`
- VRAM: RTX 3050 6GB — Qwen3:8b Q4 fits within budget

## Embedding Configuration
- Model: BAAI/bge-m3
- Dimensions: 1024
- Index: pgvector HNSW (cosine)
- Retrieval: Reciprocal Rank Fusion (dense + keyword via pg_trgm)

## OCR Configuration
- Engine: PaddleOCR
- Languages: English (en), Hindi/Devanagari (hi)
- Features: Layout analysis, table extraction, text detection + recognition
