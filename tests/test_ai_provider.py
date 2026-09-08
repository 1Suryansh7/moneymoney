"""Stage 5 Commit 5B tests: provider, aliases, residency guard, redaction.

Zero network calls: Gemini bodies run against an injected fake transport.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path

import pytest

from analog_ic_design.ai.provider import (
    GeminiProvider,
    LLMRequest,
    MockProvider,
    Transport,
    resolve_alias,
)
from analog_ic_design.ai.residency import (
    DISABLED,
    HOSTED_ALLOWED,
    LOCAL_ONLY,
    ProviderGuard,
    redact_payload,
)


def _ok_transport(captured: dict[str, str]) -> Transport:
    def _send(url: str, body: str, headers: Mapping[str, str]) -> tuple[int, str]:
        captured["url"] = url
        captured["body"] = body
        reply = json.dumps(
            {
                "candidates": [{"content": {"parts": [{"text": "grounded prose here"}]}}],
                "usageMetadata": {"promptTokenCount": 7, "candidatesTokenCount": 13},
            }
        )
        return 200, reply

    return _send


def test_alias_precedence_and_fail_closed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config = tmp_path / "models.json"
    config.write_text(json.dumps({"GEMINI_STRONG_MODEL": "gemini-X"}), encoding="utf-8")
    assert resolve_alias("GEMINI_STRONG_MODEL", explicit="gemini-E") == "gemini-E"
    monkeypatch.setenv("GEMINI_STRONG_MODEL", "gemini-V")
    assert resolve_alias("GEMINI_STRONG_MODEL", config_path=config) == "gemini-V"
    monkeypatch.delenv("GEMINI_STRONG_MODEL")
    assert resolve_alias("GEMINI_STRONG_MODEL", config_path=config) == "gemini-X"
    with pytest.raises(ValueError, match="UNCONFIGURED"):
        resolve_alias("GEMINI_STRONG_MODEL")
    with pytest.raises(ValueError, match="cannot read model config"):
        resolve_alias("GEMINI_STRONG_MODEL", config_path=tmp_path / "missing.json")


def test_gemini_generate_uses_transport_not_network() -> None:
    captured: dict[str, str] = {}
    provider = GeminiProvider(
        model="gemini-T",
        api_key="AIza00000000000000000000000000000000000",
        transport=_ok_transport(captured),
    )
    response = provider.generate(LLMRequest(prompt="explain ERR-1", temperature=0.0, seed=3))
    assert response.text == "grounded prose here"
    assert (response.model, response.provider) == ("gemini-T", "gemini")
    assert (response.input_tokens, response.output_tokens) == (7, 13)
    assert response.seed == 3
    assert "gemini-T" in captured["url"]
    body = json.loads(captured["body"])
    assert body["contents"][0]["parts"][-1] == {"text": "explain ERR-1"}
    assert body["generationConfig"]["seed"] == 3


def test_gemini_rejects_without_key() -> None:
    with pytest.raises(ValueError, match="GEMINI_API_KEY is missing"):
        GeminiProvider(model="gemini-T", api_key="")


def test_gemini_fails_closed_on_transport() -> None:
    def _bad(url: str, body: str, headers: Mapping[str, str]) -> tuple[int, str]:
        return 500, "backend exploded"

    def _junk(url: str, body: str, headers: Mapping[str, str]) -> tuple[int, str]:
        return 200, "not json{"

    provider = GeminiProvider(model="gemini-T", api_key="k", transport=_bad)
    with pytest.raises(RuntimeError, match="HTTP 500"):
        provider.generate(LLMRequest(prompt="x"))
    broken = GeminiProvider(model="gemini-T", api_key="k", transport=_junk)
    with pytest.raises(RuntimeError, match="malformed"):
        broken.generate(LLMRequest(prompt="x"))


def test_mock_deterministic() -> None:
    mock = MockProvider({"hi": "hello there"})
    first = mock.generate(LLMRequest(prompt="hi"))
    assert (first.text, first.provider) == ("hello there", "mock")
    assert mock.generate(LLMRequest(prompt="hi")).request_id == first.request_id
    assert mock.generate(LLMRequest(prompt="other")).text.startswith("MOCK-REPLY")


def test_guard_modes_and_reversion() -> None:
    guard = ProviderGuard()
    assert guard.mode == LOCAL_ONLY
    guard.check_local(provider="mock")
    with pytest.raises(PermissionError, match="blocked"):
        guard.check_hosted(provider="gemini", model="m")
    record = guard.grant_hosted_opt_in(
        provider="gemini", model="m", artifact_classes=("ErrorRecord",)
    )
    with pytest.raises(PermissionError, match="blocked"):
        guard.check_hosted(provider="gemini", model="m")
    guard.set_mode(HOSTED_ALLOWED)
    assert guard.check_hosted(provider="gemini", model="m") is record
    with pytest.raises(PermissionError, match="no recorded opt-in"):
        guard.check_hosted(provider="gemini", model="other")
    guard.set_mode(LOCAL_ONLY)
    with pytest.raises(PermissionError, match="blocked"):
        guard.check_hosted(provider="gemini", model="m")
    guard.set_mode(DISABLED)
    with pytest.raises(PermissionError, match="blocked"):
        guard.check_local(provider="mock")
    with pytest.raises(ValueError, match="unknown AI execution mode"):
        guard.set_mode("YOLO")


def test_redact_payload() -> None:
    payload = {
        "prompt": "explain ERR-9",
        "api_key": "AIza00000000000000000000000000000000000",
        "nested": {"tokens": ["x", "AIza11111111111111111111111111111111111"]},
        "count": 3,
    }
    cleaned = redact_payload(payload)
    assert cleaned["prompt"] == "explain ERR-9"
    assert cleaned["api_key"] == "[REDACTED]"
    assert cleaned["nested"] == {"tokens": ["x", "[REDACTED]"]}
    assert cleaned["count"] == 3
    assert payload["nested"] == {"tokens": ["x", "AIza11111111111111111111111111111111111"]}
