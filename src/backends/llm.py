import os

import requests
from dotenv import load_dotenv

load_dotenv()

MAX_RESPONSE_TOKENS = 400


class LLMBackend:
    """Common logic. Subclasses supply the endpoint, model, and headers."""

    url = ""
    model = ""

    def headers(self) -> dict:
        return {"Content-Type": "application/json"}

    def check_ready(self) -> str:
        """Return an error message if this backend can't be used, else ''."""
        return ""

    def chat(self, messages: list, tools: list) -> dict:
        """Send a conversation + tool list, return the raw message dict."""
        response = requests.post(
            self.url,
            headers=self.headers(),
            json={
                "model": self.model,
                "messages": messages,
                "tools": tools,
                "max_tokens": MAX_RESPONSE_TOKENS,
            },
            timeout=120,
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]


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
    model = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")

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
        raise ValueError(
            f"Unknown backend '{name}'. Options: {', '.join(BACKENDS)}"
        )
    return backend_class()