from __future__ import annotations


def extract_text_from_image(image_path: str) -> str:
    """Try PaddleOCR first. Return empty text if OCR dependency is unavailable."""
    try:
        from paddleocr import PaddleOCR  # type: ignore
    except Exception:
        return ""

    try:
        ocr = PaddleOCR(use_angle_cls=True, lang="ch")
        result = ocr.ocr(image_path, cls=True)
    except Exception:
        return ""

    lines: list[str] = []
    for page in result or []:
        for item in page or []:
            if len(item) >= 2 and isinstance(item[1], (list, tuple)) and item[1]:
                lines.append(str(item[1][0]))
    return "\n".join(lines).strip()
