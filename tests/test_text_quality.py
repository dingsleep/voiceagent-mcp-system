import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.check_text_quality import find_mojibake


class TextQualityTest(unittest.TestCase):
    def test_detects_mojibake_marker(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "README.md"
            path.write_text("项目说明\n乱码 鏄\n", encoding="utf-8")
            findings = find_mojibake([path])
            self.assertEqual(len(findings), 1)
            self.assertEqual(findings[0]["line"], 2)

    def test_clean_text_passes(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "README.md"
            path.write_text("项目说明\n正常中文\n", encoding="utf-8")
            self.assertEqual(find_mojibake([path]), [])


if __name__ == "__main__":
    unittest.main()
