from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    handler: Callable[[dict], dict]


class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def call(self, name: str, slots: dict) -> dict:
        if name not in self._tools:
            return {"error": f"tool not found: {name}"}
        return self._tools[name].handler(slots)

    def list_tools(self) -> list[dict]:
        return [{"name": tool.name, "description": tool.description} for tool in self._tools.values()]


def default_registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(Tool("weather.query", "查询城市天气", _weather))
    registry.register(Tool("music.play", "播放歌手歌曲", _music))
    registry.register(Tool("map.route", "查询路线规划", _route))
    return registry


def _weather(slots: dict) -> dict:
    city = slots.get("city", "北京")
    date = slots.get("date", "今天")
    return {"city": city, "date": date, "weather": "晴", "temperature": "18-27C"}


def _music(slots: dict) -> dict:
    artist = slots.get("artist", "周杰伦")
    return {"artist": artist, "song": "晴天", "action": "play"}


def _route(slots: dict) -> dict:
    destination = slots.get("destination", "目的地")
    return {"destination": destination, "distance": "3.2km", "duration": "12min"}
