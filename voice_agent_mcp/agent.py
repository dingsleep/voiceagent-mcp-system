from .arbitration import arbitrate
from .frames import Frame, stream_text
from .memory import MemoryStore, Turn
import time
import uuid

from .nlu_backends import NLUBackend, RuleNluBackend, build_nlu_backend
from .rewrite import rewrite_query
from .tools import ToolRegistry, default_registry


class DialogueAgent:
    def __init__(
        self,
        memory: MemoryStore | None = None,
        tools: ToolRegistry | None = None,
        nlu_backend: NLUBackend | None = None,
    ):
        self.memory = memory or MemoryStore()
        self.tools = tools or default_registry()
        self.nlu_backend = nlu_backend or build_nlu_backend()

    def handle(self, query: str, sender_id: str = "demo", trace_id: str | None = None) -> list[Frame]:
        started = time.perf_counter()
        trace_id = trace_id or uuid.uuid4().hex
        history = self.memory.get(sender_id)
        rewritten = rewrite_query(query, history)
        route = arbitrate(rewritten)
        metadata = {"trace_id": trace_id, "route": route, "nlu_backend": "not_used"}

        if route == "reject":
            answer = "抱歉，这个问题我还没理解，请换个说法。"
            self.memory.append(sender_id, Turn(rewritten, answer, "reject"))
            return list(stream_text(answer, intent="reject", metadata=self._finish(metadata, started)))

        if route == "chat":
            answer = self._chat(rewritten)
            self.memory.append(sender_id, Turn(rewritten, answer, "chat"))
            return list(stream_text(answer, intent="chat", metadata=self._finish(metadata, started)))

        try:
            decision = self.nlu_backend.parse(rewritten, trace_id)
        except (OSError, RuntimeError, ValueError) as exc:
            decision = RuleNluBackend().parse(rewritten, trace_id)
            decision = decision.__class__(
                result=decision.result,
                backend=decision.backend,
                latency_ms=decision.latency_ms,
                fallback_reason=f"remote_error:{type(exc).__name__}",
            )

        nlu = decision.result
        if not self.tools.has(nlu.function):
            fallback = RuleNluBackend().parse(rewritten, trace_id)
            decision = fallback.__class__(
                result=fallback.result,
                backend=fallback.backend,
                latency_ms=decision.latency_ms + fallback.latency_ms,
                fallback_reason=f"unsupported_function:{nlu.function}",
            )
            nlu = decision.result

        tool_result = self.tools.call(nlu.function, nlu.slots)
        answer = self._nlg(nlu.function, tool_result)
        self.memory.append(sender_id, Turn(rewritten, answer, nlu.intent, nlu.slots))
        metadata.update(
            {
                "nlu_backend": decision.backend,
                "nlu_latency_ms": decision.latency_ms,
                "fallback_reason": decision.fallback_reason,
            }
        )
        return list(
            stream_text(
                answer,
                intent=nlu.intent,
                function=nlu.function,
                slots=nlu.slots,
                metadata=self._finish(metadata, started),
            )
        )

    def handle_as_dicts(self, query: str, sender_id: str = "demo", trace_id: str | None = None) -> list[dict]:
        return [frame.to_dict() for frame in self.handle(query, sender_id, trace_id)]

    def status(self) -> dict:
        return {"status": "healthy", "nlu": self.nlu_backend.describe(), "tools": len(self.tools.list_tools())}

    @staticmethod
    def _finish(metadata: dict, started: float) -> dict:
        return {**metadata, "total_latency_ms": round((time.perf_counter() - started) * 1000)}

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
