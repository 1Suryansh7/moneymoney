"""Stage 4 Commit 4B tests: optimizer interface, space, ledger.

Pure-logic tests with a hand-rolled deterministic fake (no Optuna, no
simulator): run on base image with zero skips.
"""

from __future__ import annotations

import random
import sqlite3
from collections.abc import Generator

import pytest

from analog_ic_design.optimize import (
    Optimizer,
    OptunaOptimizer,
    SearchSpace,
    TrialResult,
    list_experiments,
    record_experiment,
)
from analog_ic_design.store import connect, migrate, new_id

STAMP = "2026-09-05T00:00:00+00:00"


class _FakeOptimizer(Optimizer):
    """Deterministic stand-in: seeded uniform suggestions, recorded observes."""

    def __init__(self, space: SearchSpace, *, seed: int) -> None:
        super().__init__(space, seed=seed)
        self._rng = random.Random(seed)
        self.observed: list[tuple[dict[str, float], float]] = []

    def suggest(self) -> dict[str, float]:
        return {
            name: self._rng.uniform(float(low), float(high))
            for name, (low, high) in self.space.bounds.items()
        }

    def observe(self, params: dict[str, float], value: float) -> None:
        self.observed.append((dict(params), float(value)))


@pytest.fixture()
def db() -> Generator[sqlite3.Connection, None, None]:
    conn = connect()
    migrate(conn)
    yield conn
    conn.close()


def test_space_rejects_degenerate() -> None:
    with pytest.raises(ValueError, match="no parameters"):
        SearchSpace({})
    with pytest.raises(ValueError, match="empty"):
        SearchSpace({"w": (2e-06, 1e-06)})
    with pytest.raises(ValueError, match="not finite"):
        SearchSpace({"w": (1e-06, float("inf"))})
    assert SearchSpace({"w": (1e-06, 2e-06)}).in_bounds({"w": 1.5e-06})
    assert not SearchSpace({"w": (1e-06, 2e-06)}).in_bounds({"w": 3e-06})
    assert not SearchSpace({"w": (1e-06, 2e-06)}).in_bounds({})


def test_optimizer_rejects_bad_seed() -> None:
    space = SearchSpace({"w": (1e-06, 2e-06)})
    with pytest.raises(ValueError, match="seed must be an int"):
        _FakeOptimizer(space, seed=True)
    assert _FakeOptimizer(space, seed=3).seed == 3


def test_abstract_optimizer_cannot_instantiate() -> None:
    with pytest.raises(TypeError):
        Optimizer(SearchSpace({"w": (1e-06, 2e-06)}), seed=0)  # type: ignore[abstract]


def test_suggest_observe_determinism() -> None:
    space = SearchSpace({"w_n": (0.5e-06, 3e-06), "w_p": (1e-06, 6e-06)})
    first, second = _FakeOptimizer(space, seed=11), _FakeOptimizer(space, seed=11)
    for _ in range(5):
        params = first.suggest()
        assert first.space.in_bounds(params)
        first.observe(params, 1.0)
        twin = second.suggest()
        assert twin == params
        second.observe(twin, 1.0)
    assert [p for p, _ in first.observed] == [p for p, _ in second.observed]


def test_ledger_round_trip_records_failures_too(db: sqlite3.Connection) -> None:
    jid = new_id()
    db.execute(
        "INSERT INTO job VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (jid, "trial", "succeeded", "{}", "{}", None, STAMP, STAMP),
    )
    db.commit()
    good = TrialResult(
        study="s",
        trial=0,
        kind="trial",
        status="succeeded",
        corner="nominal",
        parameters={"w_n": 1e-06},
        metrics={"bandwidth": 2e7},
        verdict="pass",
        reproducibility_id="r0",
        seed=7,
        job_id=jid,
    )
    bad = TrialResult(
        study="s",
        trial=1,
        kind="trial",
        status="failed",
        corner="nominal",
        parameters={"w_n": 0.5e-06},
        metrics={},
        verdict="spice_convergence",
        reproducibility_id="r1",
        seed=7,
        job_id=None,
    )
    record_experiment(db, good, created_at=STAMP)
    record_experiment(db, bad, created_at=STAMP)
    rows = list_experiments(db, "s")
    assert [r.trial for r in rows] == [0, 1]
    assert rows[0].parameters == {"w_n": 1e-06}
    assert rows[0].metrics == {"bandwidth": 2e7}
    assert rows[0].job_id == jid
    assert (rows[1].status, rows[1].verdict, rows[1].job_id) == (
        "failed",
        "spice_convergence",
        None,
    )
    assert list_experiments(db, "other") == []


def _optuna_space() -> SearchSpace:
    return SearchSpace({"w_n": (0.5e-06, 3e-06), "w_p": (1e-06, 6e-06)})


def test_optuna_rejects_bad_direction() -> None:
    with pytest.raises(ValueError, match="direction"):
        OptunaOptimizer(_optuna_space(), seed=0, direction="sideways")


def test_optuna_suggest_observe_determinism() -> None:
    first = OptunaOptimizer(_optuna_space(), seed=21, study_name="a")
    second = OptunaOptimizer(_optuna_space(), seed=21, study_name="b")
    assert first.study_name == "a"
    for _ in range(4):
        params = first.suggest()
        assert first.space.in_bounds(params)
        value = -sum((v - 1e-06) ** 2 for v in params.values())
        first.observe(params, value)
        twin = second.suggest()
        assert twin == params
        second.observe(twin, value)


def test_optuna_observe_guards_pairing() -> None:
    opt = OptunaOptimizer(_optuna_space(), seed=21)
    with pytest.raises(ValueError, match="no open suggestion"):
        opt.observe({"w_n": 1e-06, "w_p": 2e-06}, 1.0)
    params = opt.suggest()
    with pytest.raises(ValueError, match="do not match"):
        opt.observe({"w_n": 9e-06, "w_p": 2e-06}, 1.0)
    with pytest.raises(ValueError, match="not finite"):
        opt.observe(params, float("inf"))
    opt.observe(params, 1.0)
