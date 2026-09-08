"""Stage 5 Commit 5A tests: taxonomy classifier + AIAction ledger.

Pure-logic tests (no model calls anywhere): run on base image with zero skips.
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Generator

import pytest

from analog_ic_design.ai import (
    TAXONOMY,
    ClassifiedFailure,
    classify_failure,
    record_ai_action,
)
from analog_ic_design.store import connect, migrate, new_id

STAMP = "2026-09-05T00:00:00+00:00"


@pytest.fixture()
def db() -> Generator[sqlite3.Connection, None, None]:
    conn = connect()
    migrate(conn)
    yield conn
    conn.close()


def test_taxonomy_is_twelve_in_canonical_order() -> None:
    assert TAXONOMY == (
        "syntax",
        "schema",
        "netlist",
        "spice_convergence",
        "operating_point",
        "constraint",
        "pvt",
        "monte_carlo",
        "drc",
        "lvs",
        "pex",
        "post_layout",
    )


def test_prefix_mapping_and_evidence() -> None:
    got = classify_failure(
        message="SPICE convergence: ngspice 'run' command failed",
        evidence=("JOB-1",),
    )
    assert isinstance(got, ClassifiedFailure)
    assert (got.category, got.trigger, got.evidence) == (
        "spice_convergence",
        "taxonomy-prefixed message (SPICE convergence)",
        ("JOB-1",),
    )
    assert classify_failure(message="Schema: bad cell").category == "schema"
    assert classify_failure(message="Netlist: dangling pin").category == "netlist"


def test_explicit_category_passthrough_and_rejection() -> None:
    assert classify_failure(error_category="monte_carlo").category == "monte_carlo"
    with pytest.raises(ValueError, match="unknown taxonomy category"):
        classify_failure(error_category="vibes")


def test_spec_failure_maps_to_constraint() -> None:
    assert classify_failure(spec_failed=True).category == "constraint"


def test_unknown_evidence_fails_closed() -> None:
    with pytest.raises(ValueError, match="without taxonomy evidence"):
        classify_failure()
    with pytest.raises(ValueError, match="without taxonomy evidence"):
        classify_failure(message="something odd happened")


def _action(**over: object) -> dict[str, object]:
    base: dict[str, object] = {
        "action_type": "explain_failure",
        "model_provider": "mock",
        "model_name": "mock-1",
        "prompt_version": "explain-v1",
        "input_context_hash": "in0",
        "output_hash": "out0",
        "source_artifacts": ("ERR-1",),
    }
    base.update(over)
    return base


def test_ai_action_round_trip(db: sqlite3.Connection) -> None:
    kwargs = _action()
    aid = record_ai_action(
        db,
        action_type=str(kwargs["action_type"]),
        model_provider=str(kwargs["model_provider"]),
        model_name=str(kwargs["model_name"]),
        prompt_version=str(kwargs["prompt_version"]),
        input_context_hash=str(kwargs["input_context_hash"]),
        output_hash=str(kwargs["output_hash"]),
        source_artifacts=tuple(kwargs["source_artifacts"]),  # type: ignore[arg-type]
        created_at=STAMP,
    )
    row = db.execute(
        "SELECT action_type, model_provider, source_artifacts, human_decision"
        " FROM ai_action WHERE id = ?",
        (aid,),
    ).fetchone()
    assert (row[0], row[1]) == ("explain_failure", "mock")
    assert json.loads(row[2]) == ["ERR-1"]
    assert row[3] == "n/a"

    # Also test propose_topology and propose_sizing
    for act in ("propose_topology", "propose_sizing", "narrate_optimization"):
        aid2 = record_ai_action(
            db,
            action_type=act,
            model_provider="mock",
            model_name="mock_v1",
            prompt_version="p1",
            input_context_hash="ctx",
            output_hash="out",
            source_artifacts=("EXP-1",),
        )
        act_row = db.execute("SELECT action_type FROM ai_action WHERE id = ?", (aid2,)).fetchone()
        assert act_row[0] == act


def test_ai_action_rejects_bad_vocabulary(db: sqlite3.Connection) -> None:
    base = _action()
    with pytest.raises(ValueError, match="unknown action_type"):
        record_ai_action(db, **{**base, "action_type": "vibes"})  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="unknown human_decision"):
        record_ai_action(db, **{**base, "human_decision": "maybe"})  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="must be non-empty"):
        record_ai_action(db, **{**base, "model_name": ""})  # type: ignore[arg-type]
    with pytest.raises(sqlite3.IntegrityError):
        db.execute(
            "INSERT INTO ai_action VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (new_id(), "explain_failure", "mock", "m", None, "p", "i", "o", "[]",
             None, "shrug", None, None, STAMP),
        )
