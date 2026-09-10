import os

# Directories the assistant is allowed to create, modify, or delete
# files in. Everything else is read-only. Paths are expanded and
# resolved, so symlinks and ~ can't be used to escape.
ALLOWED_WRITE_DIRS = [
    os.getcwd(),  # the project directory Jarvis was started from
    os.path.expanduser("~/Desktop"),
    os.path.expanduser("~/Downloads"),
]

# Files that must never be modified even inside allowed directories,
# because breaking them breaks the assistant or leaks secrets.
PROTECTED_NAMES = {
    ".env",
    "memory.json",
    "audit_log.jsonl",
}


def _resolve(path: str) -> str:
    return os.path.realpath(os.path.expanduser(path))


def check_writable(path: str):
    """Return a refusal message if this path can't be written, else None."""
    resolved = _resolve(path)

    if os.path.basename(resolved) in PROTECTED_NAMES:
        return (
            f"Refused: '{os.path.basename(resolved)}' is protected and cannot "
            "be modified or deleted."
        )

    for allowed in ALLOWED_WRITE_DIRS:
        allowed_resolved = _resolve(allowed)
        # commonpath raises if the paths are on different drives
        try:
            if os.path.commonpath([resolved, allowed_resolved]) == allowed_resolved:
                return None
        except ValueError:
            continue

    readable = "\n".join(f"  {d}" for d in ALLOWED_WRITE_DIRS)
    return (
        f"Refused: '{path}' is outside the directories Jarvis can modify.\n"
        f"Writable locations are:\n{readable}"
    )


def describe_scope() -> str:
    return "\n".join(f"- {d}" for d in ALLOWED_WRITE_DIRS)