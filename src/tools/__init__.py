from .file_tools import (
    read_file,
    list_directory,
    write_file,
    READ_FILE_SCHEMA,
    LIST_DIRECTORY_SCHEMA,
    WRITE_FILE_SCHEMA,
)
from .shell_tools import run_shell_command, RUN_SHELL_COMMAND_SCHEMA

# Maps tool name -> the actual Python function to call
TOOL_FUNCTIONS = {
    "read_file": read_file,
    "list_directory": list_directory,
    "write_file": write_file,
    "run_shell_command": run_shell_command,
}

# List of schemas sent to the model so it knows what tools exist
TOOL_SCHEMAS = [
    READ_FILE_SCHEMA,
    LIST_DIRECTORY_SCHEMA,
    WRITE_FILE_SCHEMA,
    RUN_SHELL_COMMAND_SCHEMA,
]