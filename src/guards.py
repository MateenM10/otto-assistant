import re

# Patterns that indicate code or a command would do something the
# dedicated tools should handle instead, or something with no safe
# undo. File operations belong in write_file / delete_file, which are
# directory-scoped and permissioned.

PYTHON_BLOCKED = [
    (r"\bopen\s*\([^)]*['\"][wax]", "opening a file in write/append mode"),
    (r"\bos\.(remove|unlink|rmdir|rename|system)\b", "os file/system operations"),
    (r"\bshutil\.(rmtree|move|copy)", "shutil file operations"),
    (r"\bsubprocess\b", "subprocess"),
    (r"\bPath\s*\([^)]*\)\s*\.(write_text|write_bytes|unlink)", "pathlib writes"),
    (r"\b(requests|urllib|httpx|socket)\b", "network access"),
    (r"\b__import__\b", "__import__"),
    (r"\beval\s*\(", "eval"),
    (r"\bexec\s*\(", "exec"),
]

SHELL_BLOCKED = [
    (r"\brm\b", "rm — use the delete_file tool instead"),
    (r"\brmdir\b", "rmdir — use the delete_file tool instead"),
    (r"\bsudo\b", "sudo"),
    (r"\bdd\b", "dd"),
    (r"\bmkfs\b", "mkfs"),
    (r"\bshutdown\b", "shutdown"),
    (r"\breboot\b", "reboot"),
    (r"\bchmod\s+-R\b", "recursive chmod"),
    (r"\bchown\s+-R\b", "recursive chown"),
    (r">\s*/", "redirecting output to an absolute path"),
]

GUARDED_TOOLS = {
    "run_python": ("code", PYTHON_BLOCKED),
    "run_shell_command": ("command", SHELL_BLOCKED),
}


def check(tool_name: str, args: dict):
    """Return a refusal message if this call is blocked, else None."""
    guard = GUARDED_TOOLS.get(tool_name)
    if guard is None:
        return None

    arg_name, patterns = guard
    text = str(args.get(arg_name, ""))
    if not text:
        return None

    for pattern, description in patterns:
        if re.search(pattern, text):
            return (
                f"Refused: this uses {description}, which is blocked. "
                "If a dedicated tool exists for what you're trying to do, use "
                "that. Otherwise tell the user what you wanted to do and let "
                "them run it themselves."
            )
    return None