"""Stage 6 Milestone Integration Demo: Two-Stage Miller Op-Amp.

Benchmark specification:
"Design a 2-stage Miller op-amp, 60dB gain, 40MHz UGB"
producing a template instantiation that validates, simulates, gets sized by
Stage 4 optimizer, and sits as a proposal awaiting accept/reject.

Grounding rule (§9.1): every metric here is MEASURED by ngspice. Base tests
use explicit test doubles (labeled) or assert fail-closed behavior; only the
NEEDS_LIB tests touch the simulator. Spec compliance is a human verdict at
the checkpoint — never a test assertion.

Constitutional Law:
Emits the mandatory BLOCKING HUMAN CHECKPOINT (§8 & §12). Never auto-committed.
"""

from __future__ import annotations

import math
import sqlite3
from collections.abc import Generator
from pathlib import Path

import pytest

from analog_ic_design.circuit.compiler import compile_netlist
from analog_ic_design.circuit.validator import validate
from analog_ic_design.robust.corner import FAST_5_CORNER_ENVELOPE
from analog_ic_design.sim.jobs import JobRunner
from analog_ic_design.sim.miller_opamp import (
    assemble_miller_ac_deck,
    evaluate_miller_candidate,
    format_stage6_checkpoint_alert,
    run_miller_sizing_optimization,
)
from analog_ic_design.sim.ngspice import SimError, libngspice_available
from analog_ic_design.store.schema import connect, migrate
from analog_ic_design.topology import (
    CandidateCircuitIR,
    decide_proposal,
    execute_proposal_workflow,
    instantiate_template,
)

NEEDS_LIB = pytest.mark.skipif(
    not libngspice_available(),
    reason="libngspice absent (base image); covered by CI eda job",
)
SKY130_LIB = "/usr/local/share/pdk/sky130A/libs.tech/ngspice/sky130.lib.spice"


@pytest.fixture()
def db() -> Generator[sqlite3.Connection, None, None]:
    conn = connect()
    migrate(conn)
    yield conn
    conn.close()


def test_miller_deck_assembly(db: sqlite3.Connection) -> None:
    cell_id = instantiate_template(db, "two_stage_miller", cell_name="miller_deck_test")
    report = validate(db, cell_id)
    assert report.valid is True

    frag = compile_netlist(db, cell_id)
    deck = assemble_miller_ac_deck(frag, libs=[("dummy.lib", "tt")])

    assert ".subckt cap_subckt" in deck
    assert ".subckt res_subckt" in deck
    assert "Vbias1" in deck
    assert "Vbias2" in deck
    assert "Vip" in deck
    assert "Vin" in deck
    # Single-ended drive: Vid = Vip - Vin = 1.0 V AC (Stage 6E grounding fix).
    assert "AC 1.0" in deck
    assert "AC -0.5" not in deck
    assert ".ac dec 10 1.0 10000000000.0" in deck
    assert deck.endswith(".end\n")


def test_miller_deck_corner_sections(db: sqlite3.Connection) -> None:
    """Corner plumbing is additive: None keeps the nominal deck byte-identical,
    a corner swaps the .lib section, supply, and .temp (B6 PVT)."""
    cell_id = instantiate_template(db, "two_stage_miller", cell_name="miller_corner_test")
    frag = compile_netlist(db, cell_id)
    nominal = assemble_miller_ac_deck(frag, libs=[("dummy.lib", "tt")])
    assert ".lib 'dummy.lib' tt" in nominal
    assert "VDD vdd 0 DC 1.8" in nominal
    assert ".temp" not in nominal
    corner = next(c for c in FAST_5_CORNER_ENVELOPE if c.process == "ss")
    swept = assemble_miller_ac_deck(frag, libs=[("dummy.lib", "tt")], corner=corner)
    assert ".lib 'dummy.lib' ss" in swept
    assert "VDD vdd 0 DC 1.62" in swept
    assert ".temp 125.00" in swept


def test_miller_evaluation_fails_closed_without_backend(db: sqlite3.Connection) -> None:
    """No simulator backend -> SimError, never an analytical estimate (§9.1)."""
    cand = CandidateCircuitIR(
        topology_id="two_stage_miller",
        parameters={
            "w_in": 12.0e-6, "l_in": 0.5e-6,
            "w_load": 6.0e-6, "l_load": 0.5e-6,
            "w_tail": 6.0e-6, "l_tail": 0.5e-6,
            "w_out": 30.0e-6, "l_out": 0.5e-6,
            "w_load2": 15.0e-6, "l_load2": 0.5e-6,
            "cc": 1.2e-12, "rz": 1500.0,
        },
        reasoning="Fail-closed probe without a backend",
        evidence_ids=("EXP-DEMO-1",),
        requested_spec_id="SPEC-60DB-40MHZ",
    )
    with pytest.raises(SimError, match="requires a simulator backend"):
        evaluate_miller_candidate(db, cand, seed=42)


def test_miller_sizing_fails_closed_without_backend(db: sqlite3.Connection) -> None:
    """Sizing loop writes zero ledger rows when no backend is present."""
    with pytest.raises(SimError, match="requires a simulator backend"):
        run_miller_sizing_optimization(db, n_trials=2, seed=42)

    count = db.execute(
        "SELECT COUNT(*) FROM experiment WHERE study = 'two_stage_miller_sizing_demo'"
    ).fetchone()[0]
    assert count == 0


def test_blocking_human_checkpoint_alert_format() -> None:
    """Verifies the mandatory blocking human checkpoint block matches AGENTS.md §8 & §12."""
    cand = CandidateCircuitIR(
        topology_id="two_stage_miller",
        parameters={
            "w_in": 10.0e-6, "l_in": 0.5e-6,
            "w_load": 5.0e-6, "l_load": 0.5e-6,
            "w_out": 20.0e-6, "l_out": 0.5e-6,
            "cc": 1.2e-12, "rz": 1500.0,
        },
        reasoning="Target: 60 dB gain, 40 MHz UGB",
        evidence_ids=("EXP-OPT-WINNER",),
        requested_spec_id="SPEC-1",
    )

    alert = format_stage6_checkpoint_alert(
        cand,
        validation_status="PASSED",
        simulation_status="PASSED",
        # Illustrative strings (format shape only). Example values transcribed
        # from the live EDA ngspice run 2026-09-09 on the re-baselined sizing
        # (gain 81.30 dB, UGB 16.58 MHz, PM 63.64 deg — gain+PM pass, UGB short).
        constraints_status=(
            "Gain=MEASURED 81.30dB (>=60dB), UGB=MEASURED 16.58MHz (<40MHz)"
            " -> shortfall, human verdict required"
        ),
        diff_summary="[New Cell: two_stage_miller_v1]",
    )

    assert "[ HUMAN CHECKPOINT — Stage 6 / AI design proposal ]" in alert
    assert "Trigger: AI proposed two_stage_miller" in alert
    assert "W_in=10.00um" in alert
    assert "Status: BLOCKING — never auto-committed, even when all checks pass." in alert


def test_stage6_end_to_end_proposal_workflow(db: sqlite3.Connection) -> None:
    """Full workflow: propose -> validate -> simulate -> halt at AWAITING_HUMAN -> commit."""
    proposal = CandidateCircuitIR(
        topology_id="two_stage_miller",
        parameters={
            "w_in": 10.0e-6, "l_in": 0.5e-6,
            "w_load": 5.0e-6, "l_load": 0.5e-6,
            "w_tail": 5.0e-6, "l_tail": 0.5e-6,
            "w_out": 25.0e-6, "l_out": 0.5e-6,
            "w_load2": 12.0e-6, "l_load2": 0.5e-6,
            "cc": 1.2e-12, "rz": 1500.0,
        },
        reasoning="State-machine probe with a simulator stand-in (values are "
        "illustrative test doubles, not measurements).",
        evidence_ids=("EXP-OPT-WINNER",),
        requested_spec_id="SPEC-60DB-40MHZ",
    )

    def sim_cb(conn: sqlite3.Connection, cell_id: str) -> dict[str, float]:
        # Test double standing in for ngspice: exercises the state machine
        # only (the real simulator path is covered by the NEEDS_LIB test).
        # Values are illustrative, never measurements.
        return {"gain_db": 63.0, "ugb_hz": 44.0e6, "pm_deg": 62.0}

    def eval_cb(metrics: dict[str, float]) -> bool:
        return metrics["gain_db"] >= 60.0 and metrics["ugb_hz"] >= 40.0e6

    result = execute_proposal_workflow(
        db,
        proposal,
        simulate_fn=sim_cb,
        evaluate_fn=eval_cb,
    )

    # 1. State must halt at AWAITING_HUMAN
    assert result.state == "AWAITING_HUMAN"
    assert result.validation_passed is True
    assert result.simulation_passed is True
    assert result.evaluation_passed is True
    assert result.measurements is not None
    assert result.measurements["gain_db"] >= 60.0

    # 2. Human explicitly confirms the proposal
    committed = decide_proposal(db, result, decision="accept", design_revision_id="REV-MILLER-V1")
    assert committed.state == "COMMITTED"

    # 3. Provenance record shows acceptance
    row = db.execute(
        "SELECT human_decision, resulting_design_revision FROM ai_action WHERE id = ?",
        (result.action_id,),
    ).fetchone()
    assert row[0] == "accept"
    assert row[1] == "REV-MILLER-V1"


@NEEDS_LIB
def test_live_two_stage_miller_spice_simulation(tmp_path: Path) -> None:
    """Live ngspice-47 BSIM4 measurement of the two-stage Miller (EDA only).

    Asserts honesty properties of a real measurement — finiteness, ledger
    recording, and halting at AWAITING_HUMAN with a checkpoint alert.
    Spec compliance is decided by the human at the checkpoint and is
    NEVER asserted here.
    """
    db_path = tmp_path / "live_miller.sqlite"
    conn = connect(str(db_path))
    migrate(conn)
    jobs = JobRunner(db_path=str(db_path))

    # MEASURED empirical winner (focused physics-guided study, seed 200,
    # trial 17, cost 117.08): gain 81.30dB, UGB 16.58MHz, PM 63.64deg.
    # Gain + PM pass honestly; UGB shorts the 40MHz target. Exact study
    # point, re-simulated here; spec compliance stays a human verdict.
    cand = CandidateCircuitIR(
        topology_id="two_stage_miller",
        parameters={
            "w_in": 2.3878988974264008e-05,
            "l_in": 8.251754636271495e-07,
            "w_load": 1.4489908233410598e-05,
            "l_load": 1.6606568666651572e-06,
            "w_tail": 1.4389752825540067e-05,
            "l_tail": 1.4084257570195117e-06,
            "w_out": 8.625576773440542e-05,
            "l_out": 1.0546596108596654e-06,
            "w_load2": 5.7093097344949095e-05,
            "l_load2": 1.0984928168457911e-06,
            "cc": 1.3346124994111663e-12,
            "rz": 2237.6590261105234,
        },
        reasoning="Live BSIM4 measurement of the re-baselined empirical winner",
        evidence_ids=("LIVE-1",),
        requested_spec_id="SPEC-LIVE-60DB",
    )

    metrics, repro = evaluate_miller_candidate(
        conn, cand, jobs=jobs, sky130_lib=SKY130_LIB, seed=42
    )

    # Honesty properties of a real measurement (never spec compliance:
    # that verdict belongs to the human at the checkpoint, and this
    # sizing honestly shorts the UGB target).
    assert math.isfinite(metrics.gain_db)
    assert math.isfinite(metrics.ugb_hz) and metrics.ugb_hz > 0.0
    assert math.isfinite(metrics.phase_margin_deg)
    assert len(repro) == 64

    # Real-sim Optuna sizing: every trial simulated, every trial recorded.
    winner = run_miller_sizing_optimization(
        conn, target_gain_db=60.0, target_ugb_hz=40.0e6,
        n_trials=6, seed=42, jobs=jobs, sky130_lib=SKY130_LIB,
    )
    assert winner is not None
    assert set(winner.metrics) == {"gain_db", "ugb_hz", "pm_deg"}
    count = conn.execute(
        "SELECT COUNT(*) FROM experiment WHERE study = 'two_stage_miller_sizing_demo'"
    ).fetchone()[0]
    assert count == 6

    # Full proposal workflow on measured data halts at AWAITING_HUMAN.
    def live_sim_cb(c: sqlite3.Connection, cell_id: str) -> dict[str, float]:
        m, _ = evaluate_miller_candidate(
            c, cand, jobs=jobs, sky130_lib=SKY130_LIB, seed=7
        )
        return {"gain_db": m.gain_db, "ugb_hz": m.ugb_hz, "pm_deg": m.phase_margin_deg}

    result = execute_proposal_workflow(
        conn,
        cand,
        simulate_fn=live_sim_cb,
        evaluate_fn=lambda m: m["gain_db"] >= 60.0 and m["ugb_hz"] >= 40.0e6,
    )
    assert result.state == "AWAITING_HUMAN"
    assert result.validation_passed is True
    assert result.simulation_passed is True
    assert isinstance(result.evaluation_passed, bool)
    assert result.measurements is not None

    verdict = "PASS" if result.evaluation_passed else "FAIL vs 60dB/40MHz spec"
    alert = format_stage6_checkpoint_alert(
        cand,
        validation_status="PASSED",
        simulation_status=f"MEASURED gain={metrics.gain_db:.2f}dB "
        f"ugb={metrics.ugb_hz / 1e6:.3f}MHz pm={metrics.phase_margin_deg:.1f}deg",
        constraints_status=f"{verdict} — human verdict required",
        diff_summary="[New Cell: two_stage_miller_v1]",
    )
    assert "[ HUMAN CHECKPOINT — Stage 6 / AI design proposal ]" in alert
    assert "Status: BLOCKING — never auto-committed, even when all checks pass." in alert
    conn.close()
