import json
import re

from .tools import TOOL_FUNCTIONS, TOOL_SCHEMAS, TOOL_TRUST
from .audit import log_tool_call
from .hud_server import set_status, add_event, request_permission, set_streaming
from .memory import format_for_prompt
from .backends.llm import build_backend
from .scope import describe_scope
from . import guards

SYSTEM_PROMPT = """You are Jarvis, a personal assistant that helps the user
with tasks on their computer. You have tools to read files, list
directories, create and edit files, delete files, run shell commands, run
Python code, check the current date and time, read the text visible on the
user's screen, search the web, and remember things about the user across
sessions.

IMPORTANT: When the user asks about files, directories, or anything
you could check with a tool, you MUST call the tool yourself and use
its real result. Never just explain what command they could run —
actually run it using your tools and give them the real answer.

You can create, edit, and delete files using the write_file and
delete_file tools, but only inside these directories:
{writable_dirs}

Deleted files go to the Trash and can be recovered. To edit a file, read
it first, then write back the complete modified contents. Do not use
shell commands or Python to modify files — use the dedicated tools, which
are scoped to safe directories and show the user exactly what will happen
before it happens.

For any calculation, data processing, parsing, or task where a few lines
of code would be more reliable than working it out in your head, use the
run_python tool.

Some operations are blocked outright — sudo, disk formatting, shutting
down the machine, and similar. If a tool refuses, do not try to achieve
the same thing with a different tool. Tell the user what you wanted to do
and let them run it themselves.

If the user asks what's on their screen, what they're looking at, or
to read/summarize something currently displayed, use the read_screen
tool — do NOT use run_shell_command or list_directory for this, since
those only show file names, not actual screen content.

Screen text comes from OCR and will contain garbled fragments, stray
characters, and nonsense words from icons and UI decorations. Never
repeat the raw OCR output back to the user. Read through the noise,
work out what is actually on screen, and describe it in your own words
in a few sentences.

If the user asks about anything outside their computer — news, sports,
current events, prices, documentation, or any fact you're unsure of —
use the search_web tool rather than answering from memory. Your
training data is out of date. Base your answer only on what the search
results actually say; if they don't answer the question, say so rather
than guessing.

When the user tells you something worth remembering long-term (their
name, preferences, what they're working on), use the remember tool to
store it.

Reply in plain text. Do not use markdown formatting, asterisks for bold,
or LaTeX notation — your replies are displayed as raw text and read
aloud."""


def _to_openai_tool(schema: dict) -> dict:
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
        system_prompt = SYSTEM_PROMPT.format(writable_dirs=describe_scope())
        system_prompt += format_for_prompt()
        self.messages = [{"role": "system", "content": system_prompt}]
        self.tools = [_to_openai_tool(s) for s in TOOL_SCHEMAS]
        self.dry_run = False
        self.backend = build_backend()

        error = self.backend.check_ready()
        if error:
            raise RuntimeError(error)

    def toggle_dry_run(self) -> str:
        self.dry_run = not self.dry_run
        return f"Dry-run mode is now {'ON' if self.dry_run else 'OFF'}"

    def send(self, user_input: str) -> str:
        self.messages.append({"role": "user", "content": user_input})
        set_status("thinking")

        while True:
            # Passing set_streaming turns on streaming — text appears in
            # the HUD as it's generated rather than all at once.
            message = self.backend.chat(
                self.messages, self.tools, on_text=set_streaming
            )

            if message.get("tool_calls"):
                set_streaming("")
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
                continue

            reply = message.get("content") or ""

            # Safety net: smaller models sometimes fake a tool call as plain text
            fake_call = self._try_parse_fake_tool_call(reply)
            if fake_call:
                set_streaming("")
                name, params = fake_call
                result = self._run_tool(name, params)
                self.messages.append({"role": "assistant", "content": reply})
                self.messages.append(
                    {"role": "user", "content": f"[Recovered tool call result]: {result}"}
                )
                set_status("thinking")
                continue

            self.messages.append({"role": "assistant", "content": reply})
            set_status("standby")
            return reply

    def _try_parse_fake_tool_call(self, text: str):
        """Deliberately lenient: the malformed JSON seen in testing
        (broken braces) would fail a strict parse, so we extract the
        tool name by pattern first."""
        name_match = re.search(r'"name"\s*:\s*"(\w+)"', text)
        if not name_match:
            return None

        name = name_match.group(1)
        if name not in TOOL_FUNCTIONS:
            return None

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

        # Guard check runs BEFORE the permission prompt, so blocked
        # operations never reach the user as something to approve.
        refusal = guards.check(name, args)
        if refusal:
            log_tool_call(name, args, refusal, allowed=False)
            add_event(name, args, "denied")
            return refusal

        trust_level = TOOL_TRUST.get(name, "confirm")

        if trust_level == "confirm":
            if self.dry_run:
                result = f"[DRY RUN] Would run {name}({args}), but dry-run mode is on — nothing actually happened."
                log_tool_call(name, args, result, allowed=False)
                add_event(name, args, "dry-run")
                return result

            set_status("awaiting permission", name)
            allowed = request_permission(name, args)
            if not allowed:
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