from ..memory import remember as _remember, forget as _forget, recall as _recall


def remember(fact: str) -> str:
    return _remember(fact)


def forget(search: str) -> str:
    return _forget(search)


def recall() -> str:
    return _recall()


REMEMBER_SCHEMA = {
    "name": "remember",
    "description": (
        "Store a fact about the user so it persists across sessions. Use this "
        "whenever the user shares something worth remembering long-term: their "
        "name, preferences, what they're working on, how they like things done."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "fact": {
                "type": "string",
                "description": "The fact to remember, written as a short standalone statement, e.g. 'User's name is Mateen' or 'User is building a JARVIS-style assistant in Python'.",
            }
        },
        "required": ["fact"],
    },
}

FORGET_SCHEMA = {
    "name": "forget",
    "description": "Remove stored facts matching some text. Use when the user asks you to forget something or corrects outdated information.",
    "input_schema": {
        "type": "object",
        "properties": {
            "search": {
                "type": "string",
                "description": "Text to match against stored facts. Any fact containing this text is removed.",
            }
        },
        "required": ["search"],
    },
}

RECALL_SCHEMA = {
    "name": "recall",
    "description": "List everything currently stored in long-term memory about the user.",
    "input_schema": {
        "type": "object",
        "properties": {},
        "required": [],
    },
}