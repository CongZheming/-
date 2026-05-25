from __future__ import annotations

import sqlite3
from pathlib import Path

from modules.rule_classifier import LABEL_OPTIONS
from modules.utils import DATABASE_PATH, PROJECT_ROOT, ensure_dirs, generate_id


def init_database() -> None:
    ensure_dirs()
    schema_path = PROJECT_ROOT / "database" / "schema.sql"
    with sqlite3.connect(DATABASE_PATH) as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.executescript(Path(schema_path).read_text(encoding="utf-8"))
        _seed_label_dictionary(conn)


def _seed_label_dictionary(conn: sqlite3.Connection) -> None:
    managed_types = tuple(LABEL_OPTIONS.keys())
    placeholders = ",".join("?" for _ in managed_types)
    conn.execute(f"DELETE FROM label_dictionary WHERE label_type IN ({placeholders})", managed_types)

    rows = []
    for label_type, labels in LABEL_OPTIONS.items():
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
