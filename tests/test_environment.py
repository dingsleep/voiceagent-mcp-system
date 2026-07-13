import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.check_env import collect_env_status, parse_dotenv, render_status


class EnvironmentCheckTest(unittest.TestCase):
    def test_parse_dotenv(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / ".env"
            path.write_text("BASE_URL=https://example.com\nAPI_KEY='Bearer token'\n", encoding="utf-8")
            self.assertEqual(parse_dotenv(path)["BASE_URL"], "https://example.com")
            self.assertEqual(parse_dotenv(path)["API_KEY"], "Bearer token")

    def test_collect_env_status_without_env_file(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".env.example").write_text("BASE_URL=https://example.com\n", encoding="utf-8")
            status = collect_env_status(root)
            self.assertFalse(status["env_file_exists"])
            self.assertTrue(status["example_file_exists"])
            self.assertIn("llm_endpoint", status["missing_legacy_groups"])
            self.assertIn("Environment readiness", render_status(status))


if __name__ == "__main__":
    unittest.main()
