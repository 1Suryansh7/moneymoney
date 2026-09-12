"""Study supervisor worker (R0-5 Commit 1, RFC-001 §3).

One OS process per study (spawn, non-daemon: it must spawn sim
workers itself, which daemon processes cannot do). Loop: ask Optuna
-> evaluate trial -> tell -> record_experiment, until max trials,
study deadline, or termination from outside (cancel kills this
process; daemon sim workers die with it — no orphans by
construction).

Timeouts: each evaluation runs under a single-thread executor with
`future.result(timeout)` — the thread only blocks on inter-process
waits, never touches libngspice itself. Abandoned evaluations keep
their bounded sim workers, which self-reap on completion; the trial
is recorded failed and the study marches on.

Objectives: `mock` (deterministic synthetic metrics through the real
scalarizer — lifecycle tests, EDA-free), `mock-slow` (mock plus a
20 s sleep — cancel-path tests), `spec` (instantiate template with
trial params, measure every rule metric, scalarize).
"""

from __future__ import annotations

import json
import sqlite3
import time
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeoutError
from typing import Any

from analog_ic_design.optimize.ledger import record_experiment
from analog_ic_design.optimize.optimizer import SearchSpace, TrialResult
from analog_ic_design.optimize.optuna_optimizer import OptunaOptimizer
from analog_ic_design.optimize.scalarizer import TIMEOUT_PENALTY, score_trial
from analog_ic_design.store.schema import connect, utcnow_iso

STUDY_KIND: str = "optimize"
MOCK_OBJECTIVE: str = "mock"
MOCK_SLOW_OBJECTIVE: str = "mock-slow"
SPEC_OBJECTIVE: str = "spec"
OBJECTIVES: tuple[str, ...] = (MOCK_OBJECTIVE, MOCK_SLOW_OBJECTIVE, SPEC_OBJECTIVE)

#: Reconciliation age: optimize jobs untouched longer than this at
#: engine boot are orphans (live studies heartbeat every trial).
ORPHAN_AFTER_S: float = 1800.0


def load_spec_rules(
    conn: sqlite3.Connection, spec_id: str
) -> list[tuple[str, str, float]]:
    """Load (metric, operator, threshold) rules; unknown specs fail closed."""
    exists = conn.execute(
        "SELECT id FROM specification WHERE id = ?", (spec_id,)
    ).fetchone()
    if exists is None:
        raise ValueError(f"Schema: unknown spec_id {spec_id!r}")
    return [
        (str(row[0]), str(row[1]), float(row[2]))
        for row in conn.execute(
            "SELECT metric, operator, threshold FROM constraint_rule"
            " WHERE specification_id = ? ORDER BY priority, id",
            (spec_id,),
        ).fetchall()
    ]


def _mock_metrics(trial_index: int) -> dict[str, float]:
    """Deterministic synthetic metrics (lifecycle paths, never physics)."""
    return {
        "dc_gain": 10.0 + float(trial_index),
        "bandwidth": 1.0e6 * float(trial_index + 1),
    }


def _heartbeat(conn: sqlite3.Connection, job_id: str) -> None:
    conn.execute(
        "UPDATE job SET updated_at = ? WHERE id = ?", (utcnow_iso(), job_id)
    )
    conn.commit()


def _settle(
    conn: sqlite3.Connection,
    job_id: str,
    *,
    status: str,
    result: dict[str, Any] | None = None,
    error: str | None = None,
) -> None:
    conn.execute(
        "UPDATE job SET status = ?, result = ?, error = ?, updated_at = ? WHERE id = ?",
        (
            status,
            json.dumps(result, sort_keys=True) if result is not None else None,
            error,
            utcnow_iso(),
            job_id,
        ),
    )
    conn.commit()


def _evaluate_trial(
    eng: Any,
    *,
    objective: str,
    template_id: str,
    anchor_cell_id: str,
    params: dict[str, float],
    rules: list[tuple[str, str, float]],
    trial_index: int,
) -> tuple[dict[str, float], str, str]:
    """Run one trial; returns (metrics, verdict, status). Never raises."""
    if objective == MOCK_SLOW_OBJECTIVE:
        time.sleep(20.0)
        objective = MOCK_OBJECTIVE
    if objective == MOCK_OBJECTIVE:
        metrics = _mock_metrics(trial_index)
        score = score_trial(metrics, rules)
        return metrics, f"mock score={score:.3f}", "succeeded"
    try:
        cell_id = eng.instantiate(
            cell_id=anchor_cell_id, template_id=template_id, parameters=params
        )
        metrics = {}
        for metric, _, _ in rules:
            if metric not in metrics:
                metrics[metric] = float(
                    eng.measure(cell_id=cell_id, metric_id=metric)
                )
        score = score_trial(metrics, rules)
        return metrics, f"score={score:.6g}", "succeeded"
    except Exception as exc:  # noqa: BLE001 - trials record failures, never raise
        kind = type(exc).__name__
        return {}, f"{kind}: {str(exc).splitlines()[0] if str(exc) else kind}", "failed"


def _study_worker(
    db_path: str,
    job_id: str,
    study_id: str,
    template_id: str,
    spec_id: str,
    space_bounds: dict[str, list[float]],
    seed: int,
    max_trials: int,
    trial_timeout_s: float,
    study_timeout_s: float,
    objective: str,
) -> None:
    """Supervisor entry (module-level: spawn-safe). Trials in, verdicts out."""
    from analog_ic_design.engine.engine_v01 import EngineV01

    conn = connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        conn.execute(
            "UPDATE job SET status = 'running', updated_at = ? WHERE id = ?",
            (utcnow_iso(), job_id),
        )
        conn.commit()
        rules = load_spec_rules(conn, spec_id)
        eng = EngineV01(db_path=db_path)
        try:
            project = eng.create_project(name=f"study-{study_id[:8]}")
            anchor = eng.create_cell(project_id=project, cell_name="anchor")
            opt = OptunaOptimizer(
                SearchSpace({k: (float(v[0]), float(v[1])) for k, v in space_bounds.items()}),
                seed=seed,
                study_name=study_id,
            )
            deadline = time.monotonic() + study_timeout_s
            best: tuple[float, int, dict[str, float]] | None = None
            completed = 0
            pool = ThreadPoolExecutor(max_workers=1)
            try:
                for trial_index in range(max_trials):
                    if time.monotonic() > deadline:
                        _settle(conn, job_id, status="failed",
                                error="Schema: study deadline exceeded with"
                                f" {completed}/{max_trials} trials complete")
                        return
                    params = opt.suggest()
                    future = pool.submit(
                        _evaluate_trial, eng, objective=objective,
                        template_id=template_id, anchor_cell_id=anchor,
                        params=params, rules=rules, trial_index=trial_index,
                    )
                    try:
                        metrics, verdict, status = future.result(
                            timeout=trial_timeout_s
                        )
                        score = (
                            score_trial(metrics, rules)
                            if status == "succeeded"
                            else TIMEOUT_PENALTY
                        )
                    except FuturesTimeoutError:
                        metrics, verdict, status = (
                            {}, "FuturesTimeoutError: trial exceeded"
                            f" {trial_timeout_s}s", "failed",
                        )
                        score = TIMEOUT_PENALTY
                    opt.observe(params, float(score))
                    record_experiment(
                        conn,
                        TrialResult(
                            study=study_id, trial=trial_index, kind="trial",
                            status=status, corner="nominal",
                            parameters=dict(params), metrics=dict(metrics),
                            verdict=verdict, reproducibility_id="",
                            seed=seed, job_id=None,
                        ),
                    )
                    completed += 1
                    if best is None or score > best[0]:
                        best = (score, trial_index, dict(params))
                    _heartbeat(conn, job_id)
            finally:
                pool.shutdown(wait=False, cancel_futures=True)
            if best is None:
                _settle(conn, job_id, status="failed",
                        error="Schema: study completed zero trials")
                return
            _settle(conn, job_id, status="succeeded", result={
                "study_id": study_id,
                "trials_completed": completed,
                "best_trial": best[1],
                "best_params": best[2],
                "best_score": best[0],
            })
        finally:
            eng.close()
    except Exception as exc:  # noqa: BLE001 - verdicts out, always
        try:
            _settle(conn, job_id, status="failed",
                    error=f"{type(exc).__name__}: {exc}")
        finally:
            conn.close()
        return
    conn.close()
