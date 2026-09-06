"""Local job runner with worker-process isolation (Stage 2 Commit 2D).

One OS process per simulation job (`spawn` context, explicit for
cross-platform determinism) — never threads: libngspice keeps global C
state that threads cannot isolate (ADR-006). No IPC is needed: the worker
writes its verdict to the ledger over its own SQLite connection; the parent
reads committed rows. A crashed worker (nonzero exit, no verdict) is marked
`failed` by the parent on reap, so crashes can never corrupt the scheduler.

Statuses live in the `job` table (migration v5 vocabulary); this module owns
their transitions and nothing else writes them.
"""

from __future__ import annotations

import json
import multiprocessing as mp
import sqlite3
import traceback
from dataclasses import dataclass
from pathlib import Path

from analog_ic_design.store.schema import new_id, utcnow_iso


@dataclass(frozen=True)
class JobResult:
    """Settled outcome of one job (ledger row snapshot)."""

    job_id: str
    status: str
    result: str | None
    error: str | None


def _simulate_worker(db_path: str, job_id: str, netlist: str, seed: int, lib_path: str) -> None:
    """Worker entry (module-level: spawn-safe). Proofs in, verdicts out."""
    from analog_ic_design.sim.backend import NgspiceBackend

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        conn.execute(
            "UPDATE job SET status = 'running', updated_at = ? WHERE id = ?", (utcnow_iso(), job_id)
        )
        conn.commit()
        out = NgspiceBackend(lib_path=lib_path).simulate(netlist=netlist, seed=seed)
        raw = json.loads(out.raw_output.decode())
        payload = json.dumps(
            {"reproducibility_id": out.reproducibility_id, "vectors": raw["vectors"]}
        )
        conn.execute(
            "UPDATE job SET status = 'succeeded', result = ?, updated_at = ? WHERE id = ?",
            (payload, utcnow_iso(), job_id),
        )
    except Exception as exc:
        conn.execute(
            "UPDATE job SET status = 'failed', error = ?, updated_at = ? WHERE id = ?",
            (f"{type(exc).__name__}: {exc}\n{traceback.format_exc(limit=3)}", utcnow_iso(), job_id),
        )
    finally:
        conn.commit()
        conn.close()


class JobRunner:
    """Submits simulation jobs to isolated worker processes."""

    def __init__(self, *, db_path: str | Path, lib_path: str = "libngspice.so") -> None:
        self._db_path = str(db_path)
        self._lib_path = lib_path
        self._ctx = mp.get_context("spawn")
        self._conn = sqlite3.connect(self._db_path)
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._live: dict[str, mp.process.BaseProcess] = {}

    @property
    def db_path(self) -> str:
        """Ledger path (fixture setup opens its own connection to it)."""
        return self._db_path

    def submit_simulation(self, *, netlist: str, seed: int) -> str:
        """Record a pending job and start its worker process."""
        job_id = new_id()
        payload = json.dumps({"netlist": netlist, "seed": seed})
        self._conn.execute(
            "INSERT INTO job (id, kind, status, payload, result, error, created_at, updated_at)"
            " VALUES (?, 'simulate', 'pending', ?, NULL, NULL, ?, ?)",
            (job_id, payload, utcnow_iso(), utcnow_iso()),
        )
        self._conn.commit()
        proc = self._ctx.Process(
            target=_simulate_worker,
            args=(self._db_path, job_id, netlist, seed, self._lib_path),
            daemon=True,
        )
        proc.start()
        self._live[job_id] = proc
        return job_id

    def _read(self, job_id: str) -> JobResult:
        row = self._conn.execute(
            "SELECT status, result, error FROM job WHERE id = ?", (job_id,)
        ).fetchone()
        if row is None:
            raise KeyError(f"unknown job {job_id!r}")
        return JobResult(job_id=job_id, status=str(row[0]), result=row[1], error=row[2])

    def status(self, job_id: str) -> str:
        """Current ledger status (unknown ids raise `KeyError`)."""
        return self._read(job_id).status

    def wait(self, job_id: str, timeout: float | None = None) -> JobResult:
        """Block until the worker exits; `TimeoutError` on expiry (job kept).

        A worker that died without a verdict is marked `failed` here —
        crash containment, decided by the parent, never by the corpse.
        """
        proc = self._live.get(job_id)
        if proc is None:
            return self._read(job_id)
        proc.join(timeout)
        if proc.is_alive():
            raise TimeoutError(f"job {job_id!r} still running after {timeout}s")
        verdict = self._read(job_id)
        if verdict.status in ("pending", "running"):
            self._conn.execute(
                "UPDATE job SET status = 'failed', error = ?, updated_at = ? WHERE id = ?",
                (f"worker exited code {proc.exitcode} without a verdict", utcnow_iso(), job_id),
            )
            self._conn.commit()
            verdict = self._read(job_id)
        del self._live[job_id]
        return verdict

    def cancel(self, job_id: str) -> str:
        """Terminate a live worker and mark `cancelled`; settled jobs keep status."""
        proc = self._live.get(job_id)
        if proc is not None and proc.is_alive():
            proc.terminate()
            proc.join(10)
            if proc.is_alive():
                proc.kill()
                proc.join(10)
            self._conn.execute(
                "UPDATE job SET status = 'cancelled', updated_at = ? WHERE id = ?",
                (utcnow_iso(), job_id),
            )
            self._conn.commit()
            del self._live[job_id]
        return self._read(job_id).status

    def shutdown(self) -> None:
        """Terminate every live worker (best-effort) and close the ledger."""
        for job_id in list(self._live):
            try:
                self.cancel(job_id)
            except KeyError:
                continue
        self._conn.close()
