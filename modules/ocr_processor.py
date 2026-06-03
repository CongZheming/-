from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class OCRResult:
    text: str
    success: bool
    error: str | None = None
    confidence: float | None = None


@lru_cache(maxsize=1)
def _get_ocr_engine() -> Any:
    from paddleocr import PaddleOCR  # type: ignore

    return PaddleOCR(use_angle_cls=True, lang="ch")


def extract_ocr_result_from_image(image_path: str) -> OCRResult:
    path = Path(image_path)
    if not path.exists():
        return OCRResult(text="", success=False, error=f"图片不存在：{image_path}")

    try:
        ocr = _get_ocr_engine()
    except Exception as exc:
        return OCRResult(text="", success=False, error=f"PaddleOCR 不可用：{exc}")

    try:
        result = ocr.ocr(str(path), cls=True)
    except Exception as exc:
        return OCRResult(text="", success=False, error=f"OCR 识别失败：{exc}")

    lines: list[str] = []
    confidences: list[float] = []
    for page in result or []:
        for item in page or []:
            if len(item) < 2 or not isinstance(item[1], (list, tuple)) or not item[1]:
                continue
            lines.append(str(item[1][0]))
            if len(item[1]) > 1:
                try:
                    confidences.append(float(item[1][1]))
                except (TypeError, ValueError):
                    pass

    text = "\n".join(lines).strip()
    if not text:
        return OCRResult(text="", success=False, error="OCR 未识别出文本", confidence=None)

    confidence = round(sum(confidences) / len(confidences), 3) if confidences else None
    return OCRResult(text=text, success=True, confidence=confidence)


def extract_text_from_image(image_path: str) -> str:
    """Backward-compatible helper for callers that only need text."""
    return extract_ocr_result_from_image(image_path).text
