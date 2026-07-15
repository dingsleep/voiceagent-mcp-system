import unittest

from voice_agent_mcp.chat_backends import DeepSeekChatBackend


class ChatBackendTest(unittest.TestCase):
    def test_streamed_content_and_usage_are_collected(self):
        backend = DeepSeekChatBackend(
            transport=lambda payload: [
                {"content": "你好"},
                {"content": "，我是车载助手。"},
                {"usage": {"prompt_tokens": 12, "completion_tokens": 8, "total_tokens": 20}},
            ]
        )

        decision = backend.reply("你好")

        self.assertEqual(decision.text, "你好，我是车载助手。")
        self.assertEqual(decision.trace["usage"]["total_tokens"], 20)
        self.assertGreaterEqual(decision.trace["first_token_ms"], 0)
