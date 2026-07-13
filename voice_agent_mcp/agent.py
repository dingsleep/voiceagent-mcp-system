from .arbitration import arbitrate
from .frames import Frame, stream_text
from .memory import MemoryStore, Turn
from .nlu import parse_task
from .rewrite import rewrite_query
from .tools import ToolRegistry, default_registry


class DialogueAgent:
    def __init__(self, memory: MemoryStore | None = None, tools: ToolRegistry | None = None):
        self.memory = memory or MemoryStore()
        self.tools = tools or default_registry()

    def handle(self, query: str, sender_id: str = "demo") -> list[Frame]:
        history = self.memory.get(sender_id)
        rewritten = rewrite_query(query, history)
        route = arbitrate(rewritten)

        if route == "reject":
            answer = "抱歉，这个问题我还没理解，请换个说法。"
            self.memory.append(sender_id, Turn(rewritten, answer, "reject"))
            return list(stream_text(answer, intent="reject"))

        if route == "chat":
            answer = self._chat(rewritten)
            self.memory.append(sender_id, Turn(rewritten, answer, "chat"))
            return list(stream_text(answer, intent="chat"))

        nlu = parse_task(rewritten)
        tool_result = self.tools.call(nlu.function, nlu.slots)
        answer = self._nlg(nlu.function, tool_result)
        self.memory.append(sender_id, Turn(rewritten, answer, nlu.intent, nlu.slots))
        return list(stream_text(answer, intent=nlu.intent, function=nlu.function, slots=nlu.slots))

    def handle_as_dicts(self, query: str, sender_id: str = "demo") -> list[dict]:
        return [frame.to_dict() for frame in self.handle(query, sender_id)]

    def _chat(self, query: str) -> str:
        if "笑话" in query:
            return "可以。为什么程序员喜欢安静？因为一有噪声，就想 debug。"
        return "我是一个任务型对话 Agent Demo，可以查天气、放音乐、规划路线，也能做简单闲聊。"

    def _nlg(self, function: str, result: dict) -> str:
        if "error" in result:
            return "工具暂时不可用，我稍后再试。"
        if function == "weather.query":
            return f"{result['city']}{result['date']}天气{result['weather']}，气温{result['temperature']}。"
        if function == "music.play":
            return f"正在为你播放{result['artist']}的《{result['song']}》。"
        if function == "map.route":
            return f"去{result['destination']}约{result['distance']}，预计{result['duration']}。"
        return "任务已处理完成。"
