from __future__ import annotations

import tempfile
import unittest
import gc
from pathlib import Path

import database.db_init as db_init
import database.db_manager as db_manager


class DatabaseManagerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.db_path = Path(self.tmpdir.name) / "test.db"
        self.original_db_init_path = db_init.DATABASE_PATH
        self.original_db_manager_path = db_manager.DATABASE_PATH
        db_init.DATABASE_PATH = self.db_path
        db_manager.DATABASE_PATH = self.db_path
        db_manager.init_database()

    def tearDown(self) -> None:
        db_init.DATABASE_PATH = self.original_db_init_path
        db_manager.DATABASE_PATH = self.original_db_manager_path
        gc.collect()
        self.tmpdir.cleanup()

    def test_insert_classify_and_delete_material(self) -> None:
        material = {
            "material_id": "mat_test",
            "platform": "微博",
            "source_type": "评论",
            "keyword": "生育",
            "url": "",
            "raw_text": "生育压力太大",
            "clean_text": "生育压力太大",
            "screenshot_path": "",
            "input_method": "text",
            "upload_time": "2026-06-03 10:00:00",
            "researcher_note": "",
        }
        classification = {
            "classification_id": "cls_test",
            "material_id": "mat_test",
            "relevance_label": "强相关",
            "content_type": "政策讨论",
            "emotion_label": "焦虑",
            "frame_label": "生育成本",
            "platform_role": "热度扩散",
            "reshape_type": "情绪化",
            "confidence": 0.8,
            "needs_review": False,
            "explanations": {"emotion_label": {"matched_keywords": ["压力"]}},
            "classified_time": "2026-06-03 10:01:00",
        }

        db_manager.insert_material(material)
        db_manager.insert_classification(classification)

        self.assertEqual(len(db_manager.load_materials()), 1)
        self.assertEqual(len(db_manager.load_classifications()), 1)

        result = db_manager.delete_material("mat_test")

        self.assertTrue(result["deleted"])
        self.assertEqual(len(db_manager.load_materials()), 0)
        self.assertEqual(len(db_manager.load_classifications()), 0)


if __name__ == "__main__":
    unittest.main()
