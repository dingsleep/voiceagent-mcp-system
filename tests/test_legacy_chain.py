import unittest

from client.arbitration import request_arbitration
from client.stream_chat import process_chat, request_chat
from function_call.schema_catalog import build_catalog, render_markdown
from utils.redis_tool import RedisClient


class LegacyChainTest(unittest.TestCase):
    def test_redis_fallback_roundtrip(self):
        redis_client = RedisClient()
        self.assertTrue(redis_client.set("test:key", "value", ex=5))
        self.assertEqual(redis_client.get("test:key"), "value")

    def test_arbitration_fallback(self):
        self.assertEqual(request_arbitration("北京天气怎么样", "u1"), "task")

    def test_chat_fallback_streams(self):
        response = request_chat("讲个笑话", "u1")
        answer = "".join(process_chat(response, "讲个笑话", "u1"))
        self.assertIn("debug", answer)

    def test_schema_catalog_loads(self):
        catalog = build_catalog()
        self.assertGreater(catalog["total_tools"], 10)
        self.assertGreaterEqual(catalog["unique_tools"], 10)
        self.assertIn("domains", catalog)
        self.assertIn("duplicates", catalog)
        self.assertIn("duplicate_analysis", catalog)
        self.assertIn("validation", catalog)
        self.assertGreater(catalog["domains"]["navigation_map"], 0)
        self.assertGreater(catalog["domains"]["media"], 0)
        self.assertIn("merge_hint", catalog["duplicate_analysis"]["Search_Music"])
        issue_codes = {item["code"] for item in catalog["validation"]}
        self.assertNotIn("required_not_in_properties", issue_codes)
        self.assertNotIn("not_in_slot_config", issue_codes)
        self.assertEqual(catalog["class_config_missing_from_tools"], [])

    def test_schema_report_renders(self):
        report = render_markdown(build_catalog())
        self.assertIn("Function Schema Quality Report", report)
        self.assertIn("Duplicate Tool Names", report)
        self.assertIn("Duplicate Merge Analysis", report)


if __name__ == "__main__":
    unittest.main()
