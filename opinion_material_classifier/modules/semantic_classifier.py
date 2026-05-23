from __future__ import annotations


def classify_with_semantics(text: str) -> dict:
    """Reserved semantic-classification interface for future versions."""
    return {
        "enabled": False,
        "message": "语义相似度分类尚未启用，V1.0 使用规则词典分类。",
        "text_length": len(text or ""),
    }
