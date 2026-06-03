from __future__ import annotations

import sqlite3
from pathlib import Path

from modules.rule_classifier import KEYWORD_GROUPS, LABEL_OPTIONS
from modules.utils import DATABASE_PATH, PROJECT_ROOT, ensure_dirs, generate_id


def init_database() -> None:
    ensure_dirs()
    schema_path = PROJECT_ROOT / "database" / "schema.sql"
    with sqlite3.connect(DATABASE_PATH) as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.executescript(Path(schema_path).read_text(encoding="utf-8"))
        _migrate_schema(conn)
        _seed_label_dictionary(conn)


def _migrate_schema(conn: sqlite3.Connection) -> None:
    _ensure_column(conn, "classifications", "needs_review", "INTEGER DEFAULT 0")
    _ensure_column(conn, "classifications", "explanation_json", "TEXT")
    _ensure_column(conn, "classifications", "reviewed_time", "TEXT")


def _ensure_column(conn: sqlite3.Connection, table_name: str, column_name: str, definition: str) -> None:
    columns = {row[1] for row in conn.execute(f"PRAGMA table_info({table_name})")}
    if column_name not in columns:
        conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}")


def _keyword_text(label_type: str, label_name: str) -> str:
    keywords = KEYWORD_GROUPS.get(label_type, {}).get(label_name, [])
    normalized = []
    for item in keywords:
        if isinstance(item, dict):
            keyword = str(item.get("keyword", "")).strip()
        else:
            keyword = str(item).strip()
        if keyword:
            normalized.append(keyword)
    return "、".join(normalized)


def _seed_label_dictionary(conn: sqlite3.Connection) -> None:
    for label_type, labels in LABEL_OPTIONS.items():
        for label_name in labels:
            keywords = _keyword_text(label_type, label_name)
            description = f"{label_type} 内置标签：{label_name}"
            existing = conn.execute(
                """
                SELECT label_id
                FROM label_dictionary
                WHERE label_type = ? AND label_name = ?
                """,
                (label_type, label_name),
            ).fetchone()
            if existing:
                conn.execute(
                    """
                    UPDATE label_dictionary
                    SET keywords = ?, description = ?
                    WHERE label_id = ?
                    """,
                    (keywords, description, existing[0]),
                )
                continue

            conn.execute(
                """
                INSERT INTO label_dictionary (label_id, label_type, label_name, keywords, description)
                VALUES (?, ?, ?, ?, ?)
                """,
                (generate_id("label"), label_type, label_name, keywords, description),
            )
