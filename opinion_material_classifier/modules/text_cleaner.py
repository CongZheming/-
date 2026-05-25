from __future__ import annotations

import re


UI_NOISE_LINES = {
    "点赞",
    "收藏",
    "分享",
    "评论",
    "转发",
    "关注",
    "已关注",
    "展开",
    "收起",
    "全文",
    "查看全文",
    "回复",
    "赞",
    "举报",
}


def clean_text(text: str) -> str:
    """轻量清洗社交媒体文本，保留反讽、谐音、缩写和 emoji 等研究线索。"""
    if not text:
        return ""

    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"https?://\S+|www\.\S+", "", text)

    cleaned_lines = []
    for line in text.split("\n"):
        normalized = re.sub(r"[ \t]+", " ", line).strip()
        if not normalized:
            continue
        if normalized in UI_NOISE_LINES:
            continue
        cleaned_lines.append(normalized)

    return "\n".join(cleaned_lines).strip()
