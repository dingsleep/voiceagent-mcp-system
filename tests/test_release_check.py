import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.check_release import collect_release_status, render_status


class ReleaseCheckTest(unittest.TestCase):
    def test_detects_blocked_model_file_and_noisy_root_file(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "model.bin").write_bytes(b"x")
            (root / "test.py").write_text("print('old smoke')\n", encoding="utf-8")
            status = collect_release_status(root, max_file_mb=1)
            self.assertIn("model.bin", status["blocked_model_files"])
            self.assertIn("test.py", status["noisy_root_files"])
            self.assertFalse(status["ok"])

    def test_render_status(self):
        status = {
            "blocked_model_files": [],
            "oversized_files": [],
            "missing_required": [],
            "noisy_root_files": [],
            "ok": True,
        }
        self.assertIn("release_readiness", render_status(status))


if __name__ == "__main__":
    unittest.main()
