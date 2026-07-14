from dataclasses import dataclass


@dataclass(frozen=True)
class Frame:
    status: str
    content: str
    intent: str = ""
    function: str = ""
    slots: dict | None = None
    metadata: dict | None = None

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "content": self.content,
            "intent": self.intent,
            "function": self.function,
            "slots": self.slots or {},
            "metadata": self.metadata or {},
        }


def stream_text(
    text: str,
    *,
    intent: str = "chat",
    function: str = "",
    slots: dict | None = None,
    metadata: dict | None = None,
):
    yield Frame("start", "", intent=intent, function=function, slots=slots, metadata=metadata)
    for chunk in split_for_stream(text):
        yield Frame("delta", chunk, intent=intent, function=function, slots=slots, metadata=metadata)
    yield Frame("end", "", intent=intent, function=function, slots=slots, metadata=metadata)


def split_for_stream(text: str, size: int = 12) -> list[str]:
    if not text:
        return []
    chunks: list[str] = []
    buf = ""
    for char in text:
        buf += char
        if char in "，。！？；,.!?" or len(buf) >= size:
            chunks.append(buf)
            buf = ""
    if buf:
        chunks.append(buf)
    return chunks
