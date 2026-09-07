"""Stage 4 Commit 4D: live cs_amp sizing demo (first demoable product).

An 8-trial seeded Optuna study sizes the common-source amplifier against
a real hard-constraint spec using real simulations. Every trial writes one
`job` row plus one `experiment` row (success and failure alike); trial sims
run in worker processes with timeouts (a hung simulator marks the trial
failed instead of hanging the study — failures are data).
Reproducibility: the winner is re-simulated once and must match within
tolerance; trial count + seed are reported, never omitted (playbook rule).
Runs under `@NEEDS_LIB`.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from analog_ic_design.circuit import compile_netlist, validate
from analog_ic_design.metrics.bandwidth import extract_bandwidth
from analog_ic_design.metrics.evaluator import evaluate_specification
from analog_ic_design.metrics.gain import extract_dc_gain
from analog_ic_design.optimize import (
    OptunaOptimizer,
    SearchSpace,
    TrialResult,
    list_experiments,
    record_experiment,
)
from analog_ic_design.sim.cs_amp import build_cs_amplifier
from analog_ic_design.sim.jobs import JobRunner
from analog_ic_design.sim.ngspice import RawSim, SimError, libngspice_available
from analog_ic_design.sim.reproduce import design_identity_hash
from analog_ic_design.sim.testbench import assemble_ac, assemble_dc_sweep
from analog_ic_design.sim.waveform import parse_ac
from analog_ic_design.store import connect, migrate, new_id, utcnow_iso

NEEDS_LIB = pytest.mark.skipif(
    not libngspice_available(),
    reason="libngspice absent (base image); covered by CI eda job",
)

SKY130_LIB = "/usr/local/share/pdk/sky130A/libs.tech/ngspice/sky130.lib.spice"
STUDY = "cs_amp_demo"
SEED = 7
N_TRIALS = 8
SIM_TIMEOUT = 240.0
SPACE = SearchSpace({"w_n": (0.5e-06, 3e-06), "w_p": (1e-06, 6e-06)})


def _run_sim(jobs: JobRunner, deck: str, seed: int) -> dict[str, list[float]]:
    """Run one deck in a worker; timeouts fail closed, never hang."""
    jid = jobs.submit_simulation(netlist=deck, seed=seed)
    try:
        result = jobs.wait(jid, timeout=SIM_TIMEOUT)
    except TimeoutError:
        jobs.cancel(jid)
        raise SimError("SPICE convergence: trial simulation timed out") from None
    if result.status != "succeeded" or result.result is None:
        raise SimError(f"SPICE convergence: trial simulation failed: {result.error}")
    return dict(json.loads(result.result)["vectors"])


def _sim_point(
    jobs: JobRunner, w_n: float, w_p: float, seed: int
) -> tuple[dict[str, float], str]:
    """Validate, compile, DC-sweep + AC the sized cell; returns metrics + repro id."""
    conn = connect()
    migrate(conn)
    cell = build_cs_amplifier(conn, w_n=w_n, w_p=w_p)
    report = validate(conn, cell)
    if not report.valid:
        conn.close()
        raise SimError(
            f"Schema: sized cell invalid: {[v.message for v in report.violations]}"
        )
    frag = compile_netlist(conn, cell)
    conn.close()
    dc_deck = assemble_dc_sweep(
        frag,
        sweep_net="in",
        v_start=0.4,
        v_stop=1.2,
        v_step=0.005,
        extra_lines=["Vbias vbias 0 DC 0.9"],
        libs=[(SKY130_LIB, "tt")],
    )
    raw_dc = _run_sim(jobs, dc_deck, seed)
    vin, vout = raw_dc["in"], raw_dc["out"]
    dc_gain = extract_dc_gain(vin, vout)
    slopes = [abs((vout[i + 1] - vout[i]) / (vin[i + 1] - vin[i])) for i in range(len(vin) - 1)]
    bias = vin[slopes.index(max(slopes))]
    ac_deck = assemble_ac(
        frag,
        in_net="in",
        v_bias=bias,
        ac_mag=1.0,
        f_start=1.0,
        f_stop=1e10,
        points_per_decade=10,
        extra_lines=["Vbias vbias 0 DC 0.9", "Cload out 0 1p"],
        libs=[(SKY130_LIB, "tt")],
    )
    raw_ac = _run_sim(jobs, ac_deck, seed + 1)
    wave = parse_ac(RawSim(vectors=raw_ac, log=""))
    ugb = extract_bandwidth(wave)
    repro = design_identity_hash(netlist=ac_deck, sim_config={"seed": seed})
    return {"dc_gain": dc_gain, "bandwidth": ugb}, repro


def _make_spec(conn: sqlite3.Connection) -> str:
    stamp = "2026-09-07T00:00:00+00:00"
    pid, lib, cell, spec = (new_id() for _ in range(4))
    conn.execute("INSERT INTO project VALUES (?, ?, ?)", (pid, "demo", stamp))
    conn.execute("INSERT INTO library VALUES (?, ?, ?, ?)", (lib, pid, "l", stamp))
    conn.execute("INSERT INTO cell VALUES (?, ?, ?, ?)", (cell, lib, "amp", stamp))
    conn.execute("INSERT INTO specification VALUES (?, ?, ?, ?)", (spec, cell, "demo-spec", stamp))
    for kind, metric, op, thr, tol, prio in (
        ("hard", "dc_gain", ">=", 8.0, 0.1, 1),
        ("hard", "bandwidth", ">=", 10e6, 1e5, 2),
    ):
        conn.execute(
            "INSERT INTO constraint_rule VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (new_id(), spec, kind, metric, op, thr, tol, prio, None, stamp),
        )
    conn.commit()
    return spec


@NEEDS_LIB
def test_cs_amp_sized_against_spec_reproducibly(tmp_path: Path) -> None:
    ledger = connect(str(tmp_path / "ledger.sqlite"))
    migrate(ledger)
    spec = _make_spec(ledger)
    jobs = JobRunner(db_path=str(tmp_path / "ledger.sqlite"))
    try:
        opt = OptunaOptimizer(SPACE, seed=SEED, study_name=STUDY)
        best: TrialResult | None = None
        for trial in range(N_TRIALS):
            params = opt.suggest()
            assert SPACE.in_bounds(params)
            jid = new_id()
            stamp = utcnow_iso()
            try:
                metrics, repro = _sim_point(jobs, params["w_n"], params["w_p"], SEED)
                status, verdict = "succeeded", "pass"
            except SimError as exc:
                metrics, repro = {}, "n/a"
                status, verdict = "failed", f"{type(exc).__name__}: {exc}"
            ledger.execute(
                "INSERT INTO job VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (jid, "trial", status, json.dumps(params, sort_keys=True),
                 json.dumps(metrics, sort_keys=True),
                 None if status == "succeeded" else verdict, stamp, stamp),
            )
            ledger.commit()
            if status == "succeeded":
                report = evaluate_specification(ledger, spec, metrics)
                verdict = "pass" if report.passed else "constraint"
            result = TrialResult(
                study=STUDY, trial=trial, kind="trial", status=status, corner="nominal",
                parameters=params, metrics=metrics, verdict=verdict,
                reproducibility_id=repro, seed=SEED, job_id=jid,
            )
            record_experiment(ledger, result)
            opt.observe(params, metrics.get("bandwidth", 0.0))
            if status == "succeeded" and (
                best is None or metrics["bandwidth"] > best.metrics["bandwidth"]
            ):
                best = result
        rows = list_experiments(ledger, STUDY)
        assert len(rows) == N_TRIALS
        assert best is not None, f"no passing trial in {N_TRIALS} trials (seed {SEED})"
        assert best.verdict == "pass", f"best trial violates spec: {best.metrics}"
        print(
            f"study={STUDY} trials={N_TRIALS} seed={SEED}"
            f" winner_trial={best.trial} params={best.parameters}"
            f" metrics={best.metrics}"
        )
        for name, (low, high) in SPACE.bounds.items():
            value = best.parameters[name]
            span = high - low
            if value - low < 0.01 * span or high - value < 0.01 * span:
                print(
                    "[ HUMAN CHECKPOINT — Stage 4 / Optimizer results ]\n"
                    f"Trigger: winning trial sits at a search-space boundary ({name}={value!r}).\n"
                    f"Check: winner {best.parameters} vs bounds {dict(SPACE.bounds)};"
                    f" metrics {best.metrics}. Confirm the spec is real.\n"
                    "Status: ADVISORY — proceeding, but flagged."
                )
        # Reproducibility: re-simulate the winner; metrics must match in tolerance.
        check, _repro = _sim_point(jobs, best.parameters["w_n"], best.parameters["w_p"], SEED)
        for metric, value in best.metrics.items():
            assert check[metric] == pytest.approx(value, rel=1e-6)
    finally:
        jobs.shutdown()
        ledger.close()
