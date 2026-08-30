"""Provider adapters.

One interface, three backends, selected by JUDGE_PROVIDER. Adding a provider is one
class. Multi-provider matters twice: it separates judge variance from service variance
now, and it is the substrate for the peer prediction layer later.

No key is needed to import or test anything here; only .complete() calls out.
"""
from __future__ import annotations

import json
import os
import time
import urllib.request
import urllib.error
from dataclasses import dataclass


@dataclass
class Completion:
    text: str
    model: str
    provider: str
    latency_ms: int


class ProviderError(RuntimeError):
    pass


class Provider:
    name = "base"
    default_model = ""

    def __init__(self, model: str | None = None, api_key: str | None = None,
                 temperature: float = 0.0, max_attempts: int = 4):
        self.model = model or self.default_model
        self.api_key = api_key or os.environ.get(self.key_env)
        self.temperature = temperature
        self.max_attempts = max_attempts

    def available(self) -> bool:
        return bool(self.api_key)

    def _post(self, url: str, payload: dict, headers: dict) -> dict:
        body = json.dumps(payload).encode()
        last = None
        for attempt in range(self.max_attempts):
            req = urllib.request.Request(url, data=body, headers=headers, method="POST")
            try:
                with urllib.request.urlopen(req, timeout=120) as r:
                    return json.load(r)
            except urllib.error.HTTPError as e:
                detail = e.read().decode()[:400]
                if e.code in (429, 500, 502, 503, 529):
                    last = ProviderError(f"HTTP {e.code}: {detail}")
                    time.sleep(2.0 * (attempt + 1))
                    continue
                raise ProviderError(f"HTTP {e.code}: {detail}") from e
            except Exception as e:
                last = e
                time.sleep(1.5 * (attempt + 1))
        raise ProviderError(f"failed after {self.max_attempts} attempts: {last}")

    def complete(self, system: str, user: str) -> Completion:
        raise NotImplementedError


class Anthropic(Provider):
    name = "anthropic"
    key_env = "ANTHROPIC_API_KEY"
    default_model = "claude-sonnet-4-6"

    def complete(self, system: str, user: str) -> Completion:
        t0 = time.time()
        d = self._post(
            "https://api.anthropic.com/v1/messages",
            {"model": self.model, "max_tokens": 2000, "temperature": self.temperature,
             "system": system, "messages": [{"role": "user", "content": user}]},
            {"content-type": "application/json", "x-api-key": self.api_key or "",
             "anthropic-version": "2023-06-01"},
        )
        text = "".join(b.get("text", "") for b in d.get("content", []) if b.get("type") == "text")
        return Completion(text, self.model, self.name, int((time.time() - t0) * 1000))


class OpenAI(Provider):
    name = "openai"
    key_env = "OPENAI_API_KEY"
    default_model = "gpt-4.1"

    def complete(self, system: str, user: str) -> Completion:
        t0 = time.time()
        d = self._post(
            "https://api.openai.com/v1/chat/completions",
            {"model": self.model, "temperature": self.temperature,
             "messages": [{"role": "system", "content": system},
                          {"role": "user", "content": user}]},
            {"content-type": "application/json", "authorization": f"Bearer {self.api_key}"},
        )
        return Completion(d["choices"][0]["message"]["content"], self.model, self.name,
                          int((time.time() - t0) * 1000))


class Google(Provider):
    name = "google"
    key_env = "GOOGLE_API_KEY"
    default_model = "gemini-2.5-pro"

    def complete(self, system: str, user: str) -> Completion:
        t0 = time.time()
        d = self._post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent",
            {"system_instruction": {"parts": [{"text": system}]},
             "contents": [{"role": "user", "parts": [{"text": user}]}],
             "generationConfig": {"temperature": self.temperature, "maxOutputTokens": 2000}},
            {"content-type": "application/json", "x-goog-api-key": self.api_key or ""},
        )
        parts = d["candidates"][0]["content"]["parts"]
        return Completion("".join(p.get("text", "") for p in parts), self.model, self.name,
                          int((time.time() - t0) * 1000))


REGISTRY = {"anthropic": Anthropic, "openai": OpenAI, "google": Google}


def get_provider(name: str | None = None, model: str | None = None) -> Provider:
    name = (name or os.environ.get("JUDGE_PROVIDER") or "anthropic").lower()
    if name not in REGISTRY:
        raise ProviderError(f"unknown provider {name!r}, expected one of {sorted(REGISTRY)}")
    return REGISTRY[name](model=model or os.environ.get("JUDGE_MODEL"))


def available_providers() -> list[str]:
    return [n for n, cls in REGISTRY.items() if os.environ.get(cls.key_env)]
