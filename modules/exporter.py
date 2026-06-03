from __future__ import annotations

import json
from datetime import datetime

import pandas as pd

from modules.utils import OUTPUT_DIR, ensure_dirs


def make_export_stamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _output_path(stem: str, suffix: str, stamp: str | None = None) -> str:
    ensure_dirs()
    export_stamp = stamp or make_export_stamp()
    return str(OUTPUT_DIR / f"{stem}_{export_stamp}.{suffix}")


def export_materials_to_excel(stamp: str | None = None) -> str:
    from database.db_manager import load_materials

    output_path = _output_path("materials", "xlsx", stamp)
    load_materials().to_excel(output_path, index=False)
    return output_path


def export_classifications_to_excel(stamp: str | None = None) -> str:
    from database.db_manager import load_classifications

    output_path = _output_path("classifications", "xlsx", stamp)
    load_classifications().to_excel(output_path, index=False)
    return output_path


def export_reviewed_dataset(stamp: str | None = None) -> str:
    from database.db_manager import load_joined_dataset

    output_path = _output_path("reviewed_dataset", "xlsx", stamp)
    load_joined_dataset().to_excel(output_path, index=False)
    return output_path


def export_texts_for_cluster(stamp: str | None = None) -> str:
    from database.db_manager import load_joined_dataset

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

    output_path = _output_path("texts_for_cluster", "csv", stamp)
    df[columns].to_csv(output_path, index=False, encoding="utf-8-sig")
    return output_path


def export_manifest(paths: dict[str, str], stamp: str | None = None) -> str:
    from database.db_manager import load_classifications, load_joined_dataset, load_materials

    output_path = _output_path("manifest", "json", stamp)
    manifest = {
        "exported_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "files": paths,
        "counts": {
            "materials": int(len(load_materials())),
            "classifications": int(len(load_classifications())),
            "joined_rows": int(len(load_joined_dataset())),
        },
    }
    with open(output_path, "w", encoding="utf-8") as file:
        json.dump(manifest, file, ensure_ascii=False, indent=2)
    return output_path
