"""
Local web server backing the HUD.

Handles two-way communication:
- Serves the HUD page and exposes state (status, tool events,
  conversation) at /status for the page to poll.
- Accepts user input from the page at /send, queued for the main
  loop to pick up.

Runs in a background thread. The queue is what lets the browser (in
the server thread) hand work to the assistant (in the main thread)
without either blocking the other.
"""

import json
import queue
import threading
from datetime import datetime
from http.server import HTTPServer, SimpleHTTPRequestHandler

PORT = 8765
MAX_EVENTS = 12      # tool activity entries kept for display
MAX_MESSAGES = 40    # conversation turns kept for display

_state = {"status": "standby", "detail": ""}
_events = []         # newest first
_messages = []       # oldest first, like a chat log
_lock = threading.Lock()
_input_queue = queue.Queue()


def set_status(status: str, detail: str = "") -> None:
    """Update what the HUD's centre display shows."""
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


def add_message(role: str, text: str) -> None:
    """Add a turn to the conversation shown in the HUD."""
    with _lock:
        _messages.append({"role": role, "text": text})
        del _messages[:-MAX_MESSAGES]


def get_next_input(timeout: float = 0.5) -> str:
    """Block until the browser sends something, or raise queue.Empty.

    The timeout matters: it lets the main loop wake up periodically so
    Ctrl+C can actually interrupt it.
    """
    return _input_queue.get(timeout=timeout)


def _summarize_args(args: dict) -> str:
    """Arguments can be long (file contents, shell commands), so
    truncate them to keep the feed readable."""
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
                payload = json.dumps(
                    {**_state, "events": list(_events), "messages": list(_messages)}
                ).encode("utf-8")
            self._respond_json(payload)
            return
        super().do_GET()

    def do_POST(self):
        if self.path == "/send":
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length).decode("utf-8")
            try:
                text = json.loads(raw).get("text", "").strip()
            except json.JSONDecodeError:
                text = ""

            if text:
                _input_queue.put(text)

            self._respond_json(json.dumps({"ok": bool(text)}).encode("utf-8"))
            return

        self.send_response(404)
        self.end_headers()

    def _respond_json(self, payload: bytes):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *args):
        pass  # silence per-request logging so it doesn't spam the terminal


def start_hud_server() -> str:
    """Start the server in a background thread. Returns the HUD URL."""
    server = HTTPServer(("localhost", PORT), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return f"http://localhost:{PORT}/index.html"