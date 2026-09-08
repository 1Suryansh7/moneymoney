"""AI execution modes, provider-call guard, secret filter (Stage 5 Commit 5B).

Residency law (AGENTS.md section 9.4): every project operates DISABLED,
LOCAL_ONLY (default), or HOSTED_ALLOWED. Hosted dispatch needs BOTH the
mode and a recorded opt-in naming provider, model, and artifact classes;
reverting the mode blocks the next call immediately. Secrets are stripped
before dispatch and never persist in provenance — filter first, then send.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Final

DISABLED: Final = "DISABLED"
LOCAL_ONLY: Final = "LOCAL_ONLY"
HOSTED_ALLOWED: Final = "HOSTED_ALLOWED"
_MODES: Final = (DISABLED, LOCAL_ONLY, HOSTED_ALLOWED)

REDACTED: Final = "[REDACTED]"

#: Payload keys whose values are secret by name (case-insensitive substring).
_SECRET_KEY_PARTS: Final = (
    "api_key",
    "apikey",
    "token",
    "secret",
    "password",
    "credential",
    "license",
    "private_key",
    "privatekey",
)

#: Google AI Studio keys start with AIza (35 trailing chars).
_KEY_PATTERN: Final = re.compile(r"AIza[0-9A-Za-z\-_]{35}")


@dataclass(frozen=True)
class HostedOptIn:
    """Recorded pre-call disclosure: what goes where, and when disclosed."""

    provider: str
    model: str
    artifact_classes: tuple[str, ...]
    timestamp: str


class ProviderGuard:
    """Session-scoped residency gate for model dispatch."""

    def __init__(self, *, mode: str = LOCAL_ONLY) -> None:
        self._mode = self._check_mode(mode)
        self._opt_in: HostedOptIn | None = None

    @staticmethod
    def _check_mode(mode: str) -> str:
        if mode not in _MODES:
            raise ValueError(f"Schema: unknown AI execution mode {mode!r}")
        return mode

    @property
    def mode(self) -> str:
        """Current execution mode (reversion takes effect immediately)."""
        return self._mode

    def set_mode(self, mode: str) -> None:
        """Switch modes; dropping from HOSTED_ALLOWED blocks hosted calls now."""
        self._mode = self._check_mode(mode)

    def grant_hosted_opt_in(
        self, *, provider: str, model: str, artifact_classes: tuple[str, ...]
    ) -> HostedOptIn:
        """Record the pre-call disclosure; returns the opt-in record."""
        if not provider or not model:
            raise ValueError("Schema: hosted opt-in needs provider and model")
        record = HostedOptIn(
            provider=provider,
            model=model,
            artifact_classes=tuple(artifact_classes),
            timestamp=datetime.now(UTC).isoformat(),
        )
        self._opt_in = record
        return record

    def check_hosted(self, *, provider: str, model: str) -> HostedOptIn:
        """Permit a hosted call iff mode allows it with a matching opt-in."""
        if self._mode != HOSTED_ALLOWED:
            raise PermissionError(
                f"AI residency: hosted call to {provider}/{model} blocked"
                f" in mode {self._mode}"
            )
        if (
            self._opt_in is None
            or self._opt_in.provider != provider
            or self._opt_in.model != model
        ):
            raise PermissionError(
                f"AI residency: no recorded opt-in for {provider}/{model}"
            )
        return self._opt_in

    def check_local(self, *, provider: str) -> None:
        """Permit a local/mock call unless DISABLED (no network either way)."""
        if self._mode == DISABLED:
            raise PermissionError(
                f"AI residency: model calls blocked in mode {self._mode} ({provider})"
            )


def redact_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Deep-copy `payload` with secret values replaced by `[REDACTED]`.

    Redacts values under secret-named keys and Google-key-shaped strings
    anywhere in string values. Never mutates the input.
    """

    def _scrub_text(text: str) -> str:
        return _KEY_PATTERN.sub(REDACTED, text)

    def _scrub(value: Any) -> Any:
        if isinstance(value, str):
            return _scrub_text(value)
        if isinstance(value, Mapping):
            return {key: _scrub(item) for key, item in value.items()}
        if isinstance(value, (list, tuple)):
            return [_scrub(item) for item in value]
        return value

    cleaned: dict[str, Any] = {}
    for key, value in payload.items():
        if isinstance(key, str) and any(part in key.lower() for part in _SECRET_KEY_PARTS):
            cleaned[key] = REDACTED
        else:
            cleaned[key] = _scrub(value)
    return cleaned


__all__ = [
    "DISABLED",
    "HOSTED_ALLOWED",
    "LOCAL_ONLY",
    "REDACTED",
    "HostedOptIn",
    "ProviderGuard",
    "redact_payload",
]
