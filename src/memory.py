import json
import os
from datetime import datetime, timezone

MEMORY_PATH = "memory.json"
MAX_FACTS = 100  # cap so the system prompt doesn't grow unbounded


def _load_raw() -> list:
    if not os.path.exists(MEMORY_PATH):
        return []
    try:
        with open(MEMORY_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def _save_raw(facts: list) -> None:
    with open(MEMORY_PATH, "w", encoding="utf-8") as f:
        json.dump(facts, f, indent=2)


def get_all_facts() -> list:
    """Return just the fact strings, for injecting into the prompt."""
    return [entry["fact"] for entry in _load_raw()]


def format_for_prompt() -> str:
    """Render stored facts as a block to append to the system prompt."""
    facts = get_all_facts()
    if not facts:
        return ""
    lines = "\n".join(f"- {fact}" for fact in facts)
    return f"\n\nThings you know about this user from previous conversations:\n{lines}"


def remember(fact: str) -> str:
    """Store a new fact about the user."""
    fact = fact.strip()
    if not fact:
        return "Nothing to remember — the fact was empty."

    facts = _load_raw()

    # Avoid storing near-duplicates of things we already know
    existing = {entry["fact"].lower() for entry in facts}
    if fact.lower() in existing:
        return f"Already remembered: {fact}"

    facts.append(
        {"fact": fact, "learned_at": datetime.now(timezone.utc).isoformat()}
    )
    del facts[:-MAX_FACTS]  # keep only the most recent MAX_FACTS
    _save_raw(facts)
    return f"Remembered: {fact}"


def forget(search: str) -> str:
    """Remove any facts containing the given text."""
    search = search.strip().lower()
    if not search:
        return "Nothing to forget — no search text given."

    facts = _load_raw()
    kept = [e for e in facts if search not in e["fact"].lower()]
    removed = len(facts) - len(kept)

    if removed == 0:
        return f"No stored facts matched '{search}'."

    _save_raw(kept)
    return f"Forgot {removed} fact(s) matching '{search}'."


def recall() -> str:
    """List everything currently remembered."""
    facts = get_all_facts()
    if not facts:
        return "I don't have any stored memories yet."
    return "Here's what I remember:\n" + "\n".join(f"- {f}" for f in facts)