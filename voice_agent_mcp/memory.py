import time
from dataclasses import dataclass, field


@dataclass
class Turn:
    query: str
    answer: str
    intent: str
    slots: dict = field(default_factory=dict)


class MemoryStore:
    def __init__(self, ttl_seconds: int = 300, max_turns: int = 6):
        self.ttl_seconds = ttl_seconds
        self.max_turns = max_turns
        self._data: dict[str, tuple[float, list[Turn]]] = {}

    def get(self, sender_id: str) -> list[Turn]:
        item = self._data.get(sender_id)
        if not item:
            return []
        expires_at, turns = item
        if expires_at < time.time():
            self._data.pop(sender_id, None)
            return []
        return turns

    def append(self, sender_id: str, turn: Turn) -> None:
        turns = [*self.get(sender_id), turn][-self.max_turns :]
        self._data[sender_id] = (time.time() + self.ttl_seconds, turns)
