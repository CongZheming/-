PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS materials (
    material_id TEXT PRIMARY KEY,
    platform TEXT,
    source_type TEXT,
    keyword TEXT,
    url TEXT,
    raw_text TEXT,
    clean_text TEXT,
    screenshot_path TEXT,
    input_method TEXT,
    upload_time TEXT,
    researcher_note TEXT
);

CREATE TABLE IF NOT EXISTS classifications (
    classification_id TEXT PRIMARY KEY,
    material_id TEXT,
    relevance_label TEXT,
    content_type TEXT,
    emotion_label TEXT,
    frame_label TEXT,
    platform_role TEXT,
    reshape_type TEXT,
    confidence REAL,
    is_human_checked INTEGER DEFAULT 0,
    final_relevance_label TEXT,
    final_content_type TEXT,
    final_emotion_label TEXT,
    final_frame_label TEXT,
    final_platform_role TEXT,
    final_reshape_type TEXT,
    classified_time TEXT,
    FOREIGN KEY(material_id) REFERENCES materials(material_id)
);

CREATE TABLE IF NOT EXISTS ocr_results (
    ocr_id TEXT PRIMARY KEY,
    material_id TEXT,
    original_image_path TEXT,
    recognized_text TEXT,
    corrected_text TEXT,
    ocr_time TEXT,
    FOREIGN KEY(material_id) REFERENCES materials(material_id)
);

CREATE TABLE IF NOT EXISTS label_dictionary (
    label_id TEXT PRIMARY KEY,
    label_type TEXT,
    label_name TEXT,
    keywords TEXT,
    description TEXT
);
