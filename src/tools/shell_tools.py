"""
Tool for running shell commands.

This is the most powerful (and dangerous) tool in Phase 1 — it can do
anything your shell can do. There's no permission system yet (that's
Phase 3), so for now we ask for confirmation on every call. Treat this
as a placeholder that WILL need real guardrails before you give it
broader access.
"""

import subprocess

TIMEOUT_SECONDS = 15


def run_shell_command(command: str) -> str:
    """Run a shell command after asking the user to confirm, return its output."""
    print(f"\n[Jarvis wants to run]: {command}")
    confirmation = input("Allow this? (y/n): ").strip().lower()
    if confirmation != "y":
        return "User declined to run this command."

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


RUN_SHELL_COMMAND_SCHEMA = {
    "name": "run_shell_command",
    "description": (
        "Run a shell command on the user's machine and return its output. "
        "The user will be asked to confirm before it runs. Use this for "
        "things like checking running processes, git status, disk usage, etc."
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