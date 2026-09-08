"""Grounded failure explainer and optimization narrator (Stage 5 Commit 5C).

CLASSIFY FIRST, EXPLAIN SECOND: evidence resolves to ledger rows, a model
writes prose about exactly those rows, and a code-level citation check
decides what ships. Citation semantics are substring-level and documented
as such: `cited_ids` are the evidence IDs appearing verbatim in the prose;
empty set means refusal — never narration. This catches uncited prose
deterministically; it does not judge semantic truth (nothing short of a
human does that — see the advisory checkpoint).

Every call writes its `AIAction` row BEFORE returning, refusals included.
"""

from __future__ import annotations

import hashlib
import sqlite3
import time
from dataclasses import dataclass
from typing import Final

from analog_ic_design.ai.actions import record_ai_action
from analog_ic_design.ai.provider import LLMProvider, LLMRequest
from analog_ic_design.ai.residency import ProviderGuard
from analog_ic_design.ai.taxonomy import ClassifiedFailure

REFUSAL: Final = "Insufficient data to explain this failure."

SHIPPED_SYSTEM_PROMPT: Final = (
    "You explain analog simulation failures. You are given a classified ErrorRecord"
    " and its associated Measurements. You may ONLY state things present in that data."
    " You may not speculate about causes not evidenced in the record. If the record is"
    ' insufficient, say exactly: "Insufficient data to explain this failure."'
    " Never invent a numeric value. Never suggest a fix you cannot ground in the record."
    " End every explanation with the ErrorRecord ID you used."
)

_EXPLAIN_VERSION: Final = "explain-v1"
_NARRATE_VERSION: Final = "narrate-v1"


@dataclass(frozen=True)
class Explanation:
    """Explainer outcome: prose, verbatim-cited evidence, provenance id."""

    prose: str
    cited_ids: tuple[str, ...]
    action_id: str


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _resolve_evidence(conn: sqlite3.Connection, evidence: tuple[str, ...]) -> str:
    """Serialize ledger rows for `evidence` IDs; fail closed on unknown IDs."""
    blocks: list[str] = []
    for eid in evidence:
        row = conn.execute(
            "SELECT category, message FROM error_record WHERE id = ?", (eid,)
        ).fetchone()
        if row is not None:
            blocks.append(f"ErrorRecord {eid}: [{row[0]}] {row[1]}")
            continue
        row = conn.execute(
            "SELECT metric_id, value, units FROM measurement WHERE id = ?", (eid,)
        ).fetchone()
        if row is not None:
            blocks.append(f"Measurement {eid}: {row[0]}={row[1]} {row[2]}")
            continue
        row = conn.execute(
            "SELECT study, trial, status, verdict FROM experiment WHERE id = ?", (eid,)
        ).fetchone()
        if row is not None:
            blocks.append(f"Experiment {eid}: study={row[0]} trial={row[1]} {row[2]}/{row[3]}")
            continue
        row = conn.execute("SELECT kind, status FROM job WHERE id = ?", (eid,)).fetchone()
        if row is not None:
            blocks.append(f"Job {eid}: {row[0]}/{row[1]}")
            continue
        raise ValueError(f"Schema: evidence id {eid!r} resolves to no ledger row")
    return "\n".join(blocks)


def _cite(prose: str, evidence: tuple[str, ...]) -> tuple[str, ...]:
    """Evidence IDs appearing verbatim in `prose` (substring semantics)."""
    return tuple(eid for eid in evidence if eid in prose)


def _dispatch(
    conn: sqlite3.Connection,
    *,
    action_type: str,
    provider: LLMProvider,
    guard: ProviderGuard,
    prompt: str,
    prompt_version: str,
    evidence: tuple[str, ...],
    model_version: str | None = None,
) -> Explanation:
    context = _resolve_evidence(conn, evidence) if evidence else ""
    if provider.hosted:
        guard.check_hosted(provider=provider.provider_name, model=provider.model_name)
    else:
        guard.check_local(provider=provider.provider_name)
    full_prompt = (
        f"{prompt}\nEvidence under discussion (cite IDs verbatim):\n{context}"
        if context
        else prompt
    )
    start = time.monotonic()
    response = provider.generate(
        LLMRequest(prompt=full_prompt, prompt_version=prompt_version)
    )
    latency = time.monotonic() - start
    cited = _cite(response.text, evidence)
    prose = response.text if cited else REFUSAL
    action_id = record_ai_action(
        conn,
        action_type=action_type,
        model_provider=response.provider,
        model_name=response.model,
        model_version=model_version,
        prompt_version=response.prompt_version,
        input_context_hash=_digest(full_prompt),
        output_hash=_digest(prose),
        source_artifacts=cited,
        token_cost=float(response.input_tokens + response.output_tokens),
        latency_s=latency,
    )
    return Explanation(prose=prose, cited_ids=cited, action_id=action_id)


def explain_failure(
    conn: sqlite3.Connection,
    *,
    classification: ClassifiedFailure,
    provider: LLMProvider,
    guard: ProviderGuard,
    model_version: str | None = None,
) -> Explanation:
    """Narrate one classified failure with verbatim-cited evidence or refuse."""
    prompt = (
        f"{SHIPPED_SYSTEM_PROMPT}\nClassified failure: "
        f"{classification.category} ({classification.trigger})."
    )
    return _dispatch(
        conn,
        action_type="explain_failure",
        provider=provider,
        guard=guard,
        prompt=prompt,
        prompt_version=_EXPLAIN_VERSION,
        evidence=classification.evidence,
        model_version=model_version,
    )


def narrate_optimization(
    conn: sqlite3.Connection,
    *,
    study_summary: str,
    experiment_ids: tuple[str, ...],
    provider: LLMProvider,
    guard: ProviderGuard,
    model_version: str | None = None,
) -> Explanation:
    """Narrate an optimization outcome grounded in experiment rows or refuse."""
    prompt = f"Summarize this optimization outcome. {study_summary}"
    return _dispatch(
        conn,
        action_type="narrate_optimization",
        provider=provider,
        guard=guard,
        prompt=prompt,
        prompt_version=_NARRATE_VERSION,
        evidence=experiment_ids,
        model_version=model_version,
    )


__all__ = [
    "REFUSAL",
    "SHIPPED_SYSTEM_PROMPT",
    "Explanation",
    "explain_failure",
    "narrate_optimization",
]
