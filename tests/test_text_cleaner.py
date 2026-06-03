from __future__ import annotations

import unittest

from modules.text_cleaner import clean_text


class TextCleanerTests(unittest.TestCase):
    def test_removes_urls_blank_lines_and_ui_noise(self) -> None:
        raw = "点赞\n  这是一条内容 https://example.com/a \n\n评论\n第二行\t内容"

        self.assertEqual(clean_text(raw), "这是一条内容\n第二行 内容")

    def test_empty_text_returns_empty_string(self) -> None:
        self.assertEqual(clean_text(""), "")


if __name__ == "__main__":
    unittest.main()
