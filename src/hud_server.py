import json
import queue
import threading
from datetime import datetime
from http.server import HTTPServer, SimpleHTTPRequestHandler

PORT = 8765
MAX_EVENTS = 12      # tool activity entries kept for display
MAX_MESSAGES = 40    # conversation turns kept for display

_state = {
    "status": "standby",
    "detail": "",
    "recording": False,
    "pending": None,
    "speech": True,
    "streaming": "",
}
_events = []         # newest first
_messages = []       # oldest first, like a chat log
_lock = threading.Lock()
_input_queue = queue.Queue()

# Set by the server thread when the mic button is pressed; read by the
# main loop. Separate from the input queue because starting a recording
# isn't a message — it's a mode change.
_mic_start = threading.Event()

# Pending permission request. The main thread parks on _decision_made
# while the browser decides; the server thread sets _decision and fires
# the event when the user clicks Allow or Deny.
_decision = None         # "allow" | "deny" | None
_decision_made = threading.Event()


def set_status(status: str, detail: str = "") -> None:
    with _lock:
        _state["status"] = status
        _state["detail"] = detail


def set_recording(is_recording: bool) -> None:
    with _lock:
        _state["recording"] = is_recording


def set_streaming(text: str) -> None:
    """Partial reply text, shown live while the model is still writing."""
    with _lock:
        _state["streaming"] = text


def toggle_speech() -> bool:
    with _lock:
        _state["speech"] = not _state["speech"]
        return _state["speech"]


def speech_enabled() -> bool:
    with _lock:
        return _state["speech"]


def add_event(tool: str, args: dict, outcome: str) -> None:
    """outcome is one of: allowed, denied, dry-run, error."""
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
    with _lock:
        _messages.append({"role": role, "text": text})
        del _messages[:-MAX_MESSAGES]


def get_next_input(timeout: float = 0.5) -> str:
    """Block until the browser sends something, or raise queue.Empty.

    The timeout lets the main loop wake up periodically so Ctrl+C can
    actually interrupt it.
    """
    return _input_queue.get(timeout=timeout)


def mic_start_requested() -> bool:
    if _mic_start.is_set():
        _mic_start.clear()
        return True
    return False


def request_permission(tool: str, args: dict, timeout: float = 120.0) -> bool:
    """Ask the user via the HUD whether to run a tool. Blocks until they
    answer or it times out. Timing out denies rather than allows —
    failing closed is the safe default for a permission system.
    """
    global _decision

    _decision = None
    _decision_made.clear()

    with _lock:
        _state["pending"] = {"tool": tool, "args": _summarize_args(args)}

    answered = _decision_made.wait(timeout=timeout)

    with _lock:
        _state["pending"] = None

    if not answered:
        return False
    return _decision == "allow"


def resolve_permission(decision: str) -> None:
    global _decision
    _decision = decision
    _decision_made.set()


def _summarize_args(args: dict) -> str:
    """Arguments can be long (file contents, shell commands), so
    truncate them to keep the display readable."""
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
            text = self._read_json().get("text", "").strip()
            if text:
                _input_queue.put(text)
            self._respond_json(json.dumps({"ok": bool(text)}).encode("utf-8"))
            return

        if self.path == "/mic":
            action = self._read_json().get("action", "")
            if action == "start":
                _mic_start.set()
            elif action == "stop":
                # Imported here to avoid a circular import at module load
                from .voice import request_stop
                request_stop()
            self._respond_json(json.dumps({"ok": True}).encode("utf-8"))
            return

        if self.path == "/permission":
            decision = self._read_json().get("decision", "")
            if decision in ("allow", "deny"):
                resolve_permission(decision)
            self._respond_json(json.dumps({"ok": True}).encode("utf-8"))
            return

        if self.path == "/speech":
            enabled = toggle_speech()
            self._respond_json(json.dumps({"enabled": enabled}).encode("utf-8"))
            return

        self.send_response(404)
        self.end_headers()

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length).decode("utf-8")
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {}

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