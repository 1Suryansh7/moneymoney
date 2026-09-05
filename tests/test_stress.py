"""Stage 2 Commit 2G: concurrency & isolation stress suite (mandatory harness).

Simultaneous 1-, 2-, and 4-job workloads across worker processes with
deliberately DIVERSE decks (different tau, different output sizes) and seeds,
asserting: results land under the right Job id, no parameter/callback state
leaks across runs, cancel/crash of one job never corrupts another, and
repeats are deterministic. Whole module needs libngspice (explicit skip
naming the covering CI eda gate).
"""

from __future__ import annotations

import json
import os
import signal
from collections.abc import Generator
from pathlib import Path

import pytest

from analog_ic_design.sim.jobs import JobResult, JobRunner
from analog_ic_design.sim.ngspice import libngspice_available, run_deck

pytestmark = pytest.mark.skipif(
    not libngspice_available(),
    reason="libngspice absent (base image); covered by CI eda job",
)


def _deck(resistance: str = "1k", tstop: str = "30n") -> str:
    return "\n".join(
        [
            "* rc stress",
            "V1 in 0 DC 0 PULSE(0 1.8 1n 1n 1n 10n 20n)",
            f"R1 in out {resistance}",
            "C1 out 0 1p",
            f".tran 0.1n {tstop}",
            ".end",
            "",
        ]
    )


@pytest.fixture()
def runner(tmp_path: Path) -> Generator[JobRunner, None, None]:
    from analog_ic_design.store import connect, migrate

    db = str(tmp_path / "stress.sqlite")
    conn = connect(db)
    migrate(conn)
    conn.close()
    jobs = JobRunner(db_path=db)
    yield jobs
    jobs.shutdown()


def _vectors(result: JobResult) -> dict[str, list[float]]:
    assert result.status == "succeeded", result.error
    assert result.result is not None
    return json.loads(result.result)["vectors"]  # type: ignore[no-any-return]


def test_solo_run_matches_direct_run(runner: JobRunner) -> None:
    deck = _deck()
    jid = runner.submit_simulation(netlist=deck, seed=3)
    result = runner.wait(jid, timeout=120)
    assert _vectors(result) == run_deck(lines=deck.splitlines()).vectors


def test_four_simultaneous_diverse_jobs_attributed(runner: JobRunner) -> None:
    decks = [_deck("1k", "30n"), _deck("2k", "30n"), _deck("1k", "60n"), _deck("1k", "30n")]
    seeds = [11, 22, 33, 44]
    ids = [runner.submit_simulation(netlist=d, seed=s) for d, s in zip(decks, seeds, strict=True)]
    got = [runner.wait(jid, timeout=180) for jid in ids]
    assert [r.status for r in got] == ["succeeded"] * 4
    vecs = [_vectors(r) for r in got]
    assert vecs[0] == vecs[3]
    assert vecs[0] != vecs[1]
    assert len(vecs[2]["time"]) != len(vecs[0]["time"])
    rids = [json.loads(r.result or "{}")["reproducibility_id"] for r in got]
    assert len(set(rids)) == 4


def test_repeated_concurrent_runs_deterministic(runner: JobRunner) -> None:
    deck = _deck()
    first = [runner.submit_simulation(netlist=deck, seed=5) for _ in range(2)]
    second = [runner.submit_simulation(netlist=deck, seed=5) for _ in range(2)]
    wave1 = [_vectors(runner.wait(j, timeout=120)) for j in first]
    wave2 = [_vectors(runner.wait(j, timeout=120)) for j in second]
    assert wave1 == wave2


def test_cancel_during_flood_spares_siblings(runner: JobRunner) -> None:
    ids = [runner.submit_simulation(netlist=_deck(), seed=i) for i in range(4)]
    assert runner.cancel(ids[0]) == "cancelled"
    assert [runner.wait(j, timeout=180).status for j in ids[1:]] == ["succeeded"] * 3
    assert runner.status(ids[0]) == "cancelled"


def test_sigkill_crash_contained(runner: JobRunner) -> None:
    # White-box by intent: reach the worker handle to SIGKILL it, proving a
    # violent death is contained and the scheduler survives.
    doomed = runner.submit_simulation(netlist=_deck(), seed=1)
    proc = runner._live[doomed]
    assert proc.pid is not None
    os.kill(proc.pid, signal.SIGKILL)
    verdict = runner.wait(doomed, timeout=60)
    assert verdict.status == "failed" and "without a verdict" in (verdict.error or "")
    healthy = runner.submit_simulation(netlist=_deck(), seed=2)
    assert runner.wait(healthy, timeout=120).status == "succeeded"
    assert not runner._live
