"""Simulation kernel: libngspice binding (2C), runner (2D), identity (2E)."""

from analog_ic_design.sim.backend import NgspiceBackend
from analog_ic_design.sim.cs_amp import build_cs_amplifier
from analog_ic_design.sim.inverter import build_inverter
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
from analog_ic_design.sim.testbench import (
    assemble_ac,
    assemble_dc_sweep,
    assemble_loop_gain,
    assemble_step_response,
    assemble_transient,
)
from analog_ic_design.sim.waveform import (
    ACTrace,
    ACWaveform,
    Trace,
    Waveform,
    parse_ac,
    parse_transient,
)

__all__ = [
    "ACTrace",
    "ACWaveform",
    "COMPARISON_POLICY_ID",
    "JobResult",
    "JobRunner",
    "NgspiceBackend",
    "RawSim",
    "SimError",
    "Trace",
    "Waveform",
    "assemble_ac",
    "assemble_dc_sweep",
    "assemble_loop_gain",
    "assemble_step_response",
    "assemble_transient",
    "build_cs_amplifier",
    "build_inverter",
    "canonical_encode",
    "design_identity_hash",
    "execution_environment_hash",
    "libngspice_available",
    "normalize_netlist",
    "parse_ac",
    "parse_transient",
    "reproducibility_id",
    "run_deck",
    "sha256_hex",
    "waveforms_close",
]

