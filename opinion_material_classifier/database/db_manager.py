from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Dict

import pandas as pd

from database.db_init import init_database as _init_database
from modules.utils import DATABASE_PATH, SCREENSHOTS_DIR


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_database() -> None:
    _init_database()


def insert_material(material_dict: Dict[str, Any]) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO materials (
                material_id, platform, source_type, keyword, url, raw_text,
                clean_text, screenshot_path, input_method, upload_time, researcher_note
            )
            VALUES (
                :material_id, :platform, :source_type, :keyword, :url, :raw_text,
                :clean_text, :screenshot_path, :input_method, :upload_time, :researcher_note
            )
            """,
            material_dict,
        )


def insert_classification(classification_dict: Dict[str, Any]) -> None:
    defaults = {
        "is_human_checked": 0,
        "final_relevance_label": classification_dict.get("relevance_label"),
        "final_content_type": classification_dict.get("content_type"),
        "final_emotion_label": classification_dict.get("emotion_label"),
        "final_frame_label": classification_dict.get("frame_label"),
        "final_platform_role": classification_dict.get("platform_role"),
        "final_reshape_type": classification_dict.get("reshape_type"),
    }
    payload = {**defaults, **classification_dict}
    with get_connection() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO classifications (
                classification_id, material_id, relevance_label, content_type,
                emotion_label, frame_label, platform_role, reshape_type, confidence,
                is_human_checked, final_relevance_label, final_content_type,
                final_emotion_label, final_frame_label, final_platform_role,
                final_reshape_type, classified_time
            )
            VALUES (
                :classification_id, :material_id, :relevance_label, :content_type,
                :emotion_label, :frame_label, :platform_role, :reshape_type, :confidence,
                :is_human_checked, :final_relevance_label, :final_content_type,
                :final_emotion_label, :final_frame_label, :final_platform_role,
                :final_reshape_type, :classified_time
            )
            """,
            payload,
        )


def insert_ocr_result(ocr_dict: Dict[str, Any]) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO ocr_results (
                ocr_id, material_id, original_image_path, recognized_text, corrected_text, ocr_time
            )
            VALUES (
                :ocr_id, :material_id, :original_image_path, :recognized_text, :corrected_text, :ocr_time
            )
            """,
            ocr_dict,
        )


def get_latest_unclassified_material() -> dict | None:
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT m.*
            FROM materials m
            LEFT JOIN classifications c ON m.material_id = c.material_id
            WHERE c.material_id IS NULL
            ORDER BY m.upload_time DESC
            LIMIT 1
            """
        ).fetchone()
    return dict(row) if row else None


def get_unchecked_classifications() -> pd.DataFrame:
    query = """
        SELECT
            c.*,
            m.platform,
            m.source_type,
            m.keyword,
            m.url,
            m.raw_text,
            m.clean_text,
            m.researcher_note
        FROM classifications c
        JOIN materials m ON c.material_id = m.material_id
        WHERE c.is_human_checked = 0
        ORDER BY c.classified_time DESC
    """
    with get_connection() as conn:
        return pd.read_sql_query(query, conn)


def update_human_review(classification_id: str, final_labels: Dict[str, str]) -> None:
    payload = {"classification_id": classification_id, **final_labels}
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE classifications
            SET
                is_human_checked = 1,
                final_relevance_label = :final_relevance_label,
                final_content_type = :final_content_type,
                final_emotion_label = :final_emotion_label,
                final_frame_label = :final_frame_label,
                final_platform_role = :final_platform_role,
                final_reshape_type = :final_reshape_type
            WHERE classification_id = :classification_id
            """,
            payload,
        )


def load_materials() -> pd.DataFrame:
    with get_connection() as conn:
        return pd.read_sql_query("SELECT * FROM materials ORDER BY upload_time DESC", conn)


def load_classifications() -> pd.DataFrame:
    with get_connection() as conn:
        return pd.read_sql_query("SELECT * FROM classifications ORDER BY classified_time DESC", conn)


def delete_classification(classification_id: str) -> int:
    with get_connection() as conn:
        cursor = conn.execute(
            "DELETE FROM classifications WHERE classification_id = ?",
            (classification_id,),
        )
        return cursor.rowcount


def delete_material(material_id: str, delete_screenshot_file: bool = False) -> dict:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT screenshot_path FROM materials WHERE material_id = ?",
            (material_id,),
        ).fetchone()
        if row is None:
            return {"deleted": False, "message": "material not found"}

        screenshot_path = row["screenshot_path"]
        conn.execute("DELETE FROM ocr_results WHERE material_id = ?", (material_id,))
        conn.execute("DELETE FROM classifications WHERE material_id = ?", (material_id,))
        conn.execute("DELETE FROM materials WHERE material_id = ?", (material_id,))

    removed_file = False
    if delete_screenshot_file and screenshot_path:
        path = Path(screenshot_path)
        try:
            resolved_path = path.resolve()
            screenshots_root = SCREENSHOTS_DIR.resolve()
            if resolved_path.is_file() and screenshots_root in resolved_path.parents:
                resolved_path.unlink()
                removed_file = True
        except OSError:
            removed_file = False

    return {"deleted": True, "screenshot_file_removed": removed_file}


def load_joined_dataset() -> pd.DataFrame:
    query = """
        SELECT
            m.material_id,
            m.platform,
            m.source_type,
            m.keyword,
            m.url,
            m.raw_text,
            m.clean_text,
            m.screenshot_path,
            m.input_method,
            m.upload_time,
            m.researcher_note,
            c.classification_id,
            c.relevance_label,
            c.content_type,
            c.emotion_label,
            c.frame_label,
            c.platform_role,
            c.reshape_type,
            c.confidence,
            c.is_human_checked,
            COALESCE(c.final_relevance_label, c.relevance_label) AS final_relevance_label,
            COALESCE(c.final_content_type, c.content_type) AS final_content_type,
            COALESCE(c.final_emotion_label, c.emotion_label) AS final_emotion_label,
            COALESCE(c.final_frame_label, c.frame_label) AS final_frame_label,
            COALESCE(c.final_platform_role, c.platform_role) AS final_platform_role,
            COALESCE(c.final_reshape_type, c.reshape_type) AS final_reshape_type,
            c.classified_time
        FROM materials m
        LEFT JOIN classifications c ON m.material_id = c.material_id
        ORDER BY m.upload_time DESC
    """
    with get_connection() as conn:
        return pd.read_sql_query(query, conn)


def export_all() -> dict:
    from modules.exporter import (
        export_classifications_to_excel,
        export_materials_to_excel,
        export_reviewed_dataset,
        export_texts_for_cluster,
    )

    return {
        "materials": export_materials_to_excel(),
        "classifications": export_classifications_to_excel(),
        "reviewed_dataset": export_reviewed_dataset(),
        "texts_for_cluster": export_texts_for_cluster(),
    }
