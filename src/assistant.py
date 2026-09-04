import requests
from .tools import TOOL_FUNCTIONS, TOOL_SCHEMAS

OLLAMA_URL = "http://localhost:11434/v1/chat/completions"
MODEL = "llama3.2:3b"

SYSTEM_PROMPT = """You are Jarvis, a personal assistant that helps the user
with tasks on their computer. You have tools to read files, list
directories, write files, and run shell commands.

IMPORTANT: When the user asks about files, directories, or anything
you could check with a tool, you MUST call the tool yourself and use
its real result. Never just explain what command they could run —
actually run it using your tools and give them the real answer."""

def _to_ollama_tool(schema: dict) -> dict:
    """Our tool files describe tools in Claude's shape. Ollama wants
    them wrapped differently, so we convert here in one place instead
    of rewriting every tool file."""
    return {
        "type": "function",
        "function": {
            "name": schema["name"],
            "description": schema["description"],
            "parameters": schema["input_schema"],
        },
    }


class Assistant:
    def __init__(self):
        self.messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        self.ollama_tools = [_to_ollama_tool(s) for s in TOOL_SCHEMAS]

    def send(self, user_input: str) -> str:
        self.messages.append({"role": "user", "content": user_input})

        while True:
            response = requests.post(
                OLLAMA_URL,
                json={
                    "model": MODEL,
                    "messages": self.messages,
                    "tools": self.ollama_tools,
                },
            )
            data = response.json()
            message = data["choices"][0]["message"]

            if not message.get("tool_calls"):
                reply = message.get("content") or ""
                self.messages.append({"role": "assistant", "content": reply})
                return reply

            # Model wants to use one or more tools
            self.messages.append(message)

            for tool_call in message["tool_calls"]:
                name = tool_call["function"]["name"]
                result = self._run_tool(name, tool_call["function"]["arguments"])
                self.messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call["id"],
                        "content": result,
                    }
                )
            # loop back around and call Ollama again with the tool results

    def _run_tool(self, name: str, raw_arguments) -> str:
        import json

        func = TOOL_FUNCTIONS.get(name)
        if func is None:
            return f"Error: unknown tool '{name}'"

        # Ollama sometimes sends arguments as a JSON string, sometimes
        # already as a dict — handle both
        if isinstance(raw_arguments, str):
            try:
                args = json.loads(raw_arguments)
            except json.JSONDecodeError:
                args = {}
        else:
            args = raw_arguments or {}

        try:
            return str(func(**args))
        except Exception as e:
            return f"Error running tool '{name}': {e}"