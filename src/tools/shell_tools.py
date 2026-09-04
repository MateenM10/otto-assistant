import subprocess

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


RUN_SHELL_COMMAND_SCHEMA = {
    "name": "run_shell_command",
    "description": (
        "Run a shell command on the user's machine and return its output. "
        "Use this for things like checking running processes, git status, "
        "disk usage, etc."
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