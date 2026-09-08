"""AIAction provenance ledger writer (Stage 5 Commit 5A).

Every AI-generated explanation or narration writes its provenance row
BEFORE anything downstream consumes it — including refusals (a refusal is
provenance too). Secrets must never reach this writer; see the Stage 5B
redaction layer (callers filter first, this module does not inspect values).
"""

from __future__ import annotations

import json
import sqlite3

from analog_ic_design.store.schema import new_id, utcnow_iso

ACTION_TYPES = (
    "explain_failure",
    "narrate_optimization",
    "propose_topology",
    "propose_sizing",
)
HUMAN_DECISIONS = ("accept", "reject", "edited", "n/a")


def record_ai_action(
    conn: sqlite3.Connection,
    *,
    action_type: str,
    model_provider: str,
    model_name: str,
    prompt_version: str,
    input_context_hash: str,
    output_hash: str,
    source_artifacts: tuple[str, ...],
    model_version: str | None = None,
    resulting_design_revision: str | None = None,
    human_decision: str = "n/a",
    token_cost: float | None = None,
    latency_s: float | None = None,
    created_at: str | None = None,
) -> str:
    """Persist one AIAction provenance row; returns the row id."""
    if action_type not in ACTION_TYPES:
        raise ValueError(f"Schema: unknown action_type {action_type!r}")
    if human_decision not in HUMAN_DECISIONS:
        raise ValueError(f"Schema: unknown human_decision {human_decision!r}")
    for label, value in (
        ("model_provider", model_provider),
        ("model_name", model_name),
        ("prompt_version", prompt_version),
        ("input_context_hash", input_context_hash),
        ("output_hash", output_hash),
    ):
        if not value:
            raise ValueError(f"Schema: AIAction {label} must be non-empty")
    aid = new_id()
    conn.execute(
        "INSERT INTO ai_action VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            aid,
            action_type,
            model_provider,
            model_name,
            model_version,
            prompt_version,
            input_context_hash,
            output_hash,
            json.dumps(list(source_artifacts), sort_keys=True),
            resulting_design_revision,
            human_decision,
            token_cost,
            latency_s,
            created_at if created_at is not None else utcnow_iso(),
        ),
    )
    conn.commit()
    return aid
