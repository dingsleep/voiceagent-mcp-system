import unittest

from eval.evaluate_demo import evaluate_cases, render_report


class FakeAgent:
    def handle_as_dicts(self, query, sender_id, trace_id):
        return [
            {
                "intent": "weather_query",
                "function": "weather.query",
                "slots": {"city": "北京"},
                "metadata": {
                    "nlu_backend": "remote",
                    "fallback_reason": "",
                    "total_latency_ms": 120,
                    "reject_trace": {"latency_ms": 8},
                    "nlu_trace": {
                        "intent_recall": {"latency_ms": 12},
                        "function_call": {
                            "latency_ms": 90,
                            "usage": {"prompt_tokens": 30, "completion_tokens": 10, "total_tokens": 40},
                        },
                    },
                    "tool_trace": {"latency_ms": 10},
                },
            }
        ]


class DemoEvaluationTest(unittest.TestCase):
    def test_report_separates_remote_success_and_fallbacks(self):
        report = evaluate_cases(
            FakeAgent(),
            [{"query": "北京天气", "intent": "weather_query", "function": "weather.query", "slots": {"city": "北京"}}],
            backend_mode="remote",
        )

        self.assertEqual(report["remote_success_rate"], 1.0)
        self.assertEqual(report["latency_ms"]["p95"], 120)
        self.assertEqual(report["stage_latency_ms"]["deepseek_fc"]["p50"], 90)
        self.assertEqual(report["function_call_tokens"]["total_tokens"]["total"], 40)
        self.assertEqual(report["remote_fallback_rate"], 0.0)
        self.assertTrue(report["all_expected_match"])
        self.assertIn("remote_success_rate: 100.00%", render_report(report))

    def test_rule_report_does_not_claim_remote_attempts(self):
        report = evaluate_cases(
            FakeAgent(),
            [{"query": "北京天气", "intent": "weather_query", "function": "weather.query", "slots": {"city": "北京"}}],
            backend_mode="rule",
        )

        self.assertEqual(report["remote_attempts"], 0)
        self.assertEqual(report["remote_success_rate"], 0.0)

    def test_performance_cases_can_omit_expected_outputs(self):
        report = evaluate_cases(FakeAgent(), [{"query": "test"}], backend_mode="remote")

        self.assertEqual(report["expected_checks"], {"intent": 0, "function": 0, "slots": 0})
        self.assertTrue(report["all_expected_match"])


if __name__ == "__main__":
    unittest.main()
