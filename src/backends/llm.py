import json
import os
import time

import requests
from dotenv import load_dotenv

load_dotenv()

# Tunable without a code change, since the right ceiling depends on the
# provider's per-minute token budget. Reasoning models spend part of this
# thinking, so dropping it too far starves the actual reply.
MAX_RESPONSE_TOKENS = int(os.environ.get("MAX_RESPONSE_TOKENS", "600"))

# Providers count the max_tokens reservation against a per-minute token
# budget, so a burst of tool calls can exhaust it in seconds. A short
# wait clears it, so a 429 is worth retrying rather than surfacing.
MAX_RATE_LIMIT_RETRIES = 2
MAX_RETRY_WAIT = 30.0


class LLMBackend:
    url = ""
    model = ""
    # Set on backends whose models reason before replying. Reasoning
    # tokens come out of the same budget as the reply, so these models
    # need an effort setting to keep the thinking affordable.
    reasoning_effort = ""

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
        if self.reasoning_effort:
            payload["reasoning_effort"] = self.reasoning_effort
        return payload

    def _as_reply(self, text: str) -> dict:
        return {"role": "assistant", "content": text}

    def _retry_after(self, response) -> float:
        """Seconds to wait before retrying, or 0 if the provider didn't say."""
        try:
            return float(response.headers.get("retry-after", ""))
        except ValueError:
            return 0.0

    def _error_reply(self, response) -> dict:
        """Turn an HTTP error into a normal assistant reply.

        A failed request used to raise straight through the main loop and
        kill the process. The provider puts useful detail in the body,
        especially for rate limits, so it gets surfaced rather than
        thrown away by raise_for_status.
        """
        try:
            detail = (response.json().get("error") or {}).get("message", "")
        except ValueError:
            detail = response.text[:300]

        if response.status_code == 429:
            return self._as_reply(
                "I'm being rate limited by the model provider and waiting "
                f"didn't clear it. {detail}".strip()
            )

        if response.status_code in (401, 403):
            return self._as_reply(
                f"The model provider rejected the API key ({response.status_code}). "
                f"Check the key in .env. {detail}".strip()
            )

        return self._as_reply(
            f"The model provider returned an error ({response.status_code}). "
            f"{detail}".strip()
        )

    def _post(self, messages: list, tools: list, stream: bool, notify=None):
        """Returns (response, error_reply). Exactly one of them will be set.

        Retries on rate limits using the provider's own retry-after hint,
        which is accurate to the fraction of a second, so there's no need
        to guess at a backoff schedule.
        """
        for attempt in range(MAX_RATE_LIMIT_RETRIES + 1):
            try:
                response = requests.post(
                    self.url,
                    headers=self.headers(),
                    json=self._payload(messages, tools, stream=stream),
                    timeout=120,
                    stream=stream,
                )
            except requests.Timeout:
                return None, self._as_reply(
                    "The model took too long to respond and the request timed out."
                )
            except requests.RequestException as e:
                return None, self._as_reply(f"Couldn't reach the model backend: {e}")

            if response.status_code != 429:
                break

            wait = self._retry_after(response)
            if attempt == MAX_RATE_LIMIT_RETRIES or wait <= 0 or wait > MAX_RETRY_WAIT:
                break

            if notify:
                notify(f"Rate limited. Waiting {wait:.0f}s before trying again…")
            response.close()
            time.sleep(wait + 0.5)

        if response.status_code >= 400:
            return None, self._error_reply(response)

        return response, None

    def _finalize(self, content: str, tool_calls: list, finish_reason: str,
                  reasoning: str) -> dict:
        """Build the message dict, converting a silent empty response into
        something the user can actually see.

        A reasoning model can spend its whole token budget thinking and
        return nothing at all. Left alone that surfaces as a blank reply
        with no error anywhere, which is impossible to debug from the
        outside, so it gets turned into a real message instead.
        """
        message = {"role": "assistant", "content": content or None}

        if tool_calls:
            message["tool_calls"] = tool_calls
            return message

        if content:
            return message

        if finish_reason == "length":
            message["content"] = (
                "I ran out of room before I could finish that reply. "
                "Try asking for something shorter, or raise MAX_RESPONSE_TOKENS "
                "in .env."
            )
        elif reasoning:
            message["content"] = (
                "I worked that through but didn't produce a reply. Ask me again."
            )
        else:
            message["content"] = (
                "I didn't get a response back from the model. Try again."
            )

        return message

    def _chat_blocking(self, messages: list, tools: list) -> dict:
        response, error = self._post(messages, tools, stream=False)
        if error:
            return error

        choice = response.json()["choices"][0]
        message = choice["message"]

        return self._finalize(
            message.get("content") or "",
            message.get("tool_calls") or [],
            choice.get("finish_reason") or "",
            message.get("reasoning") or "",
        )

    def _chat_streaming(self, messages: list, tools: list, on_text) -> dict:
        response, error = self._post(messages, tools, stream=True, notify=on_text)
        if error:
            return error

        content_parts = []
        # Reasoning models stream their thinking in a separate field.
        # It never goes to the user, but it gets collected so an empty
        # reply can be told apart from no response at all.
        reasoning_parts = []
        finish_reason = ""
        # Tool calls arrive in fragments keyed by index: the id and name
        # come early, then the arguments JSON streams in pieces that
        # have to be concatenated.
        partial_tool_calls = {}

        try:
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

                if choices[0].get("finish_reason"):
                    finish_reason = choices[0]["finish_reason"]

                delta = choices[0].get("delta") or {}

                text = delta.get("content")
                if text:
                    content_parts.append(text)
                    on_text("".join(content_parts))

                thinking = delta.get("reasoning")
                if thinking:
                    reasoning_parts.append(thinking)

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
        except requests.RequestException as e:
            # The connection can drop partway through a stream. Anything
            # that arrived before that is still worth keeping.
            if not content_parts and not partial_tool_calls:
                return self._as_reply(f"The connection to the model dropped: {e}")

        tool_calls = [partial_tool_calls[i] for i in sorted(partial_tool_calls)]

        return self._finalize(
            "".join(content_parts),
            tool_calls,
            finish_reason,
            "".join(reasoning_parts),
        )


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
    # gpt-oss reasons before answering and the thinking is billed against
    # the same max_tokens as the reply. Low effort keeps enough of the
    # budget for the actual answer, which is what the assistant needs
    # when it has to write file contents.
    reasoning_effort = os.environ.get("GROQ_REASONING_EFFORT", "low")

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