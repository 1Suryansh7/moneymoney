"""Tests for Design Knowledge Base & Multi-Criteria Retrieval Engine (Stage 6 Commit 6B).

Covers:
1. Knowledge base linkage to `experiment` table and empirical capability bounds.
2. Multi-criteria retrieval ranking: spec similarity, topology compatibility, yield.
3. Adversarial Test (AI-03): Retriever refuses to blindly copy a failed sizing even
   when that failed trial had nominally higher specification match.
4. Retrieval includes both positive evidence IDs and known failure modes.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Generator

import pytest

from analog_ic_design.optimize.optimizer import TrialResult
from analog_ic_design.store.schema import connect, migrate
from analog_ic_design.topology import (
    TargetSpec,
    get_template_experiments,
    query_template_capabilities,
    record_template_experiment,
    retrieve_best_sizing,
    retrieve_candidate_topologies,
)


@pytest.fixture()
def db() -> Generator[sqlite3.Connection, None, None]:
    conn = connect()
    migrate(conn)
    yield conn
    conn.close()


def _make_trial(
    study: str,
    trial: int,
    status: str,
    params: dict[str, float],
    metrics: dict[str, float],
    verdict: str = "pass",
) -> TrialResult:
    return TrialResult(
        study=study,
        trial=trial,
        kind="trial",
        status=status,
        corner="nominal",
        parameters=params,
        metrics=metrics,
        verdict=verdict,
        reproducibility_id="r" * 64,
        seed=42,
        job_id=None,
    )


def test_knowledge_base_recording_and_capability_bounds(db: sqlite3.Connection) -> None:
    # Initially empty
    caps0 = query_template_capabilities(db, "two_stage_miller")
    assert caps0.total_trials == 0
    assert caps0.min_gain is None

    # Record 3 trials: 2 succeeded, 1 failed
    record_template_experiment(
        db,
        "two_stage_miller",
        _make_trial(
            "two_stage_miller_run",
            1,
            "succeeded",
            {"w_in": 5e-6, "cc": 1e-12},
            {"gain": 1200.0, "bandwidth": 42e6, "power": 0.5e-3},
        ),
    )
    record_template_experiment(
        db,
        "two_stage_miller",
        _make_trial(
            "two_stage_miller_run",
            2,
            "succeeded",
            {"w_in": 8e-6, "cc": 1.2e-12},
            {"gain": 1500.0, "bandwidth": 38e6, "power": 0.6e-3},
        ),
    )
    record_template_experiment(
        db,
        "two_stage_miller",
        _make_trial(
            "two_stage_miller_run",
            3,
            "failed",
            {"w_in": 30e-6, "cc": 0.1e-12},
            {"gain": 0.0},
            verdict="Operating point: saturation violated",
        ),
    )

    trials = get_template_experiments(db, "two_stage_miller")
    assert len(trials) == 3

    caps = query_template_capabilities(db, "two_stage_miller")
    assert caps.total_trials == 3
    assert caps.successful_trials == 2
    assert caps.failed_trials == 1
    assert caps.yield_rate == pytest.approx(2.0 / 3.0)
    assert caps.min_gain == pytest.approx(1200.0)
    assert caps.max_gain == pytest.approx(1500.0)
    assert caps.max_bandwidth == pytest.approx(42e6)


def test_multi_criteria_retrieval_topology_ranking(db: sqlite3.Connection) -> None:
    # 1. Request differential input with 60 dB gain (>1000 V/V)
    spec_high_gain = TargetSpec(gain_v_v=1000.0, is_differential=True)
    ranked = retrieve_candidate_topologies(db, spec_high_gain)

    # Top choices must be two_stage_miller or folded_cascode
    top_ids = [c.template_id for c in ranked[:2]]
    assert "two_stage_miller" in top_ids or "folded_cascode" in top_ids
    # Single-ended or mirror templates must not win
    assert ranked[0].template_id not in ("current_mirror", "common_source")

    # 2. Request current mirror
    spec_mirror = TargetSpec(is_mirror=True)
    ranked_mirror = retrieve_candidate_topologies(db, spec_mirror)
    assert ranked_mirror[0].template_id == "current_mirror"

    # 3. Incompatible topologies must receive 0 topology compatibility
    diff_req = TargetSpec(is_differential=True)
    ranked_diff = retrieve_candidate_topologies(db, diff_req)
    for c in ranked_diff:
        if c.template_id in ("common_source", "current_mirror", "cascode"):
            assert c.topology_compat == 0.0


def test_adversarial_retrieval_rejects_failed_sizing(db: sqlite3.Connection) -> None:
    """Mandatory Adversarial Test per final_prompt.md §10.5 (AI-03).

    Trial 1: Semantically closest to target (gain=1000.0), but FAILED hard constraints.
    Trial 2: Slightly lower nominal gain (gain=850.0), but SUCCEEDED robustly.
    The retriever MUST NOT copy the failed sizing from Trial 1.
    """
    # Trial 1: Failed catastrophic sizing
    record_template_experiment(
        db,
        "two_stage_miller",
        _make_trial(
            "two_stage_miller_adv",
            1,
            "failed",
            {"w_in": 25.0e-06, "w_out": 80.0e-06, "cc": 0.05e-12},
            {"gain": 1000.0},  # Matches nominal target perfectly on paper
            verdict="SPICE convergence: operating point failure",
        ),
    )
    # Trial 2: Succeeded robust sizing
    t2_id = record_template_experiment(
        db,
        "two_stage_miller",
        _make_trial(
            "two_stage_miller_adv",
            2,
            "succeeded",
            {"w_in": 6.0e-06, "w_out": 22.0e-06, "cc": 1.2e-12},
            {"gain": 850.0},
            verdict="pass",
        ),
    )

    # Ask retriever for sizing best matching target_metric gain=1000.0
    best_params, evidence = retrieve_best_sizing(
        db, "two_stage_miller", target_metric={"gain": 1000.0}
    )

    # Adversarial verification: retriever must select Trial 2 and NOT Trial 1
    assert best_params["w_in"] == pytest.approx(6.0e-06), (
        f"Retriever copied failed trial! w_in was {best_params['w_in']}"
    )
    assert best_params["cc"] == pytest.approx(1.2e-12)
    assert t2_id in evidence


def test_retrieval_returns_evidence_and_failure_ids(db: sqlite3.Connection) -> None:
    eid_success = record_template_experiment(
        db,
        "cascode",
        _make_trial("cascode_demo", 1, "succeeded", {"w_in": 3e-6}, {"gain": 80.0}),
    )
    eid_fail = record_template_experiment(
        db,
        "cascode",
        _make_trial("cascode_demo", 2, "failed", {"w_in": 0.1e-6}, {"gain": 0.0}, "crash"),
    )

    candidates = retrieve_candidate_topologies(db, TargetSpec(gain_v_v=80.0))
    cascode_cand = next(c for c in candidates if c.template_id == "cascode")

    assert eid_success in cascode_cand.evidence_ids
    assert eid_fail in cascode_cand.failure_ids
    assert "Composite score" in cascode_cand.reasoning
