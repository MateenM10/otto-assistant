from .vision_tools import read_screen, READ_SCREEN_SCHEMA
from .search_tools import search_web, SEARCH_WEB_SCHEMA
from .memory_tools import (
    remember,
    forget,
    recall,
    REMEMBER_SCHEMA,
    FORGET_SCHEMA,
    RECALL_SCHEMA,
)
from .file_tools import (
    read_file,
    list_directory,
    write_file,
    READ_FILE_SCHEMA,
    LIST_DIRECTORY_SCHEMA,
    WRITE_FILE_SCHEMA,
)
from .shell_tools import (
    run_shell_command,
    get_current_datetime,
    RUN_SHELL_COMMAND_SCHEMA,
    GET_CURRENT_DATETIME_SCHEMA,
)

# 1. Maps tool name -> the actual Python function to call
TOOL_FUNCTIONS = {
    "read_file": read_file,
    "list_directory": list_directory,
    "write_file": write_file,
    "run_shell_command": run_shell_command,
    "get_current_datetime": get_current_datetime,
    "read_screen": read_screen,
    "search_web": search_web,
    "remember": remember,
    "forget": forget,
    "recall": recall,
}

# 2. Schemas sent to the model so it knows what tools exist
TOOL_SCHEMAS = [
    READ_FILE_SCHEMA,
    LIST_DIRECTORY_SCHEMA,
    WRITE_FILE_SCHEMA,
    RUN_SHELL_COMMAND_SCHEMA,
    GET_CURRENT_DATETIME_SCHEMA,
    READ_SCREEN_SCHEMA,
    SEARCH_WEB_SCHEMA,
    REMEMBER_SCHEMA,
    FORGET_SCHEMA,
    RECALL_SCHEMA,
]

# 3. Trust tiers: "safe" tools run instantly, "confirm" tools always ask
# the user first. This is the ONE place that decides which is which —
# individual tool files no longer handle their own confirmation.
TOOL_TRUST = {
    "read_file": "safe",
    "list_directory": "safe",
    "write_file": "confirm",
    "run_shell_command": "confirm",
    "get_current_datetime": "safe",
    "read_screen": "safe",
    "search_web": "safe",
    "remember": "safe",
    "recall": "safe",
    "forget": "confirm",  # destructive — ask before deleting memories
}