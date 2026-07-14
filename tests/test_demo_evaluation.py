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


if __name__ == "__main__":
    unittest.main()
