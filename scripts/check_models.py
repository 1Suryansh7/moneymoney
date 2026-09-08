"""Capability-alias health check (AGENTS.md section 9.5).

Resolves GEMINI_STRONG_MODEL / GEMINI_FAST_MODEL from environment first,
then config/models.json. Performs NO network call and reads NO secrets:
it reports only whether each alias resolves to a real model id.

Exit code: 0 always, unless --strict is passed, in which case an
UNCONFIGURED alias exits 1. Non-strict is permanent in CI: aliases stay
UNCONFIGURED in-repo by design (model IDs resolve from the operator's
environment at call time), and Stage 5 enforces configuration at dispatch
instead — `resolve_alias` and missing-key checks fail closed there, so an
unconfigured alias can never reach the network. Flipping CI to strict
would demand secrets in the repo or CI env, which the residency law forbids.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ALIASES: tuple[str, ...] = ("GEMINI_STRONG_MODEL", "GEMINI_FAST_MODEL")
SENTINEL = "UNCONFIGURED"
REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = REPO_ROOT / "config" / "models.json"


def resolve_aliases(config_path: Path = DEFAULT_CONFIG) -> dict[str, tuple[str, str]]:
    """Return {alias: (value, source)} where source is 'env' or 'config'."""
    raw: dict[str, str] = {}
    if config_path.is_file():
        data: object = json.loads(config_path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            for alias in ALIASES:
                value = data.get(alias)
                if isinstance(value, str) and value:
                    raw[alias] = value
    resolved: dict[str, tuple[str, str]] = {}
    for alias in ALIASES:
        env_value = os.environ.get(alias)
        if env_value:
            resolved[alias] = (env_value, "env")
        elif alias in raw:
            resolved[alias] = (raw[alias], "config")
        else:
            resolved[alias] = (SENTINEL, "missing")
    return resolved


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify model capability aliases resolve.")
    parser.add_argument("--strict", action="store_true",
                        help="Exit 1 if any alias is UNCONFIGURED.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args(argv)

    resolved = resolve_aliases(args.config)
    worst = 0
    for alias in ALIASES:
        value, source = resolved[alias]
        ok = value != SENTINEL
        print(f"{alias}={value} (source={source}) status={'CONFIGURED' if ok else 'UNCONFIGURED'}")
        if not ok and args.strict:
            worst = 1
    if worst:
        print("STRICT: one or more aliases UNCONFIGURED.", file=sys.stderr)
    return worst


if __name__ == "__main__":
    raise SystemExit(main())
