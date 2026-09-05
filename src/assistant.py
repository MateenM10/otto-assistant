"""
The core tool-calling loop, running against a local Ollama model.

Permission is enforced centrally here, based on each tool's trust
level (see TOOL_TRUST in src/tools/__init__.py) — "safe" tools run
instantly, "confirm" tools ask the user first (unless dry-run mode
is on, in which case they're only previewed, never actually run).
Every call, allowed or not, gets recorded to the audit log and
pushed to the HUD's live activity feed.

Also includes a fallback parser: this local model occasionally
outputs a tool call as plain text instead of a real API-level tool
call, sometimes with malformed JSON. We detect that pattern
leniently and recover it as a real tool call.
"""

import json
import re
import requests
from .tools import TOOL_FUNCTIONS, TOOL_SCHEMAS, TOOL_TRUST
from .audit import log_tool_call
from .hud_server import set_status, add_event

OLLAMA_URL = "http://localhost:11434/v1/chat/completions"
MODEL = "llama3.2:3b"
MAX_RESPONSE_TOKENS = 400  # long enough to summarize a screenful of text

SYSTEM_PROMPT = """You are Jarvis, a personal assistant that helps the user
with tasks on their computer. You have tools to read files, list
directories, write files, run shell commands, and read the text
visible on the user's screen.

IMPORTANT: When the user asks about files, directories, or anything
you could check with a tool, you MUST call the tool yourself and use
its real result. Never just explain what command they could run —
actually run it using your tools and give them the real answer.

If the user asks what's on their screen, what they're looking at, or
to read/summarize something currently displayed, use the read_screen
tool — do NOT use run_shell_command or list_directory for this, since
those only show file names, not actual screen content."""


def _to_ollama_tool(schema: dict) -> dict:
    """Our tool files describe tools in Claude's shape. Ollama wants
    them wrapped differently, so we convert here in one place instead
    of rewriting every tool file."""
    return {
        "type": "function",
        "function": {
            "name": schema["name"],
            "description": schema["description"],
            "parameters": schema["input_schema"],
        },
    }


class Assistant:
    def __init__(self):
        self.messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        self.ollama_tools = [_to_ollama_tool(s) for s in TOOL_SCHEMAS]
        self.dry_run = False

    def toggle_dry_run(self) -> str:
        self.dry_run = not self.dry_run
        return f"Dry-run mode is now {'ON' if self.dry_run else 'OFF'}"

    def send(self, user_input: str) -> str:
        self.messages.append({"role": "user", "content": user_input})
        set_status("thinking")

        while True:
            response = requests.post(
                OLLAMA_URL,
                json={
                    "model": MODEL,
                    "messages": self.messages,
                    "tools": self.ollama_tools,
                    "options": {"num_predict": MAX_RESPONSE_TOKENS},
                },
            )
            data = response.json()
            message = data["choices"][0]["message"]

            if message.get("tool_calls"):
                # Real, properly-formatted tool call from the API
                self.messages.append(message)
                for tool_call in message["tool_calls"]:
                    name = tool_call["function"]["name"]
                    result = self._run_tool(name, tool_call["function"]["arguments"])
                    self.messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_call["id"],
                            "content": result,
                        }
                    )
                set_status("thinking")
                continue  # loop back around with the real tool result

            reply = message.get("content") or ""

            # Safety net: model sometimes fakes a tool call as plain text
            fake_call = self._try_parse_fake_tool_call(reply)
            if fake_call:
                name, params = fake_call
                result = self._run_tool(name, params)
                self.messages.append({"role": "assistant", "content": reply})
                self.messages.append(
                    {"role": "user", "content": f"[Recovered tool call result]: {result}"}
                )
                set_status("thinking")
                continue  # loop back around so the model can answer using the real result

            self.messages.append({"role": "assistant", "content": reply})
            set_status("standby")
            return reply

    def _try_parse_fake_tool_call(self, text: str):
        """Detect the model outputting a tool call as plain text instead
        of a real tool call, and recover it. Deliberately lenient: the
        model sometimes emits malformed JSON (e.g. broken braces), so we
        extract the tool name by pattern rather than requiring the whole
        string to parse cleanly."""
        name_match = re.search(r'"name"\s*:\s*"(\w+)"', text)
        if not name_match:
            return None

        name = name_match.group(1)
        if name not in TOOL_FUNCTIONS:
            return None

        # Try to recover arguments if they happen to be valid JSON,
        # but don't fail the whole thing if they aren't.
        params = {}
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            try:
                parsed = json.loads(json_match.group(0))
                params = parsed.get("parameters") or parsed.get("arguments") or {}
                if not isinstance(params, dict):
                    params = {}
            except json.JSONDecodeError:
                params = {}

        return name, params

    def _run_tool(self, name: str, raw_arguments) -> str:
        func = TOOL_FUNCTIONS.get(name)
        if func is None:
            result = f"Error: unknown tool '{name}'"
            log_tool_call(name, {}, result, allowed=False)
            add_event(name, {}, "error")
            return result

        if isinstance(raw_arguments, str):
            try:
                args = json.loads(raw_arguments)
            except json.JSONDecodeError:
                args = {}
        else:
            args = raw_arguments or {}

        # --- Centralized permission check ---
        trust_level = TOOL_TRUST.get(name, "confirm")  # unknown tools default to safe-side: confirm

        if trust_level == "confirm":
            print(f"\n[Jarvis wants to use]: {name}({args})")

            if self.dry_run:
                result = f"[DRY RUN] Would run {name}({args}), but dry-run mode is on — nothing actually happened."
                log_tool_call(name, args, result, allowed=False)
                add_event(name, args, "dry-run")
                return result

            set_status("awaiting permission", name)
            confirmation = input("Allow this? (y/n): ").strip().lower()
            if confirmation != "y":
                result = "User declined to run this tool."
                log_tool_call(name, args, result, allowed=False)
                add_event(name, args, "denied")
                return result

        set_status("running tool", name)

        try:
            result = str(func(**args))
            log_tool_call(name, args, result, allowed=True)
            add_event(name, args, "allowed")
            return result
        except Exception as e:
            result = f"Error running tool '{name}': {e}"
            log_tool_call(name, args, result, allowed=False)
            add_event(name, args, "error")
            return result