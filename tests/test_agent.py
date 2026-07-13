import unittest

from voice_agent_mcp.agent import DialogueAgent


class AgentTest(unittest.TestCase):
    def test_weather_task(self):
        frames = DialogueAgent().handle_as_dicts("北京明天天气怎么样")
        self.assertEqual(frames[-1]["intent"], "weather_query")
        self.assertEqual(frames[-1]["function"], "weather.query")
        self.assertEqual(frames[-1]["slots"]["city"], "北京")

    def test_multi_turn_rewrite(self):
        agent = DialogueAgent()
        agent.handle_as_dicts("播放周杰伦的歌", "u1")
        frames = agent.handle_as_dicts("他的歌还有哪些", "u1")
        self.assertEqual(frames[-1]["slots"]["artist"], "周杰伦")

    def test_reject_noise(self):
        frames = DialogueAgent().handle_as_dicts("asdfghjkl")
        self.assertEqual(frames[-1]["intent"], "reject")


if __name__ == "__main__":
    unittest.main()
