from .memory import Turn


def rewrite_query(query: str, history: list[Turn]) -> str:
    query = query.strip()
    if not history:
        return query

    last = history[-1]
    city = last.slots.get("city")
    artist = last.slots.get("artist")

    if city and query in {"明天呢", "那明天呢"}:
        return f"{city}明天天气怎么样"
    if city and query.startswith("那") and query.endswith("呢"):
        return f"{query[1:-1]}天气怎么样"
    if artist and ("他的歌" in query or "她的歌" in query):
        return query.replace("他的歌", f"{artist}的歌").replace("她的歌", f"{artist}的歌")
    return query
