import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from .runtime import load_local_env

load_local_env()

from .agent import DialogueAgent
from .chat_backends import DeepSeekChatBackend
from .live_tools import build_live_registry, plan_driving_route, search_nearby_places
from .rate_limit import SlidingWindowRateLimiter
from .reject_backends import RemoteRejectBackend


live_tools = build_live_registry() if os.getenv("AMAP_MAPS_API_KEY") else None
agent = DialogueAgent(
    tools=live_tools,
    reject_backend=RemoteRejectBackend(os.getenv("REJECT_URL", "http://127.0.0.1:8007/reject-server/v1")),
    chat_backend=DeepSeekChatBackend(),
)
rate_limiter = SlidingWindowRateLimiter(
    max_requests=int(os.getenv("VOICE_AGENT_RATE_LIMIT_MAX", "12")),
    window_seconds=float(os.getenv("VOICE_AGENT_RATE_LIMIT_WINDOW", "60")),
)
WEB_ROOT = Path(__file__).with_name("web")


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path == "/health":
            self._json(agent.status())
            return
        if self.path in {"/", "/index.html"}:
            self._file(WEB_ROOT / "index.html", "text/html; charset=utf-8")
            return
        if self.path == "/app.js":
            self._file(WEB_ROOT / "app.js", "text/javascript; charset=utf-8")
            return
        if self.path == "/app.css":
            self._file(WEB_ROOT / "app.css", "text/css; charset=utf-8")
            return
        if self.path == "/assets/night-drive-original-demo.wav":
            self._file(WEB_ROOT / "assets" / "night-drive-original-demo.wav", "audio/wav")
            return
        if self.path == "/map-config":
            key = os.getenv("AMAP_MAPS_API_KEY", "")
            if not key:
                self._json({"error": "Amap key is not configured"}, status=503)
                return
            self._json({"key": key})
            return
        self._json({"error": "not found"}, status=404)

    def do_POST(self) -> None:
        if self.path not in {"/chat", "/route", "/nearby"}:
            self._json({"error": "not found"}, status=404)
            return

        allowed, retry_after = rate_limiter.allow(self.client_address[0])
        if not allowed:
            self._json(
                {"error": "rate limit exceeded", "retry_after_seconds": retry_after},
                status=429,
                headers={"Retry-After": str(retry_after)},
            )
            return

        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length).decode("utf-8")
        try:
            payload = json.loads(body or "{}")
        except json.JSONDecodeError:
            self._json({"error": "request body must be valid JSON"}, status=400)
            return
        if self.path == "/route":
            self._route(payload)
            return
        if self.path == "/nearby":
            self._nearby(payload)
            return
        query = payload.get("query") or payload.get("transcript", "")
        if not isinstance(query, str) or not query.strip():
            self._json({"error": "query or transcript is required"}, status=400)
            return
        sender_id = payload.get("sender_id", "demo")
        trace_id = payload.get("trace_id")
        try:
            frames = agent.handle_as_dicts(query, sender_id, trace_id)
        except Exception:
            self._json({"error": "agent execution failed; please retry"}, status=500)
            return
        self._json({"frames": frames})

    def _route(self, payload: dict) -> None:
        origin = payload.get("origin", "")
        origin_location = payload.get("origin_location", "")
        destination = payload.get("destination", "")
        destination_location = payload.get("destination_location", "")
        via = payload.get("via", [])
        if not isinstance(origin, str) or not isinstance(origin_location, str) or not (origin.strip() or origin_location.strip()):
            self._json({"error": "origin or origin_location is required"}, status=400)
            return
        if not isinstance(destination, str) or not destination.strip():
            self._json({"error": "destination is required"}, status=400)
            return
        if not isinstance(via, list) or not all(isinstance(item, str) and item.strip() for item in via):
            self._json({"error": "via must be a list of non-empty place names"}, status=400)
            return
        try:
            route = plan_driving_route(
                origin.strip() or "current location",
                destination.strip(),
                origin_location=origin_location.strip(),
                destination_location=destination_location.strip(),
                via=via,
            )
        except Exception:
            self._json({"error": "route planning failed; please retry"}, status=500)
            return
        status = 502 if "error" in route else 200
        self._json({"route": route}, status=status)

    def _nearby(self, payload: dict) -> None:
        origin = payload.get("origin", "")
        origin_location = payload.get("origin_location", "")
        category = payload.get("category", "")
        if not isinstance(origin, str) or not isinstance(origin_location, str) or not (origin.strip() or origin_location.strip()):
            self._json({"error": "origin or origin_location is required"}, status=400)
            return
        if category not in {"charging_station", "parking_lot"}:
            self._json({"error": "supported category is required"}, status=400)
            return
        try:
            nearby = search_nearby_places(
                origin.strip() or "current location",
                category,
                origin_location=origin_location.strip(),
            )
        except Exception:
            self._json({"error": "nearby search failed; please retry"}, status=500)
            return
        status = 502 if "error" in nearby else 200
        self._json({"nearby": nearby}, status=status)

    def log_message(self, format: str, *args) -> None:
        return

    def _json(self, payload: dict, status: int = 200, headers: dict[str, str] | None = None) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        for name, value in (headers or {}).items():
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(data)

    def _file(self, path: Path, content_type: str) -> None:
        if not path.is_file():
            self._json({"error": "not found"}, status=404)
            return
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def main() -> None:
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "8080"))
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"Serving on http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
