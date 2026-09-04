import os

MAX_FILE_CHARS = 8000  # keep responses small; avoid dumping huge files


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
    try:
        expanded = os.path.expanduser(path)
        with open(expanded, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Successfully wrote {len(content)} characters to '{path}'"
    except Exception as e:
        return f"Error writing file: {e}"


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
    "description": "Write text content to a file at the given path, creating or overwriting it.",
    "input_schema": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Path to the file to write, absolute or relative to the current working directory.",
            },
            "content": {
                "type": "string",
                "description": "The text content to write into the file.",
            },
        },
        "required": ["path", "content"],
    },
}