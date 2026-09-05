"""Simulation kernel: libngspice binding (2C), runner (2D), identity (2E)."""

from analog_ic_design.sim.backend import NgspiceBackend
from analog_ic_design.sim.jobs import JobResult, JobRunner
from analog_ic_design.sim.ngspice import RawSim, SimError, libngspice_available, run_deck
from analog_ic_design.sim.reproduce import (
    COMPARISON_POLICY_ID,
    canonical_encode,
    design_identity_hash,
    execution_environment_hash,
    normalize_netlist,
    reproducibility_id,
    sha256_hex,
    waveforms_close,
)

__all__ = [
    "COMPARISON_POLICY_ID",
    "JobResult",
    "JobRunner",
    "NgspiceBackend",
    "RawSim",
    "SimError",
    "canonical_encode",
    "design_identity_hash",
    "execution_environment_hash",
    "libngspice_available",
    "normalize_netlist",
    "reproducibility_id",
    "run_deck",
    "sha256_hex",
    "waveforms_close",
]
