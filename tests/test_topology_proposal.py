"""Tests for CandidateCircuitIR & Proposal State Machine (Stage 6 Commit 6C).

Verifies:
1. CandidateCircuitIR immutability, schema validation, and citation requirements.
2. AIAction provenance row is written immediately upon generation BEFORE validation.
3. Proposal state machine transitions: PROPOSED -> VALIDATED -> SIMULATED -> AWAITING_HUMAN.
4. Fail-closed behavior: malformed proposals transition to REJECTED and record ErrorRecord.
5. Mandatory Human Gate: No code path auto-commits; requires explicit human decision.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Generator
from dataclasses import FrozenInstanceError

import pytest

from analog_ic_design.store.schema import connect, migrate
from analog_ic_design.topology import (
    CandidateCircuitIR,
    decide_proposal,
    execute_proposal_workflow,
)


@pytest.fixture()
def db() -> Generator[sqlite3.Connection, None, None]:
    conn = connect()
    migrate(conn)
    yield conn
    conn.close()


def _valid_candidate() -> CandidateCircuitIR:
    return CandidateCircuitIR(
        topology_id="common_source",
        parameters={"w_n": 1.5e-6, "l_n": 0.18e-6, "w_p": 3.0e-6, "l_p": 0.18e-6},
        reasoning="Sized for 18 dB gain and 80 MHz bandwidth based on historical trial EXP-42.",
        evidence_ids=("EXP-42",),
        requested_spec_id="SPEC-1",
        confidence="high",
    )


def test_candidate_ir_immutability_and_schema_validation() -> None:
    c = _valid_candidate()
    c.validate_schema()

    # Immutability
    with pytest.raises(FrozenInstanceError):
        c.confidence = "low"  # type: ignore[misc]

    # Rejection of unknown topology
    with pytest.raises(ValueError, match="unknown topology_id"):
        CandidateCircuitIR(
            topology_id="space_laser",
            parameters={"w": 1e-6},
            reasoning="none",
            evidence_ids=("EXP-1",),
            requested_spec_id="S1",
        ).validate_schema()

    # Rejection of non-SI units / string parameters
    with pytest.raises(ValueError, match="must be a numeric SI value"):
        CandidateCircuitIR(
            topology_id="common_source",
            parameters={"w_n": "1.5u"},  # type: ignore[dict-item]
            reasoning="none",
            evidence_ids=("EXP-1",),
            requested_spec_id="S1",
        ).validate_schema()

    # Rejection of non-positive parameter
    with pytest.raises(ValueError, match="must be strictly positive"):
        CandidateCircuitIR(
            topology_id="common_source",
            parameters={"w_n": -1.0e-6},
            reasoning="none",
            evidence_ids=("EXP-1",),
            requested_spec_id="S1",
        ).validate_schema()

    # Rejection of uncited proposal (Grounding Rule)
    with pytest.raises(ValueError, match="must cite at least one evidence ID"):
        CandidateCircuitIR(
            topology_id="common_source",
            parameters={"w_n": 1.0e-6},
            reasoning="hallucinated sizing",
            evidence_ids=(),
            requested_spec_id="S1",
        ).validate_schema()


def test_immediate_ai_action_provenance_logging(db: sqlite3.Connection) -> None:
    c = _valid_candidate()
    res = execute_proposal_workflow(db, c, model_name="test_model", prompt_version="v1")

    # Assert AIAction row was persisted
    query = (
        "SELECT id, action_type, model_name, source_artifacts, human_decision"
        " FROM ai_action WHERE id = ?"
    )
    row = db.execute(query, (res.action_id,)).fetchone()
    assert row is not None
    assert row[1] == "propose_topology"
    assert row[2] == "test_model"
    assert "EXP-42" in row[3]
    assert row[4] == "n/a"


def test_proposal_workflow_execution_and_human_decision_gate(db: sqlite3.Connection) -> None:
    c = _valid_candidate()

    def mock_simulate(conn: sqlite3.Connection, cell_id: str) -> dict[str, float]:
        return {"gain_v_v": 8.5, "ugb_hz": 75e6}

    def mock_evaluate(metrics: dict[str, float]) -> bool:
        return metrics["gain_v_v"] >= 8.0

    res = execute_proposal_workflow(
        db,
        c,
        simulate_fn=mock_simulate,
        evaluate_fn=mock_evaluate,
    )

    # Workflow must stop at AWAITING_HUMAN — never auto-commit!
    assert res.state == "AWAITING_HUMAN"
    assert res.validation_passed is True
    assert res.simulation_passed is True
    assert res.evaluation_passed is True
    assert res.measurements is not None
    assert res.measurements["gain_v_v"] == 8.5

    # Human commits the design
    committed = decide_proposal(db, res, decision="accept", design_revision_id="REV-1")
    assert committed.state == "COMMITTED"

    # AIAction provenance updated to accept
    action_decision = db.execute(
        "SELECT human_decision, resulting_design_revision FROM ai_action WHERE id = ?",
        (res.action_id,),
    ).fetchone()
    assert action_decision[0] == "accept"
    assert action_decision[1] == "REV-1"


def test_proposal_workflow_fail_closed_on_schema_violation(db: sqlite3.Connection) -> None:
    # Proposal with invalid negative width
    bad_cand = CandidateCircuitIR(
        topology_id="common_source",
        parameters={"w_n": -2.0e-6},
        reasoning="invalid",
        evidence_ids=("EXP-1",),
        requested_spec_id="S1",
    )
    res = execute_proposal_workflow(db, bad_cand)

    # Must fail closed to REJECTED
    assert res.state == "REJECTED"
    assert res.validation_passed is False
    assert "Schema validation failed" in str(res.error_message)

    # Provenance action was still logged!
    count = db.execute(
        "SELECT COUNT(*) FROM ai_action WHERE id = ?", (res.action_id,)
    ).fetchone()[0]
    assert count == 1

    # ErrorRecord was logged with taxonomy 'schema'
    err = db.execute("SELECT category, message FROM error_record").fetchone()
    assert err is not None
    assert err[0] == "schema"


def test_human_gate_rejection(db: sqlite3.Connection) -> None:
    c = _valid_candidate()
    res = execute_proposal_workflow(db, c)
    assert res.state == "AWAITING_HUMAN"

    # Human rejects the proposal
    rejected = decide_proposal(db, res, decision="reject")
    assert rejected.state == "REJECTED"

    action_row = db.execute(
        "SELECT human_decision FROM ai_action WHERE id = ?", (res.action_id,)
    ).fetchone()
    assert action_row[0] == "reject"
