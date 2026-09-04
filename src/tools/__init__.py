from .file_tools import read_file, list_directory, READ_FILE_SCHEMA, LIST_DIRECTORY_SCHEMA
from .shell_tools import run_shell_command, RUN_SHELL_COMMAND_SCHEMA

# Maps tool name -> the actual Python function to call
TOOL_FUNCTIONS = {
    "read_file": read_file,
    "list_directory": list_directory,
    "run_shell_command": run_shell_command,
}

# List of schemas sent to Claude so it knows what tools exist
TOOL_SCHEMAS = [
    READ_FILE_SCHEMA,
    LIST_DIRECTORY_SCHEMA,
    RUN_SHELL_COMMAND_SCHEMA,
]