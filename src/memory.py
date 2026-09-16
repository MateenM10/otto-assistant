import json
import os
import tempfile
from datetime import datetime, timezone

MEMORY_PATH = "memory.json"
MAX_FACTS = 40  # capped because every fact goes into every system prompt

# A fact has to survive being read on its own, months later, with no
# conversation around it. Anything shorter than this was never going to.
MIN_FACT_LENGTH = 12
MAX_FACT_LENGTH = 200
MIN_FACT_WORDS = 3

# Models emit markdown bullets inside JSON strings despite being told not
# to. An unstripped prefix is how "- User" ended up in the system prompt.
_BULLET_PREFIXES = ("- ", "* ", "+ ", "• ", "– ", "— ")

# Two facts sharing this proportion of their words are treated as the same
# fact. Catches near-duplicates that exact matching misses.
_DUPLICATE_OVERLAP = 0.8


def _clean_fact(value) -> str:
    """Normalize a candidate fact, or return '' if it isn't usable."""
    if not isinstance(value, str):
        return ""

    fact = value.strip()

    # Strip repeatedly: models sometimes produce "- - fact"
    changed = True
    while changed:
        changed = False
        for prefix in _BULLET_PREFIXES:
            if fact.startswith(prefix):
                fact = fact[len(prefix):].strip()
                changed = True

    return " ".join(fact.split())


def _is_valid_fact(fact: str) -> bool:
    if not MIN_FACT_LENGTH <= len(fact) <= MAX_FACT_LENGTH:
        return False
    if len(fact.split()) < MIN_FACT_WORDS:
        return False
    return True


def _words(fact: str) -> set:
    return {w.strip(".,!?;:'\"").lower() for w in fact.split() if w.strip(".,!?;:'\"")}


def _is_duplicate(fact: str, existing: list) -> bool:
    """Exact match after normalizing, or heavy word overlap.

    Overlap catches the case exact matching misses: a run of near-identical
    facts about successive one-off requests, which is how memory filled up
    with noise before extraction was tightened.
    """
    lowered = fact.lower()
    new_words = _words(fact)

    for entry in existing:
        if entry.lower() == lowered:
            return True

        old_words = _words(entry)
        if not old_words or not new_words:
            continue

        overlap = len(new_words & old_words) / len(new_words | old_words)
        if overlap >= _DUPLICATE_OVERLAP:
            return True

    return False


def _load_raw() -> list:
    """Read stored facts, discarding anything malformed.

    Filtering on read as well as on write means an already-corrupted file
    can't poison the system prompt. The file used to have to be deleted by
    hand when that happened.
    """
    if not os.path.exists(MEMORY_PATH):
        return []

    try:
        with open(MEMORY_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return []

    if not isinstance(data, list):
        return []

    clean = []
    for entry in data:
        if not isinstance(entry, dict):
            continue
        fact = _clean_fact(entry.get("fact"))
        if not _is_valid_fact(fact):
            continue
        clean.append(
            {"fact": fact, "learned_at": entry.get("learned_at", "")}
        )

    # Repair the file if anything was dropped, so the same entries aren't
    # re-filtered on every single load.
    if len(clean) != len(data):
        try:
            _save_raw(clean)
        except OSError:
            pass

    return clean


def _save_raw(facts: list) -> None:
    """Write atomically.

    The old version truncated the file and then wrote, so an interrupt
    partway through left invalid JSON behind. Writing to a temp file and
    renaming means the real file is either the old contents or the new
    ones, never half of each.
    """
    directory = os.path.dirname(os.path.abspath(MEMORY_PATH)) or "."

    handle, temp_path = tempfile.mkstemp(dir=directory, suffix=".tmp")
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as f:
            json.dump(facts, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp_path, MEMORY_PATH)
    except Exception:
        if os.path.exists(temp_path):
            os.unlink(temp_path)
        raise


def get_all_facts() -> list:
    return [entry["fact"] for entry in _load_raw()]


def format_for_prompt() -> str:
    facts = get_all_facts()
    if not facts:
        return ""
    lines = "\n".join(f"- {fact}" for fact in facts)
    return f"\n\nThings you know about this user from previous conversations:\n{lines}"


def remember(fact: str) -> str:
    cleaned = _clean_fact(fact)

    if not cleaned:
        return "Nothing to remember — the fact was empty."

    if not _is_valid_fact(cleaned):
        return (
            f"Skipped '{cleaned}' — too short or vague to be useful later. "
            "Facts need to stand on their own without the conversation."
        )

    facts = _load_raw()
    existing = [entry["fact"] for entry in facts]

    if _is_duplicate(cleaned, existing):
        return f"Already remembered something like that: {cleaned}"

    facts.append(
        {"fact": cleaned, "learned_at": datetime.now(timezone.utc).isoformat()}
    )
    del facts[:-MAX_FACTS]
    _save_raw(facts)
    return f"Remembered: {cleaned}"


def remember_many(candidates: list) -> list:
    """Store several facts in one read/write cycle.

    Extraction produces a batch, and calling remember() per fact reloads
    and rewrites the whole file each time.
    """
    facts = _load_raw()
    existing = [entry["fact"] for entry in facts]
    now = datetime.now(timezone.utc).isoformat()
    stored = []

    for candidate in candidates:
        cleaned = _clean_fact(candidate)
        if not _is_valid_fact(cleaned):
            continue
        if _is_duplicate(cleaned, existing):
            continue

        facts.append({"fact": cleaned, "learned_at": now})
        existing.append(cleaned)
        stored.append(cleaned)

    if stored:
        del facts[:-MAX_FACTS]
        _save_raw(facts)

    return stored


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

The test: would this still be true and useful in a month, in a completely
different conversation? If not, do not store it.

Store things like: their name, where they work or study, what projects
they're building, tools they use, preferences about how they want things
done, recurring problems they face.

Do NOT store any of the following:
- Tasks the user asked you to do, or files they asked you to create.
  "User wants a notes.txt file on their Desktop" is a request you already
  handled, not a fact about them.
- Things you did for them during this conversation.
- Temporary state, such as what they are currently debugging.
- General facts about the world.
- Anything already in the known facts list below.

Each fact must be a complete sentence that stands on its own, at least
four words long, and must make sense to someone who never saw this
conversation. Never output a bare word or fragment.

Respond with ONLY a JSON array of strings, with no markdown formatting and
no bullet characters inside the strings. Most exchanges contain nothing
worth storing. When in doubt, store nothing and respond with: []

Example of good output:
["User's name is Alex", "User prefers concise answers", "User is building a React app called Bloom"]

Example of bad output, never produce this:
["User", "wants a file created", "asked about Python"]

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
        candidates = json.loads(raw)
    except json.JSONDecodeError:
        return []

    if not isinstance(candidates, list):
        return []

    return remember_many(candidates)