import os
import re
import subprocess
import sys
import tempfile

TIMEOUT_SECONDS = 30
MAX_OUTPUT_CHARS = 4000

# Patterns that indicate the code would modify the filesystem, run
# other programs, or reach the network. This is a guard against
# accidents, not a security boundary — a determined model could work
# around it. The real protection is the permission modal showing the
# user the code before it runs.
BLOCKED_PATTERNS = [
    (r"\bopen\s*\([^)]*['\"][wax]", "opening a file in write/append mode"),
    (r"\bos\.remove\b", "os.remove"),
    (r"\bos\.unlink\b", "os.unlink"),
    (r"\bos\.rmdir\b", "os.rmdir"),
    (r"\bos\.rename\b", "os.rename"),
    (r"\bos\.system\b", "os.system"),
    (r"\bshutil\.(rmtree|move|copy)", "shutil file operations"),
    (r"\bsubprocess\b", "subprocess"),
    (r"\bPath\s*\([^)]*\)\s*\.(write_text|write_bytes|unlink)", "pathlib writes"),
    (r"\b(requests|urllib|httpx|socket)\b", "network access"),
    (r"\b__import__\b", "__import__"),
    (r"\beval\s*\(", "eval"),
    (r"\bexec\s*\(", "exec"),
]


def _check_blocked(code: str):
    """Return a description of the first blocked pattern found, or None."""
    for pattern, description in BLOCKED_PATTERNS:
        if re.search(pattern, code):
            return description
    return None


def run_python(code: str = "") -> str:
    """Execute Python code and return whatever it printed."""
    code = code.strip()
    if not code:
        return "Error: no code given."

    blocked = _check_blocked(code)
    if blocked:
        return (
            f"Refused to run: this code uses {blocked}, which isn't allowed. "
            "run_python is for calculations and data processing only. Use "
            "write_file or run_shell_command if you genuinely need to modify "
            "files or run programs — those have their own permission prompts."
        )

    # Run in a throwaway directory so relative paths can't reach the
    # project. Absolute paths would still work, which is why the pattern
    # blocking above matters too.
    workdir = None
    path = None
    try:
        workdir = tempfile.mkdtemp(prefix="jarvis_py_")
        path = os.path.join(workdir, "snippet.py")

        with open(path, "w", encoding="utf-8") as f:
            f.write(code)

        result = subprocess.run(
            [sys.executable, path],
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS,
            cwd=workdir,
        )

        output = result.stdout.strip()
        error = result.stderr.strip()

        if len(output) > MAX_OUTPUT_CHARS:
            output = output[:MAX_OUTPUT_CHARS] + "\n...[truncated]"

        if result.returncode != 0:
            return f"Code failed (exit {result.returncode}).\nstdout: {output}\nstderr: {error}"

        if not output:
            return "Code ran successfully but printed nothing. Remember to print() anything you want to see."

        return output

    except subprocess.TimeoutExpired:
        return f"Error: code timed out after {TIMEOUT_SECONDS} seconds."
    except Exception as e:
        return f"Error running code: {e}"
    finally:
        try:
            if path and os.path.exists(path):
                os.unlink(path)
            if workdir and os.path.isdir(workdir):
                os.rmdir(workdir)
        except OSError:
            pass


RUN_PYTHON_SCHEMA = {
    "name": "run_python",
    "description": (
        "Execute Python code and return whatever it prints. Use this for "
        "calculations, data processing, parsing, text generation, or any task "
        "where writing a few lines of code is more reliable than reasoning it "
        "out. You MUST print() anything you want to see — return values are "
        "not captured. Only the Python standard library is available, and file "
        "writes, subprocesses, and network access are blocked. If you need to "
        "write a file or run a command, use write_file or run_shell_command "
        "instead."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "code": {
                "type": "string",
                "description": "The Python code to run. Use print() to output results.",
            }
        },
        "required": ["code"],
    },
}