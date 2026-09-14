"""Grounded tutor v0: failure-explanation-first chat (RFC-002, accepted 2026-09-14).

SEQUENCING LAW: the tutor may discuss exactly what the measurement ledger
covers and must refuse everything else. v0 answers failure questions about
the user's own runs through the proven `explain_job` pipeline, or refuses
via a code path — no model call is even attempted on refusal, so refusal
writes no `AIAction` row (null trail) and costs zero tokens (log-only
metering verdict: grounded answers meter through their explainer rows).
No synthesis whatsoever; proposals wait for the v1 gate.
"""

from __future__ import annotations

from typing import Final, Literal

Intent = Literal["failure_question", "other"]

CHAT_REFUSAL: Final = "I do not have a verified testbench for this topic."
CHAT_VERSION: Final = "tutor-chat-v0"
REFUSED_TRAIL: Final = "refused-no-evidence"

# RFC-002 §4 keyword set (deterministic, reviewable — human verdict 2026-09-14).
# Stems, not words: "converg" catches converge/converged/convergence.
_FAILURE_KEYWORDS: Final = (
    "job",
    "error",
    "sim",
    "run",
    "trial",
    "fail",
    "converg",
    "crash",
    "timestep",
)


def classify_intent(message: str) -> Intent:
    """Route one chat message: failure question or everything else.

    Pure function (no I/O, no model): a message mentioning a job, error,
    sim, run, or trial is a failure question; concepts, how-tos, and
    out-of-domain topologies fall through to refusal. ML classifiers stay
    out until an Eval they can fail exists (verdict 2026-09-14).
    """
    lowered = message.lower()
    for keyword in _FAILURE_KEYWORDS:
        if keyword in lowered:
            return "failure_question"
    return "other"


__all__ = [
    "Intent",
    "CHAT_REFUSAL",
    "CHAT_VERSION",
    "REFUSED_TRAIL",
    "classify_intent",
]
