import json
import os

import requests
from dotenv import load_dotenv

load_dotenv()

MAX_RESPONSE_TOKENS = 400


class LLMBackend:
    url = ""
    model = ""

    def headers(self) -> dict:
        return {"Content-Type": "application/json"}

    def check_ready(self) -> str:
        """Return an error message if this backend can't be used, else ''."""
        return ""

    def chat(self, messages: list, tools: list, on_text=None) -> dict:
        """Send a conversation and return the assistant's message dict.

        If on_text is given, the response is streamed and on_text is
        called with the accumulated text so far as each piece arrives.
        Either way the return value has the same shape, so callers that
        don't care about streaming don't have to change.
        """
        if on_text is None:
            return self._chat_blocking(messages, tools)
        return self._chat_streaming(messages, tools, on_text)

    def _payload(self, messages: list, tools: list, stream: bool) -> dict:
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": MAX_RESPONSE_TOKENS,
        }
        # Some APIs reject an empty tools array, and the memory
        # extraction call deliberately passes none.
        if tools:
            payload["tools"] = tools
        if stream:
            payload["stream"] = True
        return payload

    def _chat_blocking(self, messages: list, tools: list) -> dict:
        response = requests.post(
            self.url,
            headers=self.headers(),
            json=self._payload(messages, tools, stream=False),
            timeout=120,
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]

    def _chat_streaming(self, messages: list, tools: list, on_text) -> dict:
        response = requests.post(
            self.url,
            headers=self.headers(),
            json=self._payload(messages, tools, stream=True),
            timeout=120,
            stream=True,
        )
        response.raise_for_status()

        content_parts = []
        # Tool calls arrive in fragments keyed by index: the id and name
        # come early, then the arguments JSON streams in pieces that
        # have to be concatenated.
        partial_tool_calls = {}

        for raw_line in response.iter_lines():
            if not raw_line:
                continue
            line = raw_line.decode("utf-8")
            if not line.startswith("data: "):
                continue

            data = line[6:]
            if data.strip() == "[DONE]":
                break

            try:
                chunk = json.loads(data)
            except json.JSONDecodeError:
                continue

            choices = chunk.get("choices") or []
            if not choices:
                continue
            delta = choices[0].get("delta") or {}

            text = delta.get("content")
            if text:
                content_parts.append(text)
                on_text("".join(content_parts))

            for fragment in delta.get("tool_calls") or []:
                index = fragment.get("index", 0)
                call = partial_tool_calls.setdefault(
                    index,
                    {
                        "id": "",
                        "type": "function",
                        "function": {"name": "", "arguments": ""},
                    },
                )
                if fragment.get("id"):
                    call["id"] = fragment["id"]
                function = fragment.get("function") or {}
                if function.get("name"):
                    call["function"]["name"] = function["name"]
                if function.get("arguments"):
                    call["function"]["arguments"] += function["arguments"]

        content = "".join(content_parts)
        message = {"role": "assistant", "content": content or None}

        if partial_tool_calls:
            message["tool_calls"] = [
                partial_tool_calls[i] for i in sorted(partial_tool_calls)
            ]

        return message


class OllamaBackend(LLMBackend):
    url = "http://localhost:11434/v1/chat/completions"
    model = os.environ.get("OLLAMA_MODEL", "llama3.2:3b")

    def check_ready(self) -> str:
        try:
            requests.get("http://localhost:11434/api/tags", timeout=3)
        except requests.RequestException:
            return "Ollama doesn't appear to be running. Start the Ollama app and try again."
        return ""


class GroqBackend(LLMBackend):
    url = "https://api.groq.com/openai/v1/chat/completions"
    model = os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")

    def headers(self) -> dict:
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {os.environ.get('GROQ_API_KEY', '')}",
        }

    def check_ready(self) -> str:
        if not os.environ.get("GROQ_API_KEY"):
            return "GROQ_API_KEY not found in .env. Get a free key at console.groq.com."
        return ""


BACKENDS = {
    "ollama": OllamaBackend,
    "groq": GroqBackend,
}


def build_backend(name: str = None) -> LLMBackend:
    """Create the configured backend. Defaults to LLM_BACKEND in .env."""
    name = (name or os.environ.get("LLM_BACKEND", "ollama")).lower()
    backend_class = BACKENDS.get(name)
    if backend_class is None:
        raise ValueError(f"Unknown backend '{name}'. Options: {', '.join(BACKENDS)}")
    return backend_class()