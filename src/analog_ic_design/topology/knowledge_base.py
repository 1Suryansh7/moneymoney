"""Design Knowledge Base for Topology Intelligence (Stage 6 Commit 6B).

Links topology templates to historical trials from the Experiment Ledger
(`experiment` and `measurement` tables). Aggregates empirical capability
boundaries, success/failure rates, and robust yield history per template.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass

from analog_ic_design.optimize.optimizer import TrialResult
from analog_ic_design.store.schema import new_id, utcnow_iso
from analog_ic_design.topology.templates import REGISTERED_TEMPLATES


@dataclass(frozen=True)
class TemplateCapabilities:
    """Empirical capability boundaries extracted from historical experiments."""

    template_id: str
    total_trials: int
    successful_trials: int
    failed_trials: int
    yield_rate: float
    min_gain: float | None
    max_gain: float | None
    min_bandwidth: float | None
    max_bandwidth: float | None
    min_power: float | None
    max_power: float | None


def template_study_name(template_id: str) -> str:
    """Canonical study prefix for a given template."""
    return f"{template_id}_study"


def record_template_experiment(
    conn: sqlite3.Connection,
    template_id: str,
    result: TrialResult,
    *,
    created_at: str | None = None,
) -> str:
    """Record an experiment trial explicitly linked to a topology template."""
    if template_id not in REGISTERED_TEMPLATES:
        raise ValueError(f"Schema: unknown template_id {template_id!r}")

    study = (
        result.study if result.study.startswith(template_id)
        else f"{template_id}_{result.study}"
    )
    eid = new_id()
    conn.execute(
        "INSERT INTO experiment VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            eid,
            study,
            result.trial,
            result.kind,
            result.status,
            result.corner,
            json.dumps(result.parameters, sort_keys=True),
            json.dumps(result.metrics, sort_keys=True),
            result.verdict,
            result.reproducibility_id,
            result.seed,
            result.job_id,
            created_at if created_at is not None else utcnow_iso(),
        ),
    )
    conn.commit()
    return eid


def get_template_experiments(
    conn: sqlite3.Connection,
    template_id: str,
) -> list[dict[str, object]]:
    """Query all historical experiment trials for a given template."""
    pattern = f"{template_id}%"
    rows = conn.execute(
        "SELECT id, study, trial, kind, status, corner, parameters, metrics, verdict, seed"
        " FROM experiment WHERE study LIKE ? ORDER BY trial, id",
        (pattern,),
    ).fetchall()

    records: list[dict[str, object]] = []
    for r in rows:
        records.append({
            "id": str(r[0]),
            "study": str(r[1]),
            "trial": int(r[2]),
            "kind": str(r[3]),
            "status": str(r[4]),
            "corner": str(r[5]),
            "parameters": dict(json.loads(str(r[6]))),
            "metrics": dict(json.loads(str(r[7]))),
            "verdict": str(r[8]),
            "seed": int(r[9]),
        })
    return records


def query_template_capabilities(
    conn: sqlite3.Connection,
    template_id: str,
) -> TemplateCapabilities:
    """Compute empirical performance bounds and historical yield for a template."""
    if template_id not in REGISTERED_TEMPLATES:
        raise ValueError(f"Schema: unknown template_id {template_id!r}")

    experiments = get_template_experiments(conn, template_id)
    total = len(experiments)
    if total == 0:
        return TemplateCapabilities(
            template_id=template_id,
            total_trials=0,
            successful_trials=0,
            failed_trials=0,
            yield_rate=0.0,
            min_gain=None,
            max_gain=None,
            min_bandwidth=None,
            max_bandwidth=None,
            min_power=None,
            max_power=None,
        )

    successes = [e for e in experiments if e["status"] == "succeeded"]
    fails = [e for e in experiments if e["status"] == "failed"]
    yield_rate = len(successes) / float(total)

    gains: list[float] = []
    bws: list[float] = []
    powers: list[float] = []

    for s in successes:
        metrics = s["metrics"]
        if isinstance(metrics, dict):
            for k, val in metrics.items():
                if not isinstance(val, (int, float)):
                    continue
                k_lower = k.lower()
                if "gain" in k_lower:
                    gains.append(float(val))
                elif "bandwidth" in k_lower or "ugb" in k_lower:
                    bws.append(float(val))
                elif "power" in k_lower:
                    powers.append(float(val))

    return TemplateCapabilities(
        template_id=template_id,
        total_trials=total,
        successful_trials=len(successes),
        failed_trials=len(fails),
        yield_rate=yield_rate,
        min_gain=min(gains) if gains else None,
        max_gain=max(gains) if gains else None,
        min_bandwidth=min(bws) if bws else None,
        max_bandwidth=max(bws) if bws else None,
        min_power=min(powers) if powers else None,
        max_power=max(powers) if powers else None,
    )
