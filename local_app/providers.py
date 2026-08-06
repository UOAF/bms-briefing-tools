from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any


Message = dict[str, str]


@dataclass
class ProviderResult:
    provider: str
    text: str


class LLMProviderError(RuntimeError):
    pass


class ChatProvider:
    name = "base"

    def available(self) -> bool:
        return False

    def chat(self, messages: list[Message], *, temperature: float = 0.2) -> ProviderResult:
        raise NotImplementedError


def post_json(url: str, payload: dict[str, Any], headers: dict[str, str] | None = None, timeout: int = 90) -> dict[str, Any]:
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json", **(headers or {})},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise LLMProviderError(f"{url} returned HTTP {exc.code}: {body[:800]}") from exc
    except OSError as exc:
        raise LLMProviderError(f"{url} unavailable: {exc}") from exc


class OpenAIProvider(ChatProvider):
    name = "openai"

    def __init__(self) -> None:
        self.api_key = os.environ.get("OPENAI_API_KEY", "")
        self.base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
        self.model = os.environ.get("OPENAI_MODEL", "gpt-4.1-mini")

    def available(self) -> bool:
        return bool(self.api_key)

    def chat(self, messages: list[Message], *, temperature: float = 0.2) -> ProviderResult:
        if not self.available():
            raise LLMProviderError("OPENAI_API_KEY is not set")
        payload = {"model": self.model, "messages": messages, "temperature": temperature}
        data = post_json(
            f"{self.base_url}/chat/completions",
            payload,
            headers={"Authorization": f"Bearer {self.api_key}"},
        )
        return ProviderResult(self.name, data["choices"][0]["message"]["content"])


class OllamaProvider(ChatProvider):
    name = "ollama"

    def __init__(self) -> None:
        self.base_url = os.environ.get("OLLAMA_OPENAI_BASE_URL", "http://localhost:11434/v1").rstrip("/")
        self.model = os.environ.get("OLLAMA_MODEL", "llama3.1:8b")

    def available(self) -> bool:
        try:
            with urllib.request.urlopen(f"{self.base_url}/models", timeout=2) as response:
                return response.status == 200
        except OSError:
            return False

    def chat(self, messages: list[Message], *, temperature: float = 0.2) -> ProviderResult:
        payload = {"model": self.model, "messages": messages, "temperature": temperature}
        data = post_json(f"{self.base_url}/chat/completions", payload)
        return ProviderResult(self.name, data["choices"][0]["message"]["content"])


class LMStudioProvider(ChatProvider):
    name = "lmstudio"

    def __init__(self) -> None:
        self.base_url = os.environ.get("LMSTUDIO_OPENAI_BASE_URL", "http://localhost:1234/v1").rstrip("/")
        self.model = os.environ.get("LMSTUDIO_MODEL", "local-model")

    def available(self) -> bool:
        try:
            with urllib.request.urlopen(f"{self.base_url}/models", timeout=2) as response:
                return response.status == 200
        except OSError:
            return False

    def chat(self, messages: list[Message], *, temperature: float = 0.2) -> ProviderResult:
        payload = {"model": self.model, "messages": messages, "temperature": temperature}
        data = post_json(f"{self.base_url}/chat/completions", payload)
        return ProviderResult(self.name, data["choices"][0]["message"]["content"])


class HeuristicProvider(ChatProvider):
    name = "offline-template"

    def available(self) -> bool:
        return True

    def chat(self, messages: list[Message], *, temperature: float = 0.2) -> ProviderResult:
        latest = next((m["content"] for m in reversed(messages) if m.get("role") == "user"), "")
        text = (
            "I do not have an LLM provider online, so I can still run the deterministic pipeline "
            "from the fields you provide. Put planner intent, package IDs, callsigns, named marks, "
            "comms, TACAN, and target priorities in the planner text box, then run the workflow.\n\n"
            f"Latest note captured:\n{latest.strip()}"
        )
        return ProviderResult(self.name, text)


class ProviderRouter:
    def __init__(self) -> None:
        self.providers: dict[str, ChatProvider] = {
            "openai": OpenAIProvider(),
            "ollama": OllamaProvider(),
            "lmstudio": LMStudioProvider(),
            "offline-template": HeuristicProvider(),
        }

    def status(self) -> dict[str, bool]:
        return {name: provider.available() for name, provider in self.providers.items()}

    def chat(self, messages: list[Message], *, requested: str = "auto", temperature: float = 0.2) -> ProviderResult:
        if requested != "auto":
            provider = self.providers.get(requested)
            if provider is None:
                raise LLMProviderError(f"Unknown provider: {requested}")
            return provider.chat(messages, temperature=temperature)
        for name in ("openai", "ollama", "lmstudio", "offline-template"):
            provider = self.providers[name]
            if provider.available():
                return provider.chat(messages, temperature=temperature)
        return self.providers["offline-template"].chat(messages, temperature=temperature)
