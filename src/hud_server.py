import json
import threading
from http.server import HTTPServer, SimpleHTTPRequestHandler

PORT = 8765

# Shared state the assistant updates and the HUD reads.
# A lock isn't strictly needed for a single string on CPython, but it
# makes the intent clear and avoids surprises if this grows.
_state = {"status": "standby", "detail": ""}
_lock = threading.Lock()


def set_status(status: str, detail: str = "") -> None:
    """Called by the assistant to update what the HUD displays."""
    with _lock:
        _state["status"] = status
        _state["detail"] = detail


class _Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        # Serve files out of the hud/ folder
        super().__init__(*args, directory="hud", **kwargs)

    def do_GET(self):
        if self.path == "/status":
            with _lock:
                payload = json.dumps(_state).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return
        # Anything else: serve as a normal static file
        super().do_GET()

    def log_message(self, *args):
        pass  # silence per-request logging so it doesn't spam the terminal


def start_hud_server() -> str:
    """Start the server in a background thread. Returns the HUD URL."""
    server = HTTPServer(("localhost", PORT), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return f"http://localhost:{PORT}/index.html"