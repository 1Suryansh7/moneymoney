"""LLM provider abstraction: types, Gemini (stdlib HTTP), Mock (Stage 5 Commit 5B).

Every programmatic model call routes through `LLMProvider`. Model IDs
resolve via `GEMINI_*` capability aliases (explicit arg > environment >
config file); UNCONFIGURED fails closed. Gemini transport is stdlib
`urllib` only — zero new dependencies — and is injectable for tests, so
no test ever touches the network. Metadata per AGENTS.md section 9.2 is
recorded on every response.
"""

from __future__ import annotations

import hashlib
import json
import os
import urllib.request
from abc import ABC, abstractmethod
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Final

GEMINI_API_HOST: Final = "https://generativelanguage.googleapis.com"
UNCONFIGURED: Final = "UNCONFIGURED"


@dataclass(frozen=True)
class LLMRequest:
    """One model call: prompt plus explicit generation controls."""

    prompt: str
    system: str = ""
    temperature: float = 0.0
    seed: int | None = None
    max_tokens: int = 1024
    prompt_version: str = "v1"


@dataclass(frozen=True)
class LLMResponse:
    """One model reply with AGENTS.md section 9.2 provenance metadata."""

    text: str
    model: str
    provider: str
    prompt_version: str
    temperature: float
    seed: int | None
    input_tokens: int
    output_tokens: int
    timestamp: str
    request_id: str


def _utcnow() -> str:
    return datetime.now(UTC).isoformat()


class LLMProvider(ABC):
    """Abstract model client (Law 4: the only path to any model)."""

    provider_name: str = "base"
    hosted: bool = False

    @property
    def model_name(self) -> str:
        """Concrete model ID behind this instance (for opt-in matching)."""
        raise NotImplementedError

    @abstractmethod
    def generate(self, request: LLMRequest) -> LLMResponse:
        """Run one generation synchronously."""
        raise NotImplementedError


def resolve_alias(
    alias: str, *, explicit: str | None = None, config_path: Path | None = None
) -> str:
    """Resolve a capability alias to a concrete model ID.

    Precedence: explicit argument, then environment, then config file.
    Raises `ValueError` while UNCONFIGURED (fail closed, never a default model).
    """
    if explicit:
        return explicit
    env_value = os.environ.get(alias)
    if env_value and env_value != UNCONFIGURED:
        return env_value
    if config_path is not None:
        try:
            data = json.loads(Path(config_path).read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise ValueError(f"Schema: cannot read model config {config_path}: {exc}") from exc
        value = data.get(alias) if isinstance(data, dict) else None
        if isinstance(value, str) and value and value != UNCONFIGURED:
            return value
    raise ValueError(f"Schema: model alias {alias!r} is UNCONFIGURED")


# Transport: (url, body_json, headers) -> (http_status, response_text).
Transport = Callable[[str, str, Mapping[str, str]], tuple[int, str]]


def _urllib_transport(url: str, body: str, headers: Mapping[str, str]) -> tuple[int, str]:
    request = urllib.request.Request(
        url, data=body.encode("utf-8"), headers=dict(headers), method="POST"
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            return int(response.status), response.read().decode("utf-8", "replace")
    except OSError as exc:
        raise ConnectionError(f"provider transport failed: {exc}") from exc


class GeminiProvider(LLMProvider):
    """Gemini via AI Studio `generateContent` (stdlib HTTP, key from env)."""

    provider_name = "gemini"
    hosted = True

    def __init__(
        self,
        *,
        alias: str = "GEMINI_STRONG_MODEL",
        model: str | None = None,
        config_path: Path | None = None,
        api_key: str | None = None,
        prompt_version: str = "v1",
        transport: Transport | None = None,
    ) -> None:
        self._model = resolve_alias(alias, explicit=model, config_path=config_path)
        key = api_key if api_key is not None else os.environ.get("GEMINI_API_KEY", "")
        if not key:
            raise ValueError("Schema: GEMINI_API_KEY is missing (no hosted calls possible)")
        self._key = key
        self._prompt_version = prompt_version
        self._transport = transport if transport is not None else _urllib_transport

    @property
    def model_name(self) -> str:
        """Resolved Gemini model ID."""
        return self._model

    def generate(self, request: LLMRequest) -> LLMResponse:
        """POST one `generateContent` call; malformed replies fail closed."""
        url = (
            f"{GEMINI_API_HOST}/v1beta/models/{self._model}:generateContent"
            f"?key={self._key}"
        )
        parts: list[dict[str, str]] = []
        if request.system:
            parts.append({"text": request.system})
        parts.append({"text": request.prompt})
        body = {
            "contents": [{"parts": parts}],
            "generationConfig": {
                "temperature": request.temperature,
                "maxOutputTokens": request.max_tokens,
            },
        }
        if request.seed is not None:
            body["generationConfig"]["seed"] = request.seed  # type: ignore[index]
        status, text = self._transport(url, json.dumps(body), {"Content-Type": "application/json"})
        if status != 200:
            raise RuntimeError(f"provider error: HTTP {status}: {text[:500]}")
        try:
            payload = json.loads(text)
            candidate = payload["candidates"][0]
            part = candidate["content"]["parts"][0]
            reply = part["text"]
            usage = payload.get("usageMetadata", {})
            in_tokens = int(usage.get("promptTokenCount", 0))
            out_tokens = int(usage.get("candidatesTokenCount", 0))
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise RuntimeError(f"provider error: malformed model reply: {exc}") from exc
        if not isinstance(reply, str) or not reply:
            raise RuntimeError("provider error: empty model reply")
        digest = hashlib.sha256((self._model + text).encode("utf-8")).hexdigest()[:16]
        return LLMResponse(
            text=reply,
            model=self._model,
            provider=self.provider_name,
            prompt_version=request.prompt_version or self._prompt_version,
            temperature=request.temperature,
            seed=request.seed,
            input_tokens=in_tokens,
            output_tokens=out_tokens,
            timestamp=_utcnow(),
            request_id=f"gemini-{digest}",
        )


class MockProvider(LLMProvider):
    """Deterministic canned responses for tests — never touches the network."""

    provider_name = "mock"

    def __init__(
        self,
        canned: Mapping[str, str] | None = None,
        *,
        default_reply: str | None = None,
    ) -> None:
        self._canned = dict(canned) if canned is not None else {}
        self._default_reply = default_reply

    @property
    def model_name(self) -> str:
        """Fixed mock model ID."""
        return "mock-1"

    def generate(self, request: LLMRequest) -> LLMResponse:
        """Return the canned reply (or fallback) — fully deterministic."""
        if request.prompt in self._canned:
            text = self._canned[request.prompt]
        elif self._default_reply is not None:
            text = self._default_reply
        else:
            text = f"MOCK-REPLY[len={len(request.prompt)}]"
        digest = hashlib.sha256(request.prompt.encode("utf-8")).hexdigest()[:16]
        return LLMResponse(
            text=text,
            model="mock-1",
            provider=self.provider_name,
            prompt_version=request.prompt_version,
            temperature=request.temperature,
            seed=request.seed,
            input_tokens=0,
            output_tokens=0,
            timestamp=_utcnow(),
            request_id=f"mock-{digest}",
        )


__all__ = [
    "GEMINI_API_HOST",
    "UNCONFIGURED",
    "LLMRequest",
    "LLMResponse",
    "LLMProvider",
    "GeminiProvider",
    "MockProvider",
    "Transport",
    "resolve_alias",
]
