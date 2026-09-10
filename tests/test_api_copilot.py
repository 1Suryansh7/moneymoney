"""Stage 7B-7 tests: grounded copilot explanations per failed job.

POST /copilot/explain classifies the stored taxonomy-prefixed error with
the job itself as evidence and narrates through the deterministic mock
model — hosted models stay out until a human opt-in flow exists. Every
response carries its AIAction provenance id, pinned by reading the
ledger row back directly (tests may touch storage; product code may not).
"""

from __future__ import annotations

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

STAMP = "2026-09-05T00:00:00+00:00"


def _free_port() -> int:
    """Unbound localhost port (tiny bind-then-release race accepted)."""
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@pytest.fixture()
def server(tmp_path: Path) -> Generator[tuple[httpx2.Client, str], None, None]:
    db = str(tmp_path / "copilot.sqlite")
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


def _seed_job(db: str, job_id: str, status: str, error: str | None) -> str:
    conn = sqlite3.connect(db)
    try:
        conn.execute(
            "INSERT INTO job (id, kind, status, payload, result, error,"
            " created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (job_id, "simulate", status, "{}", None, error, STAMP, STAMP),
        )
        conn.commit()
    finally:
        conn.close()
    return job_id


def _ai_actions(db: str) -> list[tuple[str, ...]]:
    conn = sqlite3.connect(db)
    try:
        return list(
            conn.execute(
                "SELECT action_type, model_provider, model_name,"
                " source_artifacts FROM ai_action"
            ).fetchall()
        )
    finally:
        conn.close()


def test_unknown_job_explain_404(server: tuple[httpx2.Client, str]) -> None:
    client, _ = server
    resp = client.post("/copilot/explain", json={"job_id": "nope"})
    assert resp.status_code == 404
    assert "unknown job" in resp.json()["detail"]


def test_succeeded_job_explain_422(server: tuple[httpx2.Client, str]) -> None:
    client, db = server
    jid = _seed_job(db, "job-ok-1", "succeeded", None)
    resp = client.post("/copilot/explain", json={"job_id": jid})
    assert resp.status_code == 422
    assert "nothing to explain" in resp.json()["detail"]
    assert _ai_actions(db) == []


def test_failed_job_explained_with_provenance(
    server: tuple[httpx2.Client, str],
) -> None:
    client, db = server
    jid = _seed_job(
        db, "job-bad-1", "failed", "SimError: SPICE convergence: boom\nTraceback ..."
    )
    body = client.post("/copilot/explain", json={"job_id": jid}).json()
    assert body["job_id"] == jid
    assert body["category"] == "spice_convergence"
    assert body["cited_ids"] == [jid]
    assert jid in body["prose"]
    assert body["provider"] == "mock"
    assert body["action_id"]
    rows = _ai_actions(db)
    assert len(rows) == 1
    assert rows[0][0] == "explain_failure"
    assert rows[0][1] == "mock"
    assert jid in str(rows[0][3])


def test_unclassifiable_failure_422_without_provenance(
    server: tuple[httpx2.Client, str],
) -> None:
    client, db = server
    jid = _seed_job(db, "job-weird-1", "failed", "Something exploded mysteriously")
    resp = client.post("/copilot/explain", json={"job_id": jid})
    assert resp.status_code == 422
    assert "cannot classify" in resp.json()["detail"]
    assert _ai_actions(db) == []
