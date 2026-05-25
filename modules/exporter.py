from __future__ import annotations

import pandas as pd

from modules.utils import OUTPUT_DIR, ensure_dirs


def export_materials_to_excel() -> str:
    from database.db_manager import load_materials

    ensure_dirs()
    output_path = OUTPUT_DIR / "materials.xlsx"
    load_materials().to_excel(output_path, index=False)
    return str(output_path)


def export_classifications_to_excel() -> str:
    from database.db_manager import load_classifications

    ensure_dirs()
    output_path = OUTPUT_DIR / "classifications.xlsx"
    load_classifications().to_excel(output_path, index=False)
    return str(output_path)


def export_reviewed_dataset() -> str:
    from database.db_manager import load_joined_dataset

    ensure_dirs()
    output_path = OUTPUT_DIR / "reviewed_dataset.xlsx"
    load_joined_dataset().to_excel(output_path, index=False)
    return str(output_path)


def export_texts_for_cluster() -> str:
    from database.db_manager import load_joined_dataset

    ensure_dirs()
    df = load_joined_dataset()
    columns = [
        "material_id",
        "platform",
        "source_type",
        "clean_text",
        "final_emotion_label",
        "final_frame_label",
        "final_platform_role",
        "final_reshape_type",
    ]
    for column in columns:
        if column not in df.columns:
            df[column] = pd.NA

    output_path = OUTPUT_DIR / "texts_for_cluster.csv"
    df[columns].to_csv(output_path, index=False, encoding="utf-8-sig")
    return str(output_path)
