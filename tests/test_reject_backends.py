import unittest

from voice_agent_mcp.agent import DialogueAgent
from voice_agent_mcp.nlu_backends import RuleNluBackend
from voice_agent_mcp.reject_backends import RemoteRejectBackend


class RejectBackendTest(unittest.TestCase):
    def test_remote_reject_trace_blocks_unsupported_input(self):
        backend = RemoteRejectBackend(
            "http://reject.example/v1",
            transport=lambda endpoint, payload, timeout: {"data": 0, "score": "0.12"},
        )
        final = DialogueAgent(nlu_backend=RuleNluBackend(), reject_backend=backend).handle_as_dicts("noise")[-1]

        self.assertEqual(final["intent"], "reject")
        self.assertEqual(final["metadata"]["reject_trace"]["backend"], "bert_tiny")
        self.assertFalse(final["metadata"]["reject_trace"]["allowed"])

    def test_remote_reject_trace_allows_task(self):
        backend = RemoteRejectBackend(
            "http://reject.example/v1",
            transport=lambda endpoint, payload, timeout: {"data": 1, "score": "0.99"},
        )
        final = DialogueAgent(nlu_backend=RuleNluBackend(), reject_backend=backend).handle_as_dicts(
            "\u5317\u4eac\u5929\u6c14"
        )[-1]

        self.assertEqual(final["function"], "weather.query")
        self.assertEqual(final["metadata"]["reject_trace"]["backend"], "bert_tiny")
