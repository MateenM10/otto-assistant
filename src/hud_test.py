"""Test the HUD server on its own: cycle through some fake statuses."""

import time
from src.hud_server import start_hud_server, set_status

url = start_hud_server()
print(f"HUD running at {url}")
print("Open that URL in your browser. Cycling statuses...")

states = [
    ("listening", ""),
    ("thinking", ""),
    ("running tool", "read_screen"),
    ("awaiting permission", "run_shell_command"),
    ("speaking", ""),
    ("standby", ""),
]

while True:
    for status, detail in states:
        set_status(status, detail)
        print(f"  -> {status} {detail}")
        time.sleep(2)