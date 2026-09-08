"""Stage 5 Commit 5C tests: grounded explainer + Mock demos.

Zero network calls: every narration runs through MockProvider. Citation
semantics, refusal behavior, provenance rows, and residency gating are
asserted — never prose eloquence.
"""

from __future__ import annotations

import hashlib
import sqlite3
from collections.abc import Generator

import pytest

from analog_ic_design.ai import (
    REFUSAL,
    MockProvider,
    ProviderGuard,
    classify_failure,
    explain_failure,
    narrate_optimization,
)
from analog_ic_design.ai.residency import DISABLED
from analog_ic_design.store import connect, migrate, new_id

STAMP = "2026-09-05T00:00:00+00:00"


@pytest.fixture()
def db() -> Generator[sqlite3.Connection, None, None]:
    conn = connect()
    migrate(conn)
    yield conn
    conn.close()


def _error_row(db: sqlite3.Connection) -> str:
    eid = new_id()
    db.execute(
        "INSERT INTO error_record (id, cell_id, category, message, created_at)"
        " VALUES (?, ?, ?, ?, ?)",
        (eid, None, "spice_convergence", "ngspice 'run' command failed", STAMP),
    )
    db.commit()
    return eid


def _experiment_row(db: sqlite3.Connection, study: str, trial: int, verdict: str) -> str:
    eid = new_id()
    db.execute(
        "INSERT INTO experiment VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (eid, study, trial, "trial", "succeeded", "nominal", '{"w": 1e-06}',
         '{"dc_gain": 9.1}', verdict, "r" * 64, 7, None, STAMP),
    )
    db.commit()
    return eid


def test_failed_run_explained_with_citation(db: sqlite3.Connection) -> None:
    eid = _error_row(db)
    mock = MockProvider(default_reply=f"Run failed at convergence step ({eid}); see {eid}.")
    classification = classify_failure(error_category="spice_convergence", evidence=(eid,))
    explanation = explain_failure(
        db, classification=classification, provider=mock, guard=ProviderGuard()
    )
    assert eid in explanation.prose
    assert explanation.cited_ids == (eid,)
    row = db.execute(
        "SELECT action_type, output_hash, source_artifacts FROM ai_action WHERE id = ?",
        (explanation.action_id,),
    ).fetchone()
    assert row[0] == "explain_failure"
    assert row[1] == hashlib.sha256(explanation.prose.encode("utf-8")).hexdigest()
    assert eid in row[2]


def test_completed_run_narrated_with_citations(db: sqlite3.Connection) -> None:
    first = _experiment_row(db, "demo", 0, "pass")
    second = _experiment_row(db, "demo", 1, "pass")
    mock = MockProvider(default_reply=f"Best trial {first}; runner-up {second}.")
    explanation = narrate_optimization(
        db,
        study_summary="8 trials seed 7",
        experiment_ids=(first, second),
        provider=mock,
        guard=ProviderGuard(),
    )
    assert explanation.cited_ids == (first, second)
    row = db.execute(
        "SELECT action_type FROM ai_action WHERE id = ?", (explanation.action_id,)
    ).fetchone()
    assert row[0] == "narrate_optimization"


def test_empty_evidence_refuses(db: sqlite3.Connection) -> None:
    mock = MockProvider(default_reply="A plausible story with no grounding.")
    classification = classify_failure(spec_failed=True, evidence=())
    explanation = explain_failure(
        db, classification=classification, provider=mock, guard=ProviderGuard()
    )
    assert explanation.prose == REFUSAL
    assert explanation.cited_ids == ()
    row = db.execute(
        "SELECT output_hash, source_artifacts FROM ai_action WHERE id = ?",
        (explanation.action_id,),
    ).fetchone()
    assert row[0] == hashlib.sha256(REFUSAL.encode("utf-8")).hexdigest()
    assert row[1] == "[]"


def test_uncited_prose_refuses(db: sqlite3.Connection) -> None:
    eid = _error_row(db)
    mock = MockProvider(default_reply="Something failed somewhere, trust me.")
    classification = classify_failure(error_category="spice_convergence", evidence=(eid,))
    explanation = explain_failure(
        db, classification=classification, provider=mock, guard=ProviderGuard()
    )
    assert explanation.prose == REFUSAL
    assert explanation.cited_ids == ()


def test_unknown_evidence_fails_closed(db: sqlite3.Connection) -> None:
    mock = MockProvider()
    classification = classify_failure(error_category="schema", evidence=("no-such-id",))
    with pytest.raises(ValueError, match="no ledger row"):
        explain_failure(
            db, classification=classification, provider=mock, guard=ProviderGuard()
        )


def test_disabled_guard_blocks_mock(db: sqlite3.Connection) -> None:
    mock = MockProvider()
    classification = classify_failure(spec_failed=True, evidence=())
    with pytest.raises(PermissionError, match="blocked"):
        explain_failure(
            db,
            classification=classification,
            provider=mock,
            guard=ProviderGuard(mode=DISABLED),
        )
