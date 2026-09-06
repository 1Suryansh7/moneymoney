"""Stage 3 Commit 3A tests: MetricContract matrix and Measurement schema.

Proves:
1. All canonical MetricContracts are frozen, unique, and strictly specified.
2. Invariants hold: legal analysis types, non-empty formulas, declared SI units.
3. Migration 6 (measurement table) enforces foreign keys to Job and cascades.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Generator
from dataclasses import FrozenInstanceError

import pytest

from analog_ic_design.metrics import (
    CANONICAL_METRICS,
    DC_GAIN,
    METRIC_BY_ID,
    MetricContract,
)
from analog_ic_design.store import connect, migrate, new_id

STAMP = "2026-09-06T00:00:00+00:00"
VALID_ANALYSES = {"dc", "ac", "tran", "op"}


@pytest.fixture()
def db() -> Generator[sqlite3.Connection, None, None]:
    conn = connect()
    migrate(conn)
    yield conn
    conn.close()


def test_metric_contracts_are_frozen() -> None:
    with pytest.raises(FrozenInstanceError):
        DC_GAIN.units = "dB"  # type: ignore[misc]


def test_canonical_matrix_completeness_and_uniqueness() -> None:
    assert len(CANONICAL_METRICS) == 8
    ids = [m.metric_id for m in CANONICAL_METRICS]
    assert len(ids) == len(set(ids)), "metric_id values must be globally unique"
    assert set(ids) == {
        "dc_gain",
        "ac_gain",
        "bandwidth",
        "phase_margin",
        "slew_rate",
        "power",
        "offset",
        "settling_time",
    }
    for m in CANONICAL_METRICS:
        assert METRIC_BY_ID[m.metric_id] is m


@pytest.mark.parametrize("contract", CANONICAL_METRICS)
def test_contract_invariants(contract: MetricContract) -> None:
    assert contract.required_analysis in VALID_ANALYSES
    assert contract.name != ""
    assert contract.definition != ""
    assert contract.required_testbench != ""
    assert contract.stimulus != ""
    assert len(contract.observed_nodes) > 0
    assert contract.formula_description != ""
    assert contract.sign_convention != ""
    assert contract.units in {"V/V", "Hz", "deg", "V/s", "W", "V", "s"}
    assert contract.reference_condition != ""
    assert contract.invalid_data_behavior != ""
    assert contract.comparison_policy != ""
    assert contract.golden_fixture_id != ""


def test_measurement_table_schema_and_foreign_key(db: sqlite3.Connection) -> None:
    job_id = new_id()
    db.execute(
        "INSERT INTO job VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (job_id, "sim", "succeeded", "{}", "{}", None, STAMP, STAMP),
    )
    meas_id = new_id()
    db.execute(
        "INSERT INTO measurement VALUES (?, ?, ?, ?, ?, ?)",
        (meas_id, job_id, DC_GAIN.metric_id, 12.5, DC_GAIN.units, STAMP),
    )
    db.commit()

    query = "SELECT metric_id, value, units FROM measurement WHERE id = ?"
    row = db.execute(query, (meas_id,)).fetchone()
    assert row is not None
    assert row[0] == "dc_gain"
    assert float(row[1]) == 12.5
    assert row[2] == "V/V"


def test_measurement_foreign_key_enforced(db: sqlite3.Connection) -> None:
    with pytest.raises(sqlite3.IntegrityError):
        db.execute(
            "INSERT INTO measurement VALUES (?, ?, ?, ?, ?, ?)",
            (new_id(), "non-existent-job", "dc_gain", 10.0, "V/V", STAMP),
        )


def test_measurement_cascades_on_job_deletion(db: sqlite3.Connection) -> None:
    job_id = new_id()
    db.execute(
        "INSERT INTO job VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (job_id, "sim", "succeeded", "{}", "{}", None, STAMP, STAMP),
    )
    meas_id = new_id()
    db.execute(
        "INSERT INTO measurement VALUES (?, ?, ?, ?, ?, ?)",
        (meas_id, job_id, "dc_gain", 15.0, "V/V", STAMP),
    )
    db.commit()

    count_q = "SELECT COUNT(*) FROM measurement WHERE id = ?"
    assert db.execute(count_q, (meas_id,)).fetchone()[0] == 1
    db.execute("DELETE FROM job WHERE id = ?", (job_id,))
    db.commit()
    assert db.execute(count_q, (meas_id,)).fetchone()[0] == 0
