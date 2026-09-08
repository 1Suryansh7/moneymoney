"""Two-Stage Miller Operational Amplifier Simulation & Sizing (Stage 6).

Builds testbenches, simulation runners, and Optuna sizing routines for the
canonical two-stage Miller op-amp (`two_stage_miller`).

Target Specification (Stage 6 Benchmark):
- Low-Frequency Gain >= 60 dB (1000 V/V)
- Unity-Gain Bandwidth (UGB) >= 40 MHz
- Phase Margin >= 60 deg

Grounding rule (§9.1): every metric returned here is MEASURED by ngspice
through a JobRunner backend. There is no analytical estimator path: without
a simulator backend evaluation fails closed. Emits the mandatory blocking
human checkpoint (§8 & §12) upon proposal generation.
"""

from __future__ import annotations

import json
import math
import sqlite3
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Final

from analog_ic_design.circuit.compiler import compile_netlist
from analog_ic_design.circuit.validator import validate
from analog_ic_design.optimize.optimizer import SearchSpace, TrialResult
from analog_ic_design.optimize.optuna_optimizer import OptunaOptimizer
from analog_ic_design.sim.jobs import JobRunner
from analog_ic_design.sim.ngspice import RawSim, SimError
from analog_ic_design.sim.reproduce import design_identity_hash
from analog_ic_design.sim.testbench import (
    _MICRONS_PER_METER,
    _corner_libs,
    _corner_supply,
    _to_microns,
)
from analog_ic_design.sim.waveform import parse_ac
from analog_ic_design.topology.knowledge_base import record_template_experiment
from analog_ic_design.topology.proposal import CandidateCircuitIR
from analog_ic_design.topology.templates import instantiate_template

PASSIVE_SUBCKTS: Final = """
* Ideal passive subcircuit wrappers for simulation compatibility
.subckt cap_subckt p n c=1e-12
C1 p n {c}
.ends
.subckt res_subckt p n r=1000
R1 p n {r}
.ends
"""


@dataclass(frozen=True)
class MillerMetrics:
    """Electrical metrics MEASURED by ngspice for a Two-Stage Miller candidate."""

    gain_v_v: float
    gain_db: float
    ugb_hz: float
    phase_margin_deg: float


MILLER_SEARCH_SPACE: Final = SearchSpace({
    "w_in": (2.0e-06, 25.0e-06),
    "w_load": (2.0e-06, 25.0e-06),
    "w_out": (10.0e-06, 60.0e-06),
    "w_load2": (5.0e-06, 40.0e-06),
    "cc": (0.5e-12, 3.0e-12),
    "rz": (500.0, 4000.0),
})


def assemble_miller_ac_deck(
    fragment: str,
    *,
    vdd_net: str = "vdd",
    vdd_volts: float = 1.8,
    vss_net: str = "vss",
    vcm_volts: float = 0.9,
    vbias1_volts: float = 0.65,
    vbias2_volts: float = 0.65,
    f_start: float = 1.0,
    f_stop: float = 10.0e9,
    points_per_decade: int = 10,
    cload_farads: float = 2.0e-12,
    libs: Sequence[tuple[str, str]] = (),
) -> str:
    """Assemble small-signal AC frequency response deck for Two-Stage Miller Op-Amp.

    Single-ended drive: Vip carries AC 1.0 V, Vin is AC ground (DC stays at
    VCM on both inputs). By linearity the response equals the response to a
    1.0 V differential stimulus up to common-mode gain (~0 with a tail
    source), so vip-referenced ratios ARE differential-input metrics and the
    Stage 3 extractors (unchanged) measure true gain / UGB / phase margin.
    """
    body = fragment.splitlines()
    while body and not body[-1].strip():
        body.pop()
    if body and body[-1].strip().lower() == ".end":
        body.pop()
    title, rest = (body[0], body[1:]) if body else ("* two_stage_miller ac deck", [])

    lines = [title]
    lines.append(PASSIVE_SUBCKTS.strip())
    lines += _corner_libs(libs, corner=None)
    lines.append(".param mc_mm_switch=0")
    lines.append(".option scale=1e-6")
    lines += [_to_microns(line) for line in rest]
    lines += _corner_supply(vdd_net, vdd_volts, corner=None)
    lines.append(f"VSS {vss_net} 0 DC 0")
    lines.append(f"Vbias1 vbias1 0 DC {vbias1_volts}")
    lines.append(f"Vbias2 vbias2 0 DC {vbias2_volts}")
    # Single-ended stimulus: Vid = Vip - Vin = 1.0 V AC (see docstring).
    lines.append(f"Vip vip 0 DC {vcm_volts} AC 1.0")
    lines.append(f"Vin vin 0 DC {vcm_volts}")
    lines.append(f"Cload out 0 {cload_farads * 1e12}p")
    lines.append(f".ac dec {points_per_decade} {f_start} {f_stop}")
    lines.append(".end")
    return "\n".join(lines) + "\n"


def format_stage6_checkpoint_alert(
    candidate: CandidateCircuitIR,
    *,
    validation_status: str,
    simulation_status: str,
    constraints_status: str,
    diff_summary: str,
) -> str:
    """Format the mandatory blocking human checkpoint alert block (§8 & §12)."""
    p = candidate.parameters
    w_in_um = p.get("w_in", 0.0) * _MICRONS_PER_METER
    l_in_um = p.get("l_in", 0.5e-6) * _MICRONS_PER_METER
    w_out_um = p.get("w_out", 0.0) * _MICRONS_PER_METER
    cc_pf = p.get("cc", 0.0) * 1e12
    rz_kohm = p.get("rz", 0.0) / 1000.0

    sizing_str = (
        f"W_in={w_in_um:.2f}um, L_in={l_in_um:.2f}um, "
        f"W_out={w_out_um:.2f}um, Cc={cc_pf:.2f}pF, Rz={rz_kohm:.2f}kOhm"
    )

    return (
        f"[ HUMAN CHECKPOINT — Stage 6 / AI design proposal ]\n"
        f"Trigger: AI proposed {candidate.topology_id} with sizing {sizing_str}.\n"
        f"Check: Validation {validation_status}, simulation {simulation_status}, "
        f"constraints {constraints_status}.\n"
        f"Proposed vs current design diff: {diff_summary}. Accept / reject / compare?\n"
        f"Status: BLOCKING — never auto-committed, even when all checks pass."
    )


def evaluate_miller_candidate(
    conn: sqlite3.Connection,
    candidate: CandidateCircuitIR,
    *,
    jobs: JobRunner | None = None,
    sky130_lib: str | None = None,
    seed: int = 42,
) -> tuple[MillerMetrics, str]:
    """Compile, simulate, and extract MEASURED metrics for a Miller candidate.

    Fail-closed contract (§9.1): without a simulator backend (`jobs` plus
    `sky130_lib`) this raises instead of estimating. Analytical formulas are
    never a source of physical truth, so no estimator path exists here.
    """
    cell_id = instantiate_template(
        conn, candidate.topology_id, params=candidate.parameters, cell_name="eval_miller"
    )
    report = validate(conn, cell_id)
    if not report.valid:
        raise SimError(f"Schema: pre-simulation validation gate failed: {report.violations}")

    netlist = compile_netlist(conn, cell_id)

    if jobs is None or sky130_lib is None:
        raise SimError(
            "Schema: evaluate_miller_candidate requires a simulator backend "
            "(jobs + sky130_lib); refusing to estimate without ngspice"
        )

    from analog_ic_design.metrics.bandwidth import extract_bandwidth
    from analog_ic_design.metrics.phase_margin import extract_phase_margin

    deck = assemble_miller_ac_deck(netlist, libs=[(sky130_lib, "tt")])
    jid = jobs.submit_simulation(netlist=deck, seed=seed)
    job_res = jobs.wait(jid, timeout=120.0)
    if job_res.status != "succeeded" or not job_res.result:
        raise SimError(f"SPICE convergence: ngspice job {jid} failed: {job_res.error}")
    payload = json.loads(job_res.result)
    vectors = payload["vectors"]
    # AC truth lives in the complex vectors: payload["vectors"] holds only
    # real parts (ngspice on_data creal), so phasor metrics (phase margin)
    # MUST be rebuilt from complex_vectors. Dropping them coerces imag to
    # zero and fabricates PM = 0 (caught live 2026-09-09).
    cx_pairs = payload.get("complex_vectors", {})
    cx_vectors = {
        name: [complex(pair[0], pair[1]) for pair in samples]
        for name, samples in cx_pairs.items()
    }
    wave = parse_ac(RawSim(vectors=vectors, complex_vectors=cx_vectors, log=""))
    ugb = extract_bandwidth(wave, in_node="vip", out_node="out")
    pm = extract_phase_margin(wave, in_node="vip", out_node="out")
    # Deck drives Vid = 1.0 V AC on vip (vin is AC ground), so out/vip is the
    # differential-input voltage gain directly. extract_bandwidth above raises
    # on non-positive input, so vip_mag[0] > 0 here.
    vip_mag = wave.trace("vip").magnitude()
    gain_v_v = wave.trace("out").magnitude()[0] / vip_mag[0]
    gain_db = 20.0 * math.log10(gain_v_v)
    repro = design_identity_hash(netlist=deck, sim_config={"seed": seed})
    return MillerMetrics(
        gain_v_v=gain_v_v, gain_db=gain_db, ugb_hz=ugb, phase_margin_deg=pm
    ), repro


def run_miller_sizing_optimization(
    conn: sqlite3.Connection,
    *,
    target_gain_db: float = 60.0,
    target_ugb_hz: float = 40.0e6,
    n_trials: int = 5,
    seed: int = 42,
    jobs: JobRunner | None = None,
    sky130_lib: str | None = None,
) -> TrialResult:
    """Run Optuna sizing study over two_stage_miller parameter space.

    Every trial is a real ngspice simulation (MEASURED metrics recorded to
    the experiment ledger). Fails closed before the first trial when no
    simulator backend is provided, so no unfounded rows are ever written.
    """
    if n_trials < 1:
        raise SimError(f"Schema: n_trials must be positive, got {n_trials}")
    opt = OptunaOptimizer(
        MILLER_SEARCH_SPACE,
        seed=seed,
        study_name="miller_sizing_demo",
        direction="minimize",
    )
    best_trial: TrialResult | None = None
    best_cost = float("inf")

    for t_idx in range(n_trials):
        params = opt.suggest()
        cand = CandidateCircuitIR(
            topology_id="two_stage_miller",
            parameters=params,
            reasoning=f"Trial {t_idx} exploration",
            evidence_ids=(f"TRIAL-{t_idx}",),
            requested_spec_id="SPEC-MILLER-60DB",
        )
        metrics, repro = evaluate_miller_candidate(
            conn, cand, jobs=jobs, sky130_lib=sky130_lib, seed=seed + t_idx
        )

        # Cost: penalty for missing 60dB gain or 40MHz bandwidth
        gain_penalty = max(0.0, target_gain_db - metrics.gain_db) * 10.0
        ugb_penalty = max(0.0, (target_ugb_hz - metrics.ugb_hz) / 1e6) * 5.0
        cost = gain_penalty + ugb_penalty

        opt.observe(params, cost)

        trial_res = TrialResult(
            study="two_stage_miller_sizing_demo",
            trial=t_idx,
            kind="trial",
            status="succeeded" if cost == 0.0 else "failed",
            corner="nominal",
            parameters=params,
            metrics={
                "gain_db": metrics.gain_db,
                "ugb_hz": metrics.ugb_hz,
                "pm_deg": metrics.phase_margin_deg,
            },
            verdict="pass" if cost == 0.0 else f"spec_gap_cost={cost:.2f}",
            reproducibility_id=repro,
            seed=seed + t_idx,
            job_id=None,
        )
        record_template_experiment(conn, "two_stage_miller", trial_res)

        if cost < best_cost:
            best_cost = cost
            best_trial = trial_res

    if best_trial is None:  # Unreachable with n_trials >= 1; defensive.
        raise SimError("Schema: sizing loop produced no trials")

    return best_trial
