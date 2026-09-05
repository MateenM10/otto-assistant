import json
import threading
from datetime import datetime
from http.server import HTTPServer, SimpleHTTPRequestHandler

PORT = 8765
MAX_EVENTS = 12  # only keep the most recent few; the HUD can't show more

_state = {"status": "standby", "detail": ""}
_events = []  # newest first
_lock = threading.Lock()


def set_status(status: str, detail: str = "") -> None:
    """Called by the assistant to update what the HUD displays."""
    with _lock:
        _state["status"] = status
        _state["detail"] = detail


def add_event(tool: str, args: dict, outcome: str) -> None:
    """Record a tool call for the HUD's activity feed.

    outcome is one of: "allowed", "denied", "dry-run", "error".
    """
    with _lock:
        _events.insert(
            0,
            {
                "time": datetime.now().strftime("%H:%M:%S"),
                "tool": tool,
                "args": _summarize_args(args),
                "outcome": outcome,
            },
        )
        del _events[MAX_EVENTS:]


def _summarize_args(args: dict) -> str:
    """Keep the feed readable — arguments can be long (file contents,
    shell commands), so truncate them for display."""
    if not args:
        return ""
    parts = []
    for key, value in args.items():
        text = str(value)
        if len(text) > 40:
            text = text[:40] + "…"
        parts.append(f"{key}={text}")
    return ", ".join(parts)


class _Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory="hud", **kwargs)

    def do_GET(self):
        if self.path == "/status":
            with _lock:
                payload = json.dumps({**_state, "events": list(_events)}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return
        super().do_GET()

    def log_message(self, *args):
        pass  # silence per-request logging so it doesn't spam the terminal


def start_hud_server() -> str:
    """Start the server in a background thread. Returns the HUD URL."""
    server = HTTPServer(("localhost", PORT), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return f"http://localhost:{PORT}/index.html"