"""Simulation kernel: libngspice binding (2C), runner (2D), identity (2E)."""

from analog_ic_design.sim.backend import NgspiceBackend
from analog_ic_design.sim.cs_amp import build_cs_amplifier
from analog_ic_design.sim.diff_pair import build_diff_pair
from analog_ic_design.sim.inverter import build_inverter
from analog_ic_design.sim.jobs import JobResult, JobRunner
from analog_ic_design.sim.miller_opamp import (
    MILLER_SEARCH_SPACE,
    MillerMetrics,
    assemble_miller_ac_deck,
    evaluate_miller_candidate,
    format_stage6_checkpoint_alert,
    run_miller_sizing_optimization,
)
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
    assemble_closed_loop_step,
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
    "MILLER_SEARCH_SPACE",
    "MillerMetrics",
    "NgspiceBackend",
    "RawSim",
    "SimError",
    "Trace",
    "Waveform",
    "assemble_ac",
    "assemble_closed_loop_step",
    "assemble_dc_sweep",
    "assemble_loop_gain",
    "assemble_miller_ac_deck",
    "assemble_step_response",
    "assemble_transient",
    "build_cs_amplifier",
    "build_diff_pair",
    "build_inverter",
    "canonical_encode",
    "design_identity_hash",
    "evaluate_miller_candidate",
    "execution_environment_hash",
    "format_stage6_checkpoint_alert",
    "libngspice_available",
    "normalize_netlist",
    "parse_ac",
    "parse_transient",
    "reproducibility_id",
    "run_deck",
    "run_miller_sizing_optimization",
    "sha256_hex",
    "waveforms_close",
]

