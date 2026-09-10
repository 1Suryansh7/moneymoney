"""Stage 7B-6 tests: PlotPane-ready waveform vectors per job.

GET /jobs/{id}/waveforms serves transient SI samples (unit + y) or AC
magnitude_db/phase_deg, parsed behind the EngineV01 boundary — the
frontend never sees raw SPICE vectors. Base tests seed ledger rows
directly (tests may touch storage; product code may not) with exact
hand-computed expectations; the live EDA test runs a real RC sim and
asserts the charging shape through the route.
"""

from __future__ import annotations

import json
import socket
import sqlite3
import threading
import time
from collections.abc import Generator
from pathlib import Path
from typing import Any

import httpx2
import pytest
import uvicorn

from analog_ic_design.api.server import create_app
from analog_ic_design.sim.ngspice import libngspice_available

NEEDS_LIB = pytest.mark.skipif(
    not libngspice_available(),
    reason="libngspice absent (base image); covered by CI eda job",
)

RC_DECK = "\n".join(
    [
        "* rc probe",
        "V1 in 0 DC 0 PULSE(0 1.8 1n 1n 1n 10n 20n)",
        "R1 in out 1k",
        "C1 out 0 1p",
        ".tran 0.1n 30n",
        ".end",
        "",
    ]
)
STAMP = "2026-09-05T00:00:00+00:00"

TRAN_PAYLOAD = {
    "reproducibility_id": "ab" * 32,
    "vectors": {
        "time": [0.0, 1.0e-09, 2.0e-09],
        "in": [0.0, 1.8, 1.8],
        "out": [1.8, 1.8, 0.0],
    },
    "complex_vectors": {},
}

AC_PAYLOAD = {
    "reproducibility_id": "cd" * 32,
    "vectors": {"frequency": [10.0, 100.0]},
    "complex_vectors": {"out": [[1.0, 0.0], [0.0, 1.0]]},
}


def _free_port() -> int:
    """Unbound localhost port (tiny bind-then-release race accepted)."""
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@pytest.fixture()
def server(tmp_path: Path) -> Generator[tuple[httpx2.Client, str], None, None]:
    db = str(tmp_path / "waveforms.sqlite")
    app = create_app(db_path=db)
    port = _free_port()
    server = uvicorn.Server(
        uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error")
    )
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{port}"
    deadline = time.time() + 30.0
    while True:
        try:
            if httpx2.get(base + "/health", timeout=2.0).status_code == 200:
                break
        except Exception:
            pass
        if time.time() > deadline:
            raise TimeoutError("API test server never became ready")
        time.sleep(0.1)
    client = httpx2.Client(base_url=base, timeout=60.0)
    yield client, db
    client.close()
    server.should_exit = True
    thread.join(timeout=15.0)


def _seed_job(db: str, job_id: str, status: str, payload: Any,
              error: str | None) -> str:
    conn = sqlite3.connect(db)
    try:
        conn.execute(
            "INSERT INTO job (id, kind, status, payload, result, error,"
            " created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                job_id,
                "simulate",
                status,
                "{}",
                json.dumps(payload) if payload is not None else None,
                error,
                STAMP,
                STAMP,
            ),
        )
        conn.commit()
    finally:
        conn.close()
    return job_id


def test_unknown_job_waveforms_404(server: tuple[httpx2.Client, str]) -> None:
    client, _ = server
    resp = client.get("/jobs/nope/waveforms")
    assert resp.status_code == 404
    assert "unknown job" in resp.json()["detail"]


def test_failed_job_waveforms_500_preserves_taxonomy(
    server: tuple[httpx2.Client, str],
) -> None:
    client, db = server
    jid = _seed_job(db, "job-fail-1", "failed", None, "SimError: SPICE convergence: boom")
    resp = client.get(f"/jobs/{jid}/waveforms")
    assert resp.status_code == 500
    assert "SPICE convergence" in resp.json()["detail"]


def test_seeded_transient_waveforms_exact(
    server: tuple[httpx2.Client, str],
) -> None:
    client, db = server
    jid = _seed_job(db, "job-tran-1", "succeeded", TRAN_PAYLOAD, None)
    body = client.get(f"/jobs/{jid}/waveforms").json()
    assert body["job_id"] == jid
    assert body["analysis"] == "tran"
    assert (body["x_name"], body["x_unit"]) == ("time", "s")
    assert body["x"] == [0.0, 1.0e-09, 2.0e-09]
    by_name = {t["name"]: t for t in body["traces"]}
    assert set(by_name) == {"in", "out"}
    assert by_name["in"]["unit"] == "V"
    assert by_name["in"]["y"] == [0.0, 1.8, 1.8]
    assert by_name["out"]["y"] == [1.8, 1.8, 0.0]
    assert by_name["in"]["magnitude_db"] is None


def test_seeded_ac_waveforms_exact(server: tuple[httpx2.Client, str]) -> None:
    client, db = server
    jid = _seed_job(db, "job-ac-1", "succeeded", AC_PAYLOAD, None)
    body = client.get(f"/jobs/{jid}/waveforms").json()
    assert body["analysis"] == "ac"
    assert (body["x_name"], body["x_unit"]) == ("frequency", "Hz")
    assert body["x"] == [10.0, 100.0]
    assert len(body["traces"]) == 1
    trace = body["traces"][0]
    assert trace["name"] == "out"
    assert trace["magnitude_db"] == pytest.approx([0.0, 0.0])
    assert trace["phase_deg"] == pytest.approx([0.0, 90.0])
    assert trace["y"] is None


@NEEDS_LIB
def test_live_rc_charging_shape_through_route(
    server: tuple[httpx2.Client, str],
) -> None:
    client, _ = server
    repro = client.post("/simulate", json={"netlist": RC_DECK, "seed": 7}).json()[
        "reproducibility_id"
    ]
    assert len(repro) == 64
    jid = client.get("/jobs").json()[0]["job_id"]
    body = client.get(f"/jobs/{jid}/waveforms").json()
    assert body["analysis"] == "tran"
    out = next(t for t in body["traces"] if t["name"] == "out")
    assert out["unit"] == "V"
    assert all(isinstance(v, float) for v in out["y"])
    assert out["y"][-1] > out["y"][0]
    assert body["x"][-1] > body["x"][0]
