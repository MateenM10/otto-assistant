import json
import os
from datetime import datetime, timezone

MEMORY_PATH = "memory.json"
MAX_FACTS = 40  # capped because every fact goes into every system prompt


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
    return [entry["fact"] for entry in _load_raw()]


def format_for_prompt() -> str:
    facts = get_all_facts()
    if not facts:
        return ""
    lines = "\n".join(f"- {fact}" for fact in facts)
    return f"\n\nThings you know about this user from previous conversations:\n{lines}"


def remember(fact: str) -> str:
    fact = fact.strip()
    if not fact:
        return "Nothing to remember — the fact was empty."

    facts = _load_raw()

    existing = {entry["fact"].lower() for entry in facts}
    if fact.lower() in existing:
        return f"Already remembered: {fact}"

    facts.append(
        {"fact": fact, "learned_at": datetime.now(timezone.utc).isoformat()}
    )
    del facts[:-MAX_FACTS]
    _save_raw(facts)
    return f"Remembered: {fact}"


def forget(search: str) -> str:
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
    facts = get_all_facts()
    if not facts:
        return "I don't have any stored memories yet."
    return "Here's what I remember:\n" + "\n".join(f"- {f}" for f in facts)


EXTRACTION_PROMPT = """You review a conversation and decide whether anything
about the user is worth remembering long-term.

Store things like: their name, where they work or study, what projects
they're building, tools they use, preferences about how they want things
done, recurring problems they face.

Do NOT store: one-off questions, things you did for them, general facts
about the world, temporary state ("they're currently debugging X"), or
anything already in the known facts list below.

Respond with ONLY a JSON array of short standalone strings. Each string
must make sense on its own without the conversation. If nothing is worth
storing, respond with an empty array: []

Example output:
["User's name is Alex", "User prefers concise answers", "User is building a React app called Bloom"]

Known facts already stored (do not repeat these):
{known_facts}

Conversation to review:
{conversation}"""


def extract_facts(backend, user_message: str, assistant_reply: str) -> list:
    known = get_all_facts()
    known_text = "\n".join(f"- {f}" for f in known) if known else "(none yet)"

    conversation = f"User: {user_message}\nAssistant: {assistant_reply}"

    prompt = EXTRACTION_PROMPT.format(
        known_facts=known_text, conversation=conversation
    )

    try:
        message = backend.chat(
            [{"role": "user", "content": prompt}],
            tools=[],
        )
        raw = (message.get("content") or "").strip()
    except Exception:
        return []  # extraction is best-effort; never break the main flow

    # Models often wrap JSON in markdown fences despite instructions
    raw = raw.replace("```json", "").replace("```", "").strip()

    try:
        facts = json.loads(raw)
    except json.JSONDecodeError:
        return []

    if not isinstance(facts, list):
        return []

    stored = []
    for fact in facts:
        if isinstance(fact, str) and 3 < len(fact) < 200:
            remember(fact)
            stored.append(fact)

    return stored