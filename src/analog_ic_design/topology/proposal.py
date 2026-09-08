"""CandidateCircuitIR and Proposal Workflow State Machine (Stage 6 Commit 6C).

Implements the proposal state machine:
AI proposes -> schema validation -> simulate -> check_constraints
-> human approval (accept / reject / compare) -> commit.

Constitutional Rules (AGENTS.md & final_build.md §4):
1. The AI outputs CandidateCircuitIR, never free prose.
2. Immediate provenance: writes an AIAction row the moment a proposal is generated,
   BEFORE validation or simulation runs.
3. Fail-closed: malformed proposals or schema violations transition to REJECTED.
4. Human gate: no code path from passing checks to COMMITTED without explicit human decision.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from collections.abc import Callable
from dataclasses import dataclass
from typing import Final

from analog_ic_design.ai.actions import record_ai_action
from analog_ic_design.circuit.validator import record_errors, validate
from analog_ic_design.topology.templates import REGISTERED_TEMPLATES, instantiate_template

STAMP: Final = "2026-09-08T00:00:00+00:00"

WORKFLOW_STATES: Final = (
    "PROPOSED",
    "VALIDATED",
    "SIMULATED",
    "EVALUATED",
    "AWAITING_HUMAN",
    "COMMITTED",
    "REJECTED",
)


@dataclass(frozen=True)
class CandidateCircuitIR:
    """Structured machine-readable design proposal object."""

    topology_id: str
    parameters: dict[str, float]
    reasoning: str
    evidence_ids: tuple[str, ...]
    requested_spec_id: str
    confidence: str = "high"

    def validate_schema(self) -> None:
        """Enforces schema, known template, valid SI bounds, and grounded citations."""
        if self.topology_id not in REGISTERED_TEMPLATES:
            raise ValueError(f"Schema: unknown topology_id {self.topology_id!r}")
        if not self.parameters:
            raise ValueError("Schema: candidate parameters dictionary must not be empty")
        for key, val in self.parameters.items():
            if isinstance(val, bool) or not isinstance(val, (int, float)):
                raise ValueError(
                    f"Units: parameter {key!r} must be a numeric SI value, got {val!r}"
                )
            if val <= 0:
                raise ValueError(
                    f"Units: parameter {key!r} must be strictly positive, got {val!r}"
                )
        if not self.evidence_ids:
            raise ValueError("Grounding: AI proposal must cite at least one evidence ID")
        if self.confidence not in ("high", "medium", "low"):
            raise ValueError(f"Schema: invalid confidence {self.confidence!r}")


@dataclass(frozen=True)
class ProposalWorkflowResult:
    """Outcome of executing the proposal state machine."""

    action_id: str
    candidate: CandidateCircuitIR
    state: str
    cell_id: str | None = None
    validation_passed: bool = False
    simulation_passed: bool = False
    evaluation_passed: bool = False
    measurements: dict[str, float] | None = None
    error_message: str | None = None


def _hash_obj(obj: object) -> str:
    """Deterministic SHA-256 hex string."""
    encoded = json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def execute_proposal_workflow(
    conn: sqlite3.Connection,
    candidate: CandidateCircuitIR,
    *,
    model_provider: str = "mock",
    model_name: str = "mock_proposer_v1",
    prompt_version: str = "stage6_v1",
    simulate_fn: Callable[[sqlite3.Connection, str], dict[str, float]] | None = None,
    evaluate_fn: Callable[[dict[str, float]], bool] | None = None,
) -> ProposalWorkflowResult:
    """Execute proposal state machine with fail-closed gates and immediate provenance."""
    # Step 1: Immediate provenance logging BEFORE validation or simulation
    input_ctx = {
        "requested_spec_id": candidate.requested_spec_id,
        "evidence_ids": list(candidate.evidence_ids),
    }
    output_ctx = {
        "topology_id": candidate.topology_id,
        "parameters": candidate.parameters,
        "confidence": candidate.confidence,
    }
    input_hash = _hash_obj(input_ctx)
    output_hash = _hash_obj(output_ctx)

    action_id = record_ai_action(
        conn,
        action_type="propose_topology",
        model_provider=model_provider,
        model_name=model_name,
        prompt_version=prompt_version,
        input_context_hash=input_hash,
        output_hash=output_hash,
        source_artifacts=candidate.evidence_ids,
        human_decision="n/a",
    )

    # Step 2: Schema validation of the structured object
    try:
        candidate.validate_schema()
    except ValueError as exc:
        conn.execute(
            "INSERT INTO error_record VALUES (?, NULL, ?, ?, ?)",
            (hashlib.sha256(str(exc).encode()).hexdigest()[:32], "schema", str(exc), STAMP),
        )
        conn.commit()
        return ProposalWorkflowResult(
            action_id=action_id,
            candidate=candidate,
            state="REJECTED",
            error_message=f"Schema validation failed: {exc}",
        )

    # Instantiate relational cell into SQLite
    cell_id = instantiate_template(
        conn,
        candidate.topology_id,
        params=candidate.parameters,
        cell_name=f"prop_{candidate.topology_id}",
    )

    # Pre-simulation validation gate (Law 3: Zero bypass)
    report = validate(conn, cell_id)
    if not report.valid:
        record_errors(conn, cell_id, report)
        return ProposalWorkflowResult(
            action_id=action_id,
            candidate=candidate,
            state="REJECTED",
            cell_id=cell_id,
            error_message="Circuit validation gate failed",
        )

    # Step 3: Simulation (if simulation callback provided)
    measurements: dict[str, float] | None = None
    sim_passed = True
    if simulate_fn is not None:
        try:
            measurements = simulate_fn(conn, cell_id)
        except Exception as exc:  # noqa: BLE001
            conn.execute(
                "INSERT INTO error_record VALUES (?, ?, ?, ?, ?)",
                (
                    hashlib.sha256(str(exc).encode()).hexdigest()[:32],
                    cell_id,
                    "spice_convergence",
                    str(exc),
                    STAMP,
                ),
            )
            conn.commit()
            return ProposalWorkflowResult(
                action_id=action_id,
                candidate=candidate,
                state="REJECTED",
                cell_id=cell_id,
                validation_passed=True,
                error_message=f"Simulation failed: {exc}",
            )

    # Step 4: Constraint evaluation
    eval_passed = True
    if evaluate_fn is not None and measurements is not None:
        eval_passed = evaluate_fn(measurements)

    # Step 5: Transition to AWAITING_HUMAN (Never auto-commits!)
    return ProposalWorkflowResult(
        action_id=action_id,
        candidate=candidate,
        state="AWAITING_HUMAN",
        cell_id=cell_id,
        validation_passed=True,
        simulation_passed=sim_passed,
        evaluation_passed=eval_passed,
        measurements=measurements,
    )


def decide_proposal(
    conn: sqlite3.Connection,
    result: ProposalWorkflowResult,
    decision: str,
    *,
    design_revision_id: str | None = None,
) -> ProposalWorkflowResult:
    """Human decision gate: accepts or rejects proposal and updates provenance."""
    if result.state != "AWAITING_HUMAN":
        raise ValueError(
            f"State error: cannot decide proposal in state {result.state!r} "
            "(must be 'AWAITING_HUMAN')"
        )
    if decision not in ("accept", "reject"):
        raise ValueError(f"Decision error: decision must be 'accept' or 'reject', got {decision!r}")

    new_state = "COMMITTED" if decision == "accept" else "REJECTED"
    conn.execute(
        "UPDATE ai_action SET human_decision = ?, resulting_design_revision = ? WHERE id = ?",
        (decision, design_revision_id, result.action_id),
    )
    conn.commit()

    return ProposalWorkflowResult(
        action_id=result.action_id,
        candidate=result.candidate,
        state=new_state,
        cell_id=result.cell_id,
        validation_passed=result.validation_passed,
        simulation_passed=result.simulation_passed,
        evaluation_passed=result.evaluation_passed,
        measurements=result.measurements,
    )
