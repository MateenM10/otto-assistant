"""
Shell and system-info tools.

run_shell_command is the most powerful (and dangerous) tool in the
project — it can do anything your shell can do. Confirmation isn't
handled here; it's decided centrally in assistant.py based on trust
level (see TOOL_TRUST in src/tools/__init__.py).

get_current_datetime exists as its own tool rather than leaving the
date to run_shell_command. The local model kept composing partial
commands (e.g. `date +%Y`, which returns only the year) and then
inventing the missing parts of the date. A zero-argument tool that
returns the whole thing removes that failure mode.
"""

import subprocess
from datetime import datetime

TIMEOUT_SECONDS = 15


def run_shell_command(command: str) -> str:
    """Run a shell command and return its output."""
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS,
        )
        output = result.stdout.strip()
        error = result.stderr.strip()
        if result.returncode != 0:
            return f"Command exited with code {result.returncode}.\nstdout: {output}\nstderr: {error}"
        return output if output else "(command produced no output)"
    except subprocess.TimeoutExpired:
        return f"Error: command timed out after {TIMEOUT_SECONDS} seconds."
    except Exception as e:
        return f"Error running command: {e}"


def get_current_datetime() -> str:
    """Return the current local date and time."""
    now = datetime.now().astimezone()
    return now.strftime("%A, %B %d, %Y at %I:%M %p %Z")


RUN_SHELL_COMMAND_SCHEMA = {
    "name": "run_shell_command",
    "description": (
        "Run a shell command on the user's machine and return its output. "
        "Use this for things like checking running processes, git status, "
        "disk usage, etc. Do NOT use this to get the date or time — use "
        "get_current_datetime for that instead."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "The shell command to execute.",
            }
        },
        "required": ["command"],
    },
}

GET_CURRENT_DATETIME_SCHEMA = {
    "name": "get_current_datetime",
    "description": (
        "Get the current date, day of the week, and time. Always use this "
        "instead of run_shell_command when the user asks what day, date, or "
        "time it is. Report the result exactly as returned — do not guess or "
        "add any part of the date yourself."
    ),
    "input_schema": {
        "type": "object",
        "properties": {},
        "required": [],
    },
}