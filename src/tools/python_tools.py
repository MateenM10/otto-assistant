import os
import subprocess
import sys
import tempfile

TIMEOUT_SECONDS = 30
MAX_OUTPUT_CHARS = 4000


def run_python(code: str = "") -> str:
    """Execute Python code and return whatever it printed."""
    code = code.strip()
    if not code:
        return "Error: no code given."

    # Run in a throwaway directory so relative paths can't reach the
    # project. Pattern blocking happens earlier, in assistant.py.
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
        "writes, subprocesses, and network access are blocked."
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