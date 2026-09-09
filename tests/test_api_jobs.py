"""Stage 7B-4 tests: job observability routes for Run Center wiring.

GET /jobs (summaries, no payloads) and GET /jobs/{id} (full ledger row).
Base suite seeds ledger rows directly (tests may touch storage; product
code may not). The live EDA test runs a real RC sim through POST
/simulate, then reads it back through both routes.
"""

from __future__ import annotations

import json
import socket
import sqlite3
import threading
import time
from collections.abc import Generator
from pathlib import Path

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


def _free_port() -> int:
    """Unbound localhost port (tiny bind-then-release race accepted)."""
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@pytest.fixture()
def server(tmp_path: Path) -> Generator[tuple[httpx2.Client, str], None, None]:
    db = str(tmp_path / "jobs.sqlite")
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


def _seed_job(db: str) -> str:
    conn = sqlite3.connect(db)
    try:
        conn.execute(
            "INSERT INTO job (id, kind, status, payload, result, error,"
            " created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "job-seed-1",
                "simulate",
                "succeeded",
                "{}",
                json.dumps({"reproducibility_id": "ab" * 32, "vectors": {}}),
                None,
                STAMP,
                STAMP,
            ),
        )
        conn.commit()
    finally:
        conn.close()
    return "job-seed-1"


def test_jobs_empty_initially(server: tuple[httpx2.Client, str]) -> None:
    client, _ = server
    assert client.get("/jobs").json() == []


def test_job_detail_roundtrip_seeded_row(server: tuple[httpx2.Client, str]) -> None:
    client, db = server
    jid = _seed_job(db)
    detail = client.get(f"/jobs/{jid}").json()
    assert detail["job_id"] == jid
    assert detail["status"] == "succeeded"
    assert json.loads(str(detail["result"]))["reproducibility_id"] == "ab" * 32
    assert detail["error"] is None
    listed = client.get("/jobs").json()
    assert [row["job_id"] for row in listed] == [jid]
    assert "result" not in listed[0]


def test_unknown_job_404(server: tuple[httpx2.Client, str]) -> None:
    client, _ = server
    resp = client.get("/jobs/nope")
    assert resp.status_code == 404
    assert "unknown job" in resp.json()["detail"]


@NEEDS_LIB
def test_live_sim_visible_through_jobs_routes(
    server: tuple[httpx2.Client, str],
) -> None:
    client, _ = server
    repro = client.post("/simulate", json={"netlist": RC_DECK, "seed": 7}).json()[
        "reproducibility_id"
    ]
    assert len(repro) == 64
    listed = client.get("/jobs").json()
    assert len(listed) == 1
    assert listed[0]["status"] == "succeeded"
    assert listed[0]["kind"] == "simulate"
    detail = client.get(f"/jobs/{listed[0]['job_id']}").json()
    assert "vectors" in str(detail["result"])
