"""Stage 2 Commit 2C tests: libngspice backend contract.

Environment split (documented, not green-washing): tests touching the shared
library skip on images without it (base) with a reason naming the covering
gate; the CI `eda` job runs this file with zero skips. Error-path and
identity tests run everywhere.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from analog_ic_design.interfaces.simulator import Simulator
from analog_ic_design.sim.backend import NgspiceBackend, _identity
from analog_ic_design.sim.ngspice import (
    SimError,
    _fail,
    _has_analysis,
    libngspice_available,
    run_deck,
)

NEEDS_LIB = pytest.mark.skipif(
    not libngspice_available(),
    reason="libngspice absent (base image); covered by CI eda job",
)

RC_DECK = [
    "* rc hello",
    "V1 in 0 DC 0 PULSE(0 1.8 1n 1n 1n 10n 20n)",
    "R1 in out 1k",
    "C1 out 0 1p",
    ".tran 0.1n 30n",
    ".end",
]


def test_backend_implements_simulator() -> None:
    assert isinstance(NgspiceBackend(), Simulator)


def test_missing_library_fails_closed() -> None:
    backend = NgspiceBackend(lib_path="definitely-not-a-library.so.0")
    with pytest.raises(SimError, match="cannot load"):
        backend.simulate(netlist="* x\n.end\n", seed=0)


def test_empty_deck_and_bad_seed_rejected() -> None:
    backend = NgspiceBackend()
    with pytest.raises(SimError):
        backend.simulate(netlist="   \n", seed=0)
    with pytest.raises(SimError):
        backend.simulate(netlist="* x\n.end\n", seed=True)


def test_identity_stable_and_sensitive() -> None:
    assert _identity("a", 1) == _identity("a", 1)
    assert len(_identity("a", 1)) == 64
    assert _identity("a", 1) != _identity("a", 2)
    assert _identity("a", 1) != _identity("b", 1)


@NEEDS_LIB
def test_rc_transient_through_lib() -> None:
    # NOTE: the shared library names node vectors bare (`out`), unlike the
    # CLI print convention (`v(out)`). Observed from a real run, asserted here.
    raw = run_deck(lines=RC_DECK)
    assert "time" in raw.vectors and "out" in raw.vectors
    times, values = raw.vectors["time"], raw.vectors["out"]
    assert len(times) > 10 and len(times) == len(values)
    assert times[0] == 0.0
    assert all(b > a for a, b in zip(times, times[1:], strict=False))
    # Pulse is periodic (20 ns): at t=30 ns the cap recharged ~9 time
    # constants toward the 1.8 V rail. Solver tolerance, not bitwise
    # (bitwise determinism has its own test below).
    assert abs(values[-1] - 1.8) < 1e-3


@NEEDS_LIB
def test_repeat_runs_are_bitwise_deterministic() -> None:
    first = run_deck(lines=RC_DECK).vectors
    second = run_deck(lines=RC_DECK).vectors
    assert first == second


@NEEDS_LIB
def test_backend_simulate_end_to_end() -> None:
    result = NgspiceBackend().simulate(netlist="\n".join(RC_DECK) + "\n", seed=7)
    assert result.reproducibility_id == _identity("\n".join(RC_DECK) + "\n", 7)
    assert len(result.raw_output) > 0


@NEEDS_LIB
def test_simulator_version_names_ngspice() -> None:
    assert "ngspice" in NgspiceBackend().simulator_version().lower()


def test_fail_attaches_log_tail() -> None:
    err = _fail("SPICE convergence: boom", ["ab", "cd"])
    assert "SPICE convergence: boom" in str(err)
    assert "ngspice log (tail)" in str(err)
    assert "abcd" in str(err)
    assert "(empty log)" in str(_fail("Schema: x", []))


@NEEDS_LIB
def test_worker_error_carries_ngspice_log(tmp_path: Path) -> None:
    # Error-path C calls corrupt libngspice process-global state (observed
    # 2026-09-06: full-suite segfault in the test after an in-process
    # Circ/run failure), so failing decks execute ONLY in workers here —
    # crash containment is the worker architecture's job (Stage 2D).
    from analog_ic_design.sim.jobs import JobRunner
    from analog_ic_design.store import connect, migrate

    db = str(tmp_path / "simerr.sqlite")
    conn = connect(db)
    migrate(conn)
    conn.close()
    jobs = JobRunner(db_path=db)
    try:
        deck = "\n".join(
            [
                "* bad include",
                ".include /nonexistent/x.spice",
                ".tran 0.1n 30n",
                ".end",
                ""
            ]
        )
        result = jobs.wait(jobs.submit_simulation(netlist=deck, seed=0), timeout=120)
    finally:
        jobs.shutdown()
    assert result.status == "failed", result.status
    assert result.error is not None
    assert "ngspice log (tail)" in result.error


def test_deck_without_analysis_rejected_before_simulator() -> None:
    # Pure-Python guard (no library needed): a no-analysis `run` corrupts
    # libngspice process-global state, so it must never reach the C API.
    assert _has_analysis(["* c", "V1 a 0 DC 1", ".tran 0.1n 30n", ".end"])
    assert _has_analysis([".control", "run", ".endc", ".op", ".end"])
    assert not _has_analysis(["* no analysis", "V1 a 0 DC 1", "R1 a 0 1k", ".end"])
    assert not _has_analysis([".control", "run", ".endc", ".end"])
    assert not _has_analysis([])


@NEEDS_LIB
def test_run_deck_without_analysis_raises_netlist() -> None:
    with pytest.raises(SimError, match="no analysis"):
        run_deck(lines=["* no analysis", "V1 a 0 DC 1", "R1 a 0 1k", ".end"])
