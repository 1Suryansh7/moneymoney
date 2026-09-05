"""ngspice simulator backend (Stage 2 Commit 2C).

`NgspiceBackend` implements the abstract `Simulator` over the ctypes binding
in `sim.ngspice`. The shared library loads lazily at call time so this module
imports cleanly on images without libngspice (base); calls there fail closed
with `SimError`, never with an `OSError` leak.
"""

from __future__ import annotations

import json
import subprocess

from analog_ic_design.interfaces.simulator import SimulateResult, Simulator
from analog_ic_design.sim.ngspice import SimError, run_deck
from analog_ic_design.sim.reproduce import design_identity_hash

_DEFAULT_LIB = "libngspice.so"


def _identity(netlist: str, seed: int) -> str:
    """Run identity via the 2E contract (design + seed as logical config)."""
    return design_identity_hash(netlist=netlist, sim_config={"seed": seed})


class NgspiceBackend(Simulator):
    """`Simulator` over libngspice (ngspice-47 in the pinned EDA image)."""

    def __init__(self, *, lib_path: str = _DEFAULT_LIB) -> None:
        self._lib_path = lib_path

    def simulate(self, *, netlist: str, seed: int) -> SimulateResult:
        """Run `netlist` deterministically; SI units inside the deck."""
        if not isinstance(netlist, str) or not netlist.strip():
            raise SimError("Netlist: empty deck cannot be simulated")
        if isinstance(seed, bool) or not isinstance(seed, int):
            raise SimError("Schema: seed must be an int")
        raw = run_deck(lib_path=self._lib_path, lines=netlist.splitlines())
        payload = json.dumps(
            {"vectors": {k: list(v) for k, v in raw.vectors.items()}, "log": raw.log},
            sort_keys=True,
        ).encode("utf-8")
        return SimulateResult(reproducibility_id=_identity(netlist, seed), raw_output=payload)

    def simulator_version(self) -> str:
        """First informative line of `ngspice --version` (CLI ships beside the lib)."""
        try:
            proc = subprocess.run(
                ["ngspice", "--version"], capture_output=True, text=True, timeout=60
            )
        except (OSError, subprocess.SubprocessError) as exc:
            raise SimError(f"Schema: cannot probe ngspice version: {exc}") from exc
        for line in proc.stdout.strip().splitlines():
            if line.strip().strip("*").strip():
                return line.strip()
        return "ngspice (version unknown)"
