from __future__ import annotations


def classify_with_semantics(text: str) -> dict:
    """预留语义相似度分类接口，V1.0 默认使用规则词典分类。"""
    return {
        "enabled": False,
        "message": "语义相似度分类尚未启用，V1.0 使用规则词典分类。",
        "text_length": len(text or ""),
    }
