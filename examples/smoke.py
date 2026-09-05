"""Stage 0 baseline smoke verification (packaging only, no design logic).

Reports: interpreter version, capability-alias status, and the pinned
toolchain contract declared in the Dockerfile. Fails non-zero on any
breach so `make run-example` is a real gate, not a print statement.
"""

from __future__ import annotations

import sys
from pathlib import Path

from check_models import SENTINEL, resolve_aliases

REPO_ROOT = Path(__file__).resolve().parents[1]

REQUIRED_PINS: tuple[tuple[str, str], ...] = (
    ("python:3.11", "Python 3.11 container base"),
    ("UBUNTU_IMAGE=ubuntu:22.04", "Ubuntu 22.04 EDA stage root"),
    ("NGSPICE_VERSION=47", "ngspice latest stable"),
    ("KLAYOUT_VERSION=0.30.12", "KLayout hotfix (Aug 2026)"),
)


def main() -> int:
    failures: list[str] = []

    version = sys.version_info
    print(f"python={version.major}.{version.minor}.{version.micro}")
    if (version.major, version.minor) < (3, 11):
        failures.append(f"interpreter {version.major}.{version.minor} < required 3.11")

    try:
        from analog_ic_design import ENGINE_API_VERSION
    except ImportError as exc:
        failures.append(f"package analog_ic_design not importable: {exc}")
    else:
        print(f"engine_api={ENGINE_API_VERSION}")
        if ENGINE_API_VERSION != "0.1":
            failures.append(f"ENGINE_API_VERSION={ENGINE_API_VERSION} != 0.1")

    for alias, (value, source) in resolve_aliases().items():
        state = "CONFIGURED" if value != SENTINEL else "UNCONFIGURED (expected pre-Stage-5)"
        print(f"{alias} source={source} status={state}")

    lines = (REPO_ROOT / "Dockerfile").read_text(encoding="utf-8").splitlines()
    code = "\n".join(line for line in lines if not line.lstrip().startswith("#"))
    if ":latest" in code:
        failures.append("Dockerfile pins a ':latest' image tag (pin policy breach)")
    for pin, meaning in REQUIRED_PINS:
        found = pin in code
        print(f"pin {pin} ({meaning}): {'present' if found else 'MISSING'}")
        if not found:
            failures.append(f"Dockerfile missing pin: {pin}")

    if failures:
        for failure in failures:
            # Failure taxonomy (AGENTS.md section 6): packaging-gate breaches
            # are Schema-category failures. Never a bare "failed".
            print(f"SMOKE FAIL [taxonomy: Schema]: {failure}", file=sys.stderr)
        return 1
    print("SMOKE OK: packaging baseline verified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
