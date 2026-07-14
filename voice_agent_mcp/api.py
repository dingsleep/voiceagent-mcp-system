import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .runtime import load_local_env

load_local_env()

from .agent import DialogueAgent


agent = DialogueAgent()


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path == "/health":
            self._json(agent.status())
            return
        self._json({"error": "not found"}, status=404)

    def do_POST(self) -> None:
        if self.path != "/chat":
            self._json({"error": "not found"}, status=404)
            return

        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length).decode("utf-8")
        try:
            payload = json.loads(body or "{}")
        except json.JSONDecodeError:
            self._json({"error": "request body must be valid JSON"}, status=400)
            return
        query = payload.get("query") or payload.get("transcript", "")
        if not isinstance(query, str) or not query.strip():
            self._json({"error": "query or transcript is required"}, status=400)
            return
        sender_id = payload.get("sender_id", "demo")
        trace_id = payload.get("trace_id")
        self._json({"frames": agent.handle_as_dicts(query, sender_id, trace_id)})

    def log_message(self, format: str, *args) -> None:
        return

    def _json(self, payload: dict, status: int = 200) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
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
