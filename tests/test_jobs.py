"""Stage 2 Commit 2D tests: worker-process job runner.

Base-safe lifecycle tests run everywhere (failure paths need no library);
happy-path and cancel/timeout tests need libngspice (explicit skip naming
the covering CI eda gate). Timing races are designed out: assertions rely
on spawn latency and settled states, never on sleeps.
"""

from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

import pytest

from analog_ic_design.sim.jobs import JobResult, JobRunner
from analog_ic_design.sim.ngspice import libngspice_available

NEEDS_LIB = pytest.mark.skipif(
    not libngspice_available(),
    reason="libngspice absent (base image); covered by CI eda job",
)

RC = "\n".join(
    [
        "* rc hello",
        "V1 in 0 DC 0 PULSE(0 1.8 1n 1n 1n 10n 20n)",
        "R1 in out 1k",
        "C1 out 0 1p",
        ".tran 0.1n 30n",
        ".end",
        "",
    ]
)


@pytest.fixture()
def runner(tmp_path: Path) -> Generator[JobRunner, None, None]:
    jobs = JobRunner(db_path=_db(tmp_path / "jobs.sqlite"))
    yield jobs
    jobs.shutdown()


def _db(path: Path) -> str:
    from analog_ic_design.store import connect, migrate

    conn = connect(path)
    migrate(conn)
    conn.close()
    return str(path)


def test_unknown_job_raises_key_error(runner: JobRunner) -> None:
    with pytest.raises(KeyError):
        runner.status("no-such-job")
    with pytest.raises(KeyError):
        runner.wait("no-such-job")


def test_failed_job_recorded_with_error(tmp_path: Path) -> None:
    jobs = JobRunner(db_path=_db(tmp_path / "j.sqlite"), lib_path="definitely-not-a-library.so.0")
    try:
        jid = jobs.submit_simulation(netlist=RC, seed=1)
        assert jobs.status(jid) in ("pending", "running")
        result = jobs.wait(jid, timeout=120)
    finally:
        jobs.shutdown()
    assert isinstance(result, JobResult)
    assert result.status == "failed"
    assert result.error is not None and "cannot load" in result.error
    assert result.result is None


@NEEDS_LIB
def test_successful_job_result(runner: JobRunner) -> None:
    jid = runner.submit_simulation(netlist=RC, seed=7)
    result = runner.wait(jid, timeout=120)
    assert result.status == "succeeded"
    assert result.error is None
    assert result.result is not None and "reproducibility_id" in result.result
    assert runner.wait(jid, timeout=1) == result


@NEEDS_LIB
def test_timeout_then_cancel(runner: JobRunner) -> None:
    jid = runner.submit_simulation(netlist=RC, seed=7)
    with pytest.raises(TimeoutError):
        runner.wait(jid, timeout=0.0)
    assert runner.cancel(jid) == "cancelled"
    assert runner.status(jid) == "cancelled"
    jid2 = runner.submit_simulation(netlist=RC, seed=8)
    assert runner.wait(jid2, timeout=120).status == "succeeded"


@NEEDS_LIB
def test_cancel_settles_immediately(runner: JobRunner) -> None:
    # Spawn + interpreter import take ~100ms+; cancel lands in ~1ms, so the
    # worker cannot have settled. Strict equality, no timing tolerance.
    jid = runner.submit_simulation(netlist=RC, seed=9)
    assert runner.cancel(jid) == "cancelled"
