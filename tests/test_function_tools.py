import unittest
from pathlib import Path

from function_call.api_auth import bearer_authorization
from function_call.tool_selection import build_unique_tool_map


ROOT = Path(__file__).resolve().parents[1]


class FunctionToolTest(unittest.TestCase):
    def test_bearer_authorization_accepts_both_config_formats(self):
        self.assertEqual(bearer_authorization("sk-example"), "Bearer sk-example")
        self.assertEqual(bearer_authorization("Bearer sk-example"), "Bearer sk-example")

    def test_deepseek_compatible_top_p_is_in_valid_range(self):
        source = (ROOT / "function_call" / "chatnlu_infer.py").read_text(encoding="utf-8")
        self.assertIn('"top_p": 1', source)

    def test_duplicate_function_uses_richest_schema(self):
        tools = [
            {
                "function": {
                    "name": "Search_Music",
                    "description": "short",
                    "parameters": {"properties": {}},
                }
            },
            {
                "function": {
                    "name": "Search_Music",
                    "description": "detailed music search",
                    "parameters": {
                        "properties": {"Singer": {}, "Song": {}, "Album": {}}
                    },
                }
            },
            {
                "function": {
                    "name": "Query_Weather",
                    "description": "weather query",
                    "parameters": {"properties": {"City": {}}},
                }
            },
        ]

        tool_map = build_unique_tool_map(tools)

        self.assertEqual(set(tool_map), {"Search_Music", "Query_Weather"})
        self.assertEqual(len(tool_map["Search_Music"]), 1)
        self.assertEqual(
            set(tool_map["Search_Music"][0]["function"]["parameters"]["properties"]),
            {"Singer", "Song", "Album"},
        )

    def test_description_breaks_property_count_ties(self):
        tools = [
            {
                "function": {
                    "name": "Go_POI",
                    "description": "brief",
                    "parameters": {"properties": {"POI": {}}},
                }
            },
            {
                "function": {
                    "name": "Go_POI",
                    "description": "navigation to a specified point of interest",
                    "parameters": {"properties": {"POI": {}}},
                }
            },
        ]

        tool_map = build_unique_tool_map(tools)

        self.assertEqual(
            tool_map["Go_POI"][0]["function"]["description"],
            "navigation to a specified point of interest",
        )


if __name__ == "__main__":
    unittest.main()
