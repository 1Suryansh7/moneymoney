"""Experiment Ledger writer/reader (Stage 4 Commit 4B).

Every evaluated trial — success or failure — lands exactly one
`experiment` row: study, trial index, params/metrics (SI JSON), verdict,
reproducibility id, seed, corner, and the trial's `job` linkage. Failed
trials are data: callers record them with status `'failed'` and a verdict
naming the failure class instead of dropping them.
"""

from __future__ import annotations

import json
import sqlite3

from analog_ic_design.optimize.optimizer import TrialResult
from analog_ic_design.store.schema import new_id, utcnow_iso


def record_experiment(
    conn: sqlite3.Connection, result: TrialResult, *, created_at: str | None = None
) -> str:
    """Persist one trial outcome; returns the experiment row id."""
    eid = new_id()
    conn.execute(
        "INSERT INTO experiment VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            eid,
            result.study,
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


def list_experiments(conn: sqlite3.Connection, study: str) -> list[TrialResult]:
    """All recorded trials of `study`, ordered by trial index then row id."""
    rows = conn.execute(
        "SELECT id, study, trial, kind, status, corner, parameters, metrics,"
        " verdict, reproducibility_id, seed, job_id FROM experiment"
        " WHERE study = ? ORDER BY trial, id",
        (study,),
    ).fetchall()
    found: list[TrialResult] = []
    for row in rows:
        found.append(
            TrialResult(
                study=str(row[1]),
                trial=int(row[2]),
                kind=str(row[3]),
                status=str(row[4]),
                corner=str(row[5]),
                parameters=dict(json.loads(str(row[6]))),
                metrics=dict(json.loads(str(row[7]))),
                verdict=str(row[8]),
                reproducibility_id=str(row[9]),
                seed=int(row[10]),
                job_id=None if row[11] is None else str(row[11]),
            )
        )
    return found
