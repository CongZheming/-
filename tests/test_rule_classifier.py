from __future__ import annotations

import unittest

from modules.rule_classifier import LABEL_OPTIONS, classify_all, classify_relevance


class RuleClassifierTests(unittest.TestCase):
    def test_classify_all_keeps_legacy_fields_and_adds_evidence(self) -> None:
        result = classify_all("生育政策压力太大，普通人养不起孩子。", "微博", "评论")

        self.assertIn(result["relevance_label"], LABEL_OPTIONS["relevance_label"])
        self.assertIn(result["emotion_label"], LABEL_OPTIONS["emotion_label"])
        self.assertIn("confidence", result)
        self.assertIn("needs_review", result)
        self.assertIn("explanations", result)
        self.assertIn("matched_keywords", result["explanations"]["emotion_label"])

    def test_relevance_boundaries(self) -> None:
        self.assertEqual(classify_relevance("生育政策和养孩子成本"), "强相关")
        self.assertEqual(classify_relevance("家庭教育压力"), "中等相关")
        self.assertEqual(classify_relevance("完全不相关的娱乐新闻"), "无关")


if __name__ == "__main__":
    unittest.main()
