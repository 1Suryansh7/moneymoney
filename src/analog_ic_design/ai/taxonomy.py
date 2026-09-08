"""Deterministic failure classification (Stage 5 Commit 5A).

CLASSIFY FIRST, EXPLAIN SECOND: this module maps observed failure evidence
to exactly one of the 12 taxonomy categories using fixed rules — never a
model call, never a guess. Anything without taxonomy evidence fails closed
with `ValueError` instead of inventing a category.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Final

#: Canonical 12-category failure taxonomy, in AGENTS.md section 6 order.
TAXONOMY: Final[tuple[str, ...]] = (
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

#: SimError message prefixes emitted by construction (ngspice.py, validator).
_PREFIXES: Final[tuple[tuple[str, str], ...]] = (
    ("Schema:", "schema"),
    ("Netlist:", "netlist"),
    ("SPICE convergence:", "spice_convergence"),
)


@dataclass(frozen=True)
class ClassifiedFailure:
    """One classified failure: taxonomy category, trigger, evidence IDs."""

    category: str
    trigger: str
    evidence: tuple[str, ...] = field(default_factory=tuple)


def classify_failure(
    *,
    error_category: str | None = None,
    message: str | None = None,
    spec_failed: bool = False,
    evidence: tuple[str, ...] = (),
) -> ClassifiedFailure:
    """Map observed evidence to one taxonomy category (deterministic).

    Precedence: explicit caller-asserted `error_category` (validated),
    then taxonomy-prefixed `message`, then `spec_failed` (constraint).
    Raises `ValueError` when nothing carries taxonomy evidence.
    """
    if error_category is not None:
        if error_category not in TAXONOMY:
            raise ValueError(f"Schema: unknown taxonomy category {error_category!r}")
        return ClassifiedFailure(
            category=error_category,
            trigger=f"caller-asserted category {error_category!r}",
            evidence=tuple(evidence),
        )
    if message:
        for prefix, category in _PREFIXES:
            if message.startswith(prefix):
                return ClassifiedFailure(
                    category=category,
                    trigger=f"taxonomy-prefixed message ({prefix.rstrip(':')})",
                    evidence=tuple(evidence),
                )
    if spec_failed:
        return ClassifiedFailure(
            category="constraint",
            trigger="specification evaluation reported failure",
            evidence=tuple(evidence),
        )
    raise ValueError("Schema: cannot classify failure without taxonomy evidence")
