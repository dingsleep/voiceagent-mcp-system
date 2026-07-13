import re


def arbitrate(query: str) -> str:
    text = query.strip().lower()
    if not text:
        return "reject"
    if re.fullmatch(r"[a-z0-9]{6,}", text):
        return "reject"
    if any(word in query for word in ("天气", "播放", "放一首", "的歌", "导航", "路线", "怎么走")):
        return "task"
    return "chat"
