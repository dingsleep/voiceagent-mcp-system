from dataclasses import dataclass


@dataclass(frozen=True)
class NLUResult:
    intent: str
    function: str
    slots: dict


def parse_task(query: str) -> NLUResult:
    if "天气" in query:
        city = _pick_first(query, ["北京", "上海", "广州", "深圳", "杭州"]) or "北京"
        date = "明天" if "明天" in query else "今天"
        return NLUResult("weather_query", "weather.query", {"city": city, "date": date})

    if any(word in query for word in ("播放", "放一首", "来一首", "他的歌", "她的歌", "的歌")):
        artist = _pick_first(query, ["周杰伦", "林俊杰", "邓紫棋", "陈奕迅"]) or "周杰伦"
        return NLUResult("music_play", "music.play", {"artist": artist})

    if any(word in query for word in ("导航", "路线", "怎么走")):
        destination = query.replace("导航到", "").replace("怎么走", "").strip() or "目的地"
        return NLUResult("map_route", "map.route", {"destination": destination})

    return NLUResult("unknown", "unknown", {})


def _pick_first(text: str, candidates: list[str]) -> str:
    return next((item for item in candidates if item in text), "")
