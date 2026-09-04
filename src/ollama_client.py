"""
Same chat loop as before, but now the model can call one real tool:
get_current_date. This proves the full tool-calling mechanic works
locally, before we build it properly into the real project.
"""

import requests
from datetime import date

OLLAMA_URL = "http://localhost:11434/v1/chat/completions"


# --- The actual tool ---
def get_current_date() -> str:
    return date.today().isoformat()


# --- Describing that tool to the model, in the shape Ollama expects ---
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_current_date",
            "description": "Get today's date.",
            "parameters": {"type": "object", "properties": {}},
        },
    }
]

messages = []

print("Chatting with local model (now with a date tool). Type 'exit' to quit.\n")

while True:
    user_input = input("You: ").strip()
    if user_input.lower() in ("exit", "quit"):
        print("Goodbye.")
        break
    if not user_input:
        continue

    messages.append({"role": "user", "content": user_input})

    response = requests.post(
        OLLAMA_URL,
        json={"model": "llama3.2:3b", "messages": messages, "tools": TOOLS},
    )
    data = response.json()
    message = data["choices"][0]["message"]

    # Did the model ask to use a tool instead of answering directly?
    if message.get("tool_calls"):
        # Save the model's tool request in the conversation history
        messages.append(message)

        for tool_call in message["tool_calls"]:
            print(f"\n[Jarvis is using tool]: {tool_call['function']['name']}")

            # We only have one tool right now, so no need to check the name yet
            result = get_current_date()

            # Send the result back so the model can use it in its answer
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call["id"],
                    "content": result,
                }
            )

        # Ask the model again, now that it has the tool result
        response = requests.post(
            OLLAMA_URL,
            json={"model": "llama3.2:3b", "messages": messages, "tools": TOOLS},
        )
        data = response.json()
        message = data["choices"][0]["message"]

    reply = message.get("content") or ""
    print(f"\nJarvis: {reply}\n")
    messages.append({"role": "assistant", "content": reply})