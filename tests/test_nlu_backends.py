import unittest

from voice_agent_mcp.agent import DialogueAgent
from voice_agent_mcp.nlu_backends import RemoteNluBackend


class NluBackendTest(unittest.TestCase):
    def test_remote_backend_result_is_used_when_tool_is_supported(self):
        calls = []

        def transport(endpoint, payload, timeout_seconds):
            calls.append((endpoint, payload, timeout_seconds))
            return {
                "intent": "weather_query",
                "function": "weather.query",
                "slots": {"city": "上海", "date": "今天"},
            }

        backend = RemoteNluBackend("http://nlu.example/v1", transport=transport)
        final = DialogueAgent(nlu_backend=backend).handle_as_dicts("上海天气", trace_id="trace-1")[-1]

        self.assertEqual(final["function"], "weather.query")
        self.assertEqual(final["metadata"]["nlu_backend"], "remote")
        self.assertEqual(final["metadata"]["trace_id"], "trace-1")
        self.assertEqual(calls[0][1]["enable_dm"], False)

    def test_legacy_weather_contract_is_normalized_for_demo_tool(self):
        backend = RemoteNluBackend(
            "http://nlu.example/v1",
            transport=lambda endpoint, payload, timeout_seconds: {
                "intent": "天气查询",
                "function": "Query_Weather",
                "slots": {"City": "北京", "Date": "明天"},
            },
        )
        final = DialogueAgent(nlu_backend=backend).handle_as_dicts("北京明天天气")[-1]

        self.assertEqual(final["intent"], "weather_query")
        self.assertEqual(final["function"], "weather.query")
        self.assertEqual(final["slots"], {"city": "北京", "date": "明天"})
        self.assertEqual(final["metadata"]["nlu_backend"], "remote")

    def test_remote_failure_falls_back_to_rule_backend(self):
        def unavailable(endpoint, payload, timeout_seconds):
            raise RuntimeError("connection refused")

        backend = RemoteNluBackend("http://nlu.example/v1", transport=unavailable)
        final = DialogueAgent(nlu_backend=backend).handle_as_dicts("北京明天天气")[-1]

        self.assertEqual(final["function"], "weather.query")
        self.assertEqual(final["metadata"]["nlu_backend"], "rule")
        self.assertEqual(final["metadata"]["fallback_reason"], "remote_error:RuntimeError")

    def test_remote_service_fallback_is_not_reported_as_remote_success(self):
        backend = RemoteNluBackend(
            "http://nlu.example/v1",
            transport=lambda endpoint, payload, timeout_seconds: {
                "intent": "weather_query",
                "function": "Query_Weather",
                "slots": {"City": "北京"},
                "source": "fallback",
                "fallback_reason": "llm_request_failed",
            },
        )
        final = DialogueAgent(nlu_backend=backend).handle_as_dicts("北京明天天气")[-1]

        self.assertEqual(final["metadata"]["nlu_backend"], "rule")
        self.assertEqual(
            final["metadata"]["fallback_reason"],
            "remote_fallback:llm_request_failed",
        )

    def test_legacy_music_slot_alias_is_normalized_for_demo_tool(self):
        backend = RemoteNluBackend(
            "http://nlu.example/v1",
            transport=lambda endpoint, payload, timeout_seconds: {
                "intent": "music search",
                "function": "Search_Music",
                "slots": {"\u6b4c\u624b": "\u5468\u6770\u4f26"},
            },
        )
        final = DialogueAgent(nlu_backend=backend).handle_as_dicts("\u64ad\u653e\u5468\u6770\u4f26\u7684\u6b4c")[-1]

        self.assertEqual(final["function"], "music.play")
        self.assertEqual(final["slots"], {"artist": "\u5468\u6770\u4f26"})

    def test_legacy_company_navigation_uses_implicit_destination(self):
        backend = RemoteNluBackend(
            "http://nlu.example/v1",
            transport=lambda endpoint, payload, timeout_seconds: {
                "intent": "company navigation",
                "function": "Go_Company",
                "slots": {},
            },
        )
        final = DialogueAgent(nlu_backend=backend).handle_as_dicts("\u5bfc\u822a\u5230\u516c\u53f8")[-1]

        self.assertEqual(final["function"], "map.route")
        self.assertEqual(final["slots"], {"destination": "\u516c\u53f8"})

    def test_unsupported_remote_tool_falls_back_to_demo_contract(self):
        backend = RemoteNluBackend(
            "http://nlu.example/v1",
            transport=lambda endpoint, payload, timeout_seconds: {
                "intent": "seat_control",
                "function": "seat.adjust",
                "slots": {"position": "forward"},
            },
        )
        final = DialogueAgent(nlu_backend=backend).handle_as_dicts("北京明天天气")[-1]

        self.assertEqual(final["function"], "weather.query")
        self.assertEqual(final["metadata"]["nlu_backend"], "rule")
        self.assertEqual(final["metadata"]["fallback_reason"], "unsupported_function:seat.adjust")


if __name__ == "__main__":
    unittest.main()
