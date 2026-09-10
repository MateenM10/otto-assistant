import os
import shutil

from ..scope import check_writable

MAX_FILE_CHARS = 8000


def read_file(path: str) -> str:
    """Read a text file and return its contents (truncated if large)."""
    try:
        expanded = os.path.expanduser(path)
        with open(expanded, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        if len(content) > MAX_FILE_CHARS:
            content = content[:MAX_FILE_CHARS] + "\n...[truncated]"
        return content
    except FileNotFoundError:
        return f"Error: file not found at '{path}'"
    except IsADirectoryError:
        return f"Error: '{path}' is a directory, not a file"
    except Exception as e:
        return f"Error reading file: {e}"


def list_directory(path: str = ".") -> str:
    """List files and folders in a directory."""
    try:
        expanded = os.path.expanduser(path)
        entries = sorted(os.listdir(expanded))
        if not entries:
            return f"'{path}' is empty."
        lines = []
        for entry in entries:
            full = os.path.join(expanded, entry)
            marker = "/" if os.path.isdir(full) else ""
            lines.append(f"{entry}{marker}")
        return "\n".join(lines)
    except FileNotFoundError:
        return f"Error: directory not found at '{path}'"
    except NotADirectoryError:
        return f"Error: '{path}' is a file, not a directory"
    except Exception as e:
        return f"Error listing directory: {e}"


def write_file(path: str, content: str) -> str:
    """Write text content to a file, creating or overwriting it."""
    refusal = check_writable(path)
    if refusal:
        return refusal

    try:
        expanded = os.path.expanduser(path)
        existed = os.path.exists(expanded)
        with open(expanded, "w", encoding="utf-8") as f:
            f.write(content)
        verb = "Overwrote" if existed else "Created"
        return f"{verb} '{path}' ({len(content)} characters)"
    except Exception as e:
        return f"Error writing file: {e}"


def delete_file(path: str) -> str:
    """Move a file or folder to the macOS Trash.

    Trash rather than permanent deletion, so mistakes are recoverable.
    """
    refusal = check_writable(path)
    if refusal:
        return refusal

    try:
        expanded = os.path.expanduser(path)
        if not os.path.exists(expanded):
            return f"Error: nothing found at '{path}'"

        trash = os.path.expanduser("~/.Trash")
        name = os.path.basename(expanded.rstrip("/"))
        destination = os.path.join(trash, name)

        # Don't clobber something already in the Trash with the same name
        counter = 1
        while os.path.exists(destination):
            stem, ext = os.path.splitext(name)
            destination = os.path.join(trash, f"{stem} {counter}{ext}")
            counter += 1

        shutil.move(expanded, destination)
        return f"Moved '{path}' to the Trash. It can be restored from there."
    except Exception as e:
        return f"Error deleting: {e}"


READ_FILE_SCHEMA = {
    "name": "read_file",
    "description": "Read the contents of a text file at a given path.",
    "input_schema": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Path to the file, absolute or relative to the current working directory.",
            }
        },
        "required": ["path"],
    },
}

LIST_DIRECTORY_SCHEMA = {
    "name": "list_directory",
    "description": "List the files and subdirectories inside a given directory.",
    "input_schema": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Directory path to list. Defaults to the current directory if omitted.",
            }
        },
        "required": [],
    },
}

WRITE_FILE_SCHEMA = {
    "name": "write_file",
    "description": (
        "Write text content to a file, creating it or overwriting what's "
        "there. Only works inside directories Jarvis is allowed to modify. "
        "To edit an existing file, read it first, then write back the full "
        "modified contents."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Path to the file to write.",
            },
            "content": {
                "type": "string",
                "description": "The full text content to write into the file.",
            },
        },
        "required": ["path", "content"],
    },
}

DELETE_FILE_SCHEMA = {
    "name": "delete_file",
    "description": (
        "Move a file or folder to the Trash. Only works inside directories "
        "Jarvis is allowed to modify. Files go to the Trash rather than being "
        "permanently erased, so they can be restored."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Path to the file or folder to move to the Trash.",
            }
        },
        "required": ["path"],
    },
}