"""Canonical reproducibility identity (Stage 2 Commit 2E, §14.1).

Four SEPARATE concepts — conflating them is the failure this module exists
to prevent. Numerical tolerance is a *comparison policy* (`waveforms_close`,
`COMPARISON_POLICY_ID`); it never enters an identity hash. Simulator output
is compared under a policy, never byte-asserted.

All functions are pure (no I/O, no clock): same inputs -> same hex digest,
on any machine, in any process. Callers supply environment facts; nothing
is sniffed implicitly.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping, Sequence
from typing import Any, Final

COMPARISON_POLICY_ID: Final = "tolerance-v1"


def canonical_encode(obj: Mapping[str, Any]) -> bytes:
    """Deterministic UTF-8 encoding: sorted keys, compact separators."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()


def sha256_hex(data: bytes) -> str:
    """SHA-256 hex digest."""
    return hashlib.sha256(data).hexdigest()


def normalize_netlist(netlist: str) -> str:
    """Canonical netlist text: trailing whitespace per line removed, blank
    edge lines removed, LF endings, single trailing newline."""
    lines = [line.rstrip() for line in netlist.splitlines()]
    while lines and not lines[0]:
        lines.pop(0)
    while lines and not lines[-1]:
        lines.pop()
    return "\n".join(lines) + "\n"


def design_identity_hash(*, netlist: str, sim_config: Mapping[str, Any]) -> str:
    """Same design + logical sim config -> same hash, anywhere."""
    return sha256_hex(
        canonical_encode({"netlist": normalize_netlist(netlist), "sim_config": dict(sim_config)})
    )


def execution_environment_hash(
    *,
    simulator: str,
    pdk_version: str,
    model_hashes: Mapping[str, str],
    container: str,
    backends: Mapping[str, str],
    measurement_version: str,
) -> str:
    """Same tool environment -> same hash. Any upgrade changes it (by design:
    a result is only reproducible *under* a recorded environment)."""
    return sha256_hex(
        canonical_encode(
            {
                "simulator": simulator,
                "pdk_version": pdk_version,
                "model_hashes": dict(model_hashes),
                "container": container,
                "backends": dict(backends),
                "measurement_version": measurement_version,
            }
        )
    )


def reproducibility_id(
    *, design: str, environment: str, seed: int, analysis: Mapping[str, Any]
) -> str:
    """Binds design + environment + seed + analysis settings into one id."""
    return sha256_hex(
        canonical_encode(
            {"design": design, "environment": environment, "seed": seed, "analysis": dict(analysis)}
        )
    )


def waveforms_close(
    first: Sequence[float], second: Sequence[float], *, rtol: float = 1e-3, atol: float = 1e-9
) -> bool:
    """Tolerance comparison for simulator output (policy, not identity)."""
    if len(first) != len(second):
        return False
    pairs = zip(first, second, strict=True)
    return all(math.isclose(a, b, rel_tol=rtol, abs_tol=atol) for a, b in pairs)
