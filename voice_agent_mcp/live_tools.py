"""Live tool adapters for the local vehicle Agent console."""

from __future__ import annotations

from datetime import date, timedelta
from time import perf_counter
from typing import Callable

from mcp_core.amp_server import maps_around_search, maps_direction_driving, maps_geo, maps_text_search, maps_weather

from .cockpit import CockpitSimulator
from .tools import Tool, ToolRegistry


WeatherFetcher = Callable[[str, str], dict]
PlaceSearcher = Callable[[str, str], dict]

NEARBY_CATEGORIES = {
    "charging_station": "\u5145\u7535\u7ad9",
    "parking_lot": "\u505c\u8f66\u573a",
}


def plan_driving_route(
    origin: str,
    destination: str,
    *,
    origin_location: str = "",
    destination_location: str = "",
    via: list[str] | None = None,
) -> dict:
    """Resolve endpoints and compose real Amap driving legs through waypoints."""
    started = perf_counter()
    city_hint = _infer_city_hint(destination)
    resolved_origin = origin_location or _geocode_location(origin, city_hint)
    resolved_destination = destination_location or _geocode_location(destination, city_hint)
    via_names = [name.strip() for name in (via or []) if name and name.strip()]
    resolved_via = [
        {"name": name, "location": _geocode_location(name, city_hint)}
        for name in via_names
    ]
    if not resolved_origin or not resolved_destination or any(not item["location"] for item in resolved_via):
        return {
            "error": "unable to resolve route endpoints",
            "provider": "amap-mcp",
            "tool": "maps_direction_driving",
            "latency_ms": round((perf_counter() - started) * 1000),
        }

    points = [resolved_origin, *(item["location"] for item in resolved_via), resolved_destination]
    distance_meters = duration_seconds = 0
    polyline: list[str] = []
    for leg_origin, leg_destination in zip(points, points[1:]):
        result = maps_direction_driving(leg_origin, leg_destination)
        if "error" in result:
            return {
                "error": result["error"],
                "provider": "amap-mcp",
                "tool": "maps_direction_driving",
                "latency_ms": round((perf_counter() - started) * 1000),
            }
        paths = result.get("route", {}).get("paths", [])
        first_path = paths[0] if paths else {}
        if not first_path:
            return {
                "error": "no driving route found",
                "provider": "amap-mcp",
                "tool": "maps_direction_driving",
                "latency_ms": round((perf_counter() - started) * 1000),
            }
        distance_meters += int(first_path.get("distance") or 0)
        duration_seconds += int(first_path.get("duration") or 0)
        polyline.extend(step["polyline"] for step in first_path.get("steps", []) if step.get("polyline"))

    latency_ms = round((perf_counter() - started) * 1000)
    return {
        "provider": "amap-mcp",
        "tool": "maps_direction_driving",
        "origin": origin,
        "destination": destination,
        "origin_location": resolved_origin,
        "destination_location": resolved_destination,
        "via": resolved_via,
        "legs": len(points) - 1,
        "distance_meters": distance_meters,
        "duration_seconds": duration_seconds,
        "polyline": polyline,
        "latency_ms": latency_ms,
    }


def search_nearby_places(
    origin: str,
    category: str,
    *,
    origin_location: str = "",
    radius_meters: int = 3000,
) -> dict:
    """Find actionable nearby POIs around a consented browser or manual location."""
    started = perf_counter()
    keyword = NEARBY_CATEGORIES.get(category, category or "\u5468\u8fb9")
    resolved_origin = origin_location or _geocode_location(origin)
    if not resolved_origin:
        return {
            "error": "unable to resolve nearby search origin",
            "provider": "amap-mcp",
            "tool": "maps_around_search",
            "latency_ms": round((perf_counter() - started) * 1000),
        }
    result = maps_around_search(resolved_origin, radius=str(radius_meters), keywords=keyword)
    latency_ms = round((perf_counter() - started) * 1000)
    if "error" in result:
        return {"error": result["error"], "provider": "amap-mcp", "tool": "maps_around_search", "latency_ms": latency_ms}
    pois = [poi for poi in result.get("pois", []) if poi.get("name") and poi.get("location")]
    return {
        "provider": "amap-mcp",
        "tool": "maps_around_search",
        "category": category,
        "keyword": keyword,
        "origin": origin,
        "origin_location": resolved_origin,
        "radius_meters": radius_meters,
        "pois": pois[:5],
        "latency_ms": latency_ms,
    }


def _geocode_location(address: str, city: str = "") -> str:
    if not address:
        return ""
    result = maps_geo(address, city or None)
    candidates = result.get("return", []) if isinstance(result, dict) else []
    return str(candidates[0].get("location") or "") if candidates else ""


def _infer_city_hint(destination: str) -> str:
    for city in ("\u5317\u4eac", "\u4e0a\u6d77", "\u5e7f\u5dde", "\u6df1\u5733", "\u676d\u5dde", "\u6210\u90fd", "\u6b66\u6c49", "\u91cd\u5e86", "\u897f\u5b89", "\u5357\u4eac"):
        if city in destination:
            return city
    return ""


def build_live_registry(
    weather_fetcher: WeatherFetcher = maps_weather,
    place_searcher: PlaceSearcher = maps_text_search,
    cockpit: CockpitSimulator | None = None,
) -> ToolRegistry:
    cockpit_simulator = cockpit or CockpitSimulator()
    registry = ToolRegistry()
    registry.register(Tool("weather.query", "Query live weather through the Amap MCP tool.", _weather(weather_fetcher)))
    registry.register(Tool("music.play", "Request music playback with explicit user consent.", _music))
    registry.register(Tool("map.route", "Search a destination through the Amap MCP tool.", _route(place_searcher)))
    registry.register(Tool("map.nearby", "Request a location before searching nearby vehicle services.", _nearby))
    registry.register(Tool("cockpit.control", "Execute an explicitly simulated cockpit command.", cockpit_simulator.execute))
    return registry


def _weather(fetcher: WeatherFetcher):
    def handler(slots: dict) -> dict:
        city = slots.get("city") or "\u5317\u4eac"
        requested_date, api_date = _weather_date(slots.get("date", ""))
        started = perf_counter()
        result = fetcher(city, api_date)
        latency_ms = round((perf_counter() - started) * 1000)
        if "error" in result:
            return {
                "error": result["error"],
                "provider": "amap-mcp",
                "tool": "maps_weather",
                "latency_ms": latency_ms,
            }
        return {
            "provider": "amap-mcp",
            "tool": "maps_weather",
            "city": result.get("\u57ce\u5e02", city),
            "date": requested_date,
            "weather": result.get("\u5929\u6c14", "\u672a\u77e5"),
            "temperature": result.get("\u6e29\u5ea6", "\u672a\u77e5"),
            "wind_direction": result.get("\u98ce\u5411", ""),
            "wind_power": result.get("\u98ce\u529b", ""),
            "latency_ms": latency_ms,
        }

    return handler


def _music(slots: dict) -> dict:
    artist = slots.get("artist", "")
    song = slots.get("song", "")
    query = " ".join(part for part in (artist, song) if part)
    return {
        "provider": "music-consent",
        "action": "consent_required",
        "artist": artist,
        "song": song,
        "query": query,
        "third_party": ["qq-music", "netease-music"],
        "demo_track": {"id": "night-drive", "title": "Night Drive Original Demo"},
    }


def _route(searcher: PlaceSearcher):
    def handler(slots: dict) -> dict:
        destination = slots.get("destination") or "\u76ee\u7684\u5730"
        city = slots.get("city", "")
        started = perf_counter()
        result = searcher(destination, city)
        latency_ms = round((perf_counter() - started) * 1000)
        if "error" in result:
            return {
                "error": result["error"],
                "provider": "amap-mcp",
                "tool": "maps_text_search",
                "latency_ms": latency_ms,
            }
        return {
            "provider": "amap-mcp",
            "tool": "maps_text_search",
            "destination": destination,
            "pois": result.get("pois", []),
            "latency_ms": latency_ms,
        }

    return handler


def _nearby(slots: dict) -> dict:
    category = slots.get("category", "")
    keyword = NEARBY_CATEGORIES.get(category, category or "\u5468\u8fb9\u670d\u52a1")
    return {
        "provider": "amap-mcp",
        "tool": "maps_around_search",
        "action": "location_required",
        "category": category,
        "keyword": keyword,
    }


def _weather_date(value: str) -> tuple[str, str]:
    today = date.today()
    text = str(value or "")
    if "\u660e\u5929" in text:
        return "\u660e\u5929", (today + timedelta(days=1)).isoformat()
    if "\u540e\u5929" in text:
        return "\u540e\u5929", (today + timedelta(days=2)).isoformat()
    return "\u4eca\u5929", today.isoformat()
