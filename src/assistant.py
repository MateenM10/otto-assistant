import os
from anthropic import Anthropic
from dotenv import load_dotenv

from .tools import TOOL_FUNCTIONS, TOOL_SCHEMAS

load_dotenv()

MODEL = "claude-sonnet-4-5"
MAX_TOKENS = 1024

SYSTEM_PROMPT = """You are Jarvis, a personal assistant that helps the user
with tasks on their computer. You have tools to read files, list
directories, and run shell commands. Use tools when you need real
information instead of guessing. Be concise and direct in your replies."""


class Assistant:
    def __init__(self):
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY not found. Did you create a .env file from .env.example?"
            )
        self.client = Anthropic(api_key=api_key)
        self.messages = []  # full conversation history

    def send(self, user_input: str) -> str:
        """Send a user message, run the tool loop, return the final text reply."""
        self.messages.append({"role": "user", "content": user_input})

        while True:
            response = self.client.messages.create(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                system=SYSTEM_PROMPT,
                tools=TOOL_SCHEMAS,
                messages=self.messages,
            )

            # Save Claude's reply (may contain text and/or tool_use blocks)
            self.messages.append({"role": "assistant", "content": response.content})

            if response.stop_reason != "tool_use":
                # Claude gave a final answer — extract and return the text
                return self._extract_text(response.content)

            # Claude wants to use one or more tools. Run each and collect results.
            tool_results = []
            for block in response.content:
                if block.type != "tool_use":
                    continue
                result_text = self._run_tool(block.name, block.input)
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result_text,
                    }
                )

            # Send tool results back so Claude can continue reasoning
            self.messages.append({"role": "user", "content": tool_results})

    def _run_tool(self, name: str, tool_input: dict) -> str:
        func = TOOL_FUNCTIONS.get(name)
        if func is None:
            return f"Error: unknown tool '{name}'"
        try:
            return str(func(**tool_input))
        except Exception as e:
            return f"Error running tool '{name}': {e}"

    @staticmethod
    def _extract_text(content_blocks) -> str:
        text_parts = [b.text for b in content_blocks if b.type == "text"]
        return "\n".join(text_parts).strip()