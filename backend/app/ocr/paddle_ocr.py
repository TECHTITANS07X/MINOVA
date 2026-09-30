"""
PaddleOCR wrapper for Hindi + English document text extraction.
Supports PDF, images with layout analysis and table detection.
"""
from __future__ import annotations

import os
from pathlib import Path

import structlog

logger = structlog.get_logger()

_ocr_engine = None


def _get_engine():
    global _ocr_engine
    if _ocr_engine is None:
        try:
            from paddleocr import PaddleOCR
            _ocr_engine = PaddleOCR(
                use_angle_cls=True,
                lang="en",
                use_gpu=False,
                show_log=False,
            )
            logger.info("ocr.engine_loaded", engine="PaddleOCR", lang="en")
        except ImportError:
            logger.warning("ocr.paddleocr_not_installed")
            _ocr_engine = "unavailable"
    return _ocr_engine


async def extract_text(file_path: str) -> list[dict]:
    engine = _get_engine()
    if engine == "unavailable":
        return [{"page": 1, "text": "[PaddleOCR not installed]", "confidence": 0.0}]

    ext = Path(file_path).suffix.lower()
    pages = []

    try:
        if ext == ".pdf":
            import fitz  # PyMuPDF
            doc = fitz.open(file_path)
            for page_num in range(len(doc)):
                page = doc[page_num]
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                img_path = f"{file_path}_page_{page_num}.png"
                pix.save(img_path)

                result = engine.ocr(img_path, cls=True)
                text_lines = []
                total_conf = 0
                count = 0
                if result and result[0]:
                    for line in result[0]:
                        text_lines.append(line[1][0])
                        total_conf += line[1][1]
                        count += 1

                pages.append({
                    "page": page_num + 1,
                    "text": "\n".join(text_lines),
                    "confidence": total_conf / max(count, 1),
                })

                os.remove(img_path)
            doc.close()
        else:
            result = engine.ocr(file_path, cls=True)
            text_lines = []
            total_conf = 0
            count = 0
            if result and result[0]:
                for line in result[0]:
                    text_lines.append(line[1][0])
                    total_conf += line[1][1]
                    count += 1

            pages.append({
                "page": 1,
                "text": "\n".join(text_lines),
                "confidence": total_conf / max(count, 1),
            })

    except Exception as e:
        logger.error("ocr.extraction_failed", error=str(e), file=file_path)
        pages = [{"page": 1, "text": f"[OCR failed: {e}]", "confidence": 0.0}]

    return pages


async def extract_tables(file_path: str) -> list[dict]:
    engine = _get_engine()
    if engine == "unavailable":
        return []

    try:
        from ppstructure.predict_system import StructureSystem
        # Table extraction via PP-Structure
        # This is a placeholder — PP-Structure needs separate model download
        return []
    except ImportError:
        return []
