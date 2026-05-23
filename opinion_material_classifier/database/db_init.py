from __future__ import annotations

import sqlite3
from pathlib import Path

from modules.utils import DATABASE_PATH, PROJECT_ROOT, ensure_dirs, generate_id


LABEL_DICTIONARY = {
    "relevance_label": ["强相关", "中等相关", "弱相关", "无关"],
    "content_type": ["政策讨论", "专家质疑", "个人经验", "情绪宣泄", "反讽调侃", "理性分析", "平台审核规避", "二次创作", "媒体传播", "其他"],
    "emotion_label": ["支持", "反对", "焦虑", "愤怒", "无奈", "嘲讽", "调侃", "恐惧", "理性分析", "中立", "复杂 / 混合"],
    "frame_label": ["生育成本", "女性身体风险", "性别不平等", "专家权威质疑", "政策信任", "政策质疑", "婚恋压力", "家庭责任", "职场歧视", "育儿资源", "人口焦虑", "代际观念", "媒体标题党", "平台审核规避", "科学研究方法质疑", "个人经验叙事", "其他"],
    "platform_role": ["话题定义", "热度扩散", "情绪发酵", "经验分享", "理性沉淀", "二次创作", "梗文化生成", "政策解释", "反讽抵抗", "审核规避", "其他"],
    "reshape_type": ["标题化", "情绪化", "经验化", "性别化", "娱乐化", "专业化", "政策化", "道德化", "反讽化", "审核规避化", "其他"],
}


def init_database() -> None:
    ensure_dirs()
    schema_path = PROJECT_ROOT / "database" / "schema.sql"
    with sqlite3.connect(DATABASE_PATH) as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.executescript(Path(schema_path).read_text(encoding="utf-8"))
        _seed_label_dictionary(conn)


def _seed_label_dictionary(conn: sqlite3.Connection) -> None:
    existing_count = conn.execute("SELECT COUNT(*) FROM label_dictionary").fetchone()[0]
    if existing_count:
        return

    rows = []
    for label_type, labels in LABEL_DICTIONARY.items():
        for label_name in labels:
            rows.append(
                (
                    generate_id("label"),
                    label_type,
                    label_name,
                    "",
                    f"{label_type} 内置标签：{label_name}",
                )
            )
    conn.executemany(
        """
        INSERT INTO label_dictionary (label_id, label_type, label_name, keywords, description)
        VALUES (?, ?, ?, ?, ?)
        """,
        rows,
    )
