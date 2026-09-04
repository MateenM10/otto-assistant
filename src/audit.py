import json
from datetime import datetime, timezone

LOG_PATH = "audit_log.jsonl"


def log_tool_call(name: str, arguments: dict, result: str, allowed: bool) -> None:
    """Append one record of a tool call to the audit log file."""
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "tool": name,
        "arguments": arguments,
        "allowed": allowed,
        "result_preview": result[:200],  # keep the log file readable, not huge
    }
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")