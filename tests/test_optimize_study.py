"""R0-5 Commit 1 tests: async study lifecycle over threaded HTTP.

Submit validation fails fast (422, no rows, no procs). Mock-objective
studies prove the full lifecycle EDA-free: enqueue -> run -> trials
-> succeeded, plus cancel-mid-run. The live EDA test runs a real
3-trial common-source study (gain + bandwidth spec) and pins
structure, finiteness, and best-score consistency.
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

SPACE = {"w_n": [0.5e-06, 2.0e-06], "w_p": [1.0e-06, 4.0e-06]}


def _free_port() -> int:
    """Unbound localhost port (tiny bind-then-release race accepted)."""
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@pytest.fixture()
def server(tmp_path: Path) -> Generator[tuple[httpx2.Client, str], None, None]:
    db = str(tmp_path / "study.sqlite")
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
    client = httpx2.Client(base_url=base, timeout=120.0)
    yield client, db
    client.close()
    server.should_exit = True
    thread.join(timeout=15.0)


def _seed_spec(
    client: httpx2.Client, db: str, rules: list[tuple[str, str, float]]
) -> str:
    pid = client.post("/projects", json={"name": "sp"}).json()["project_id"]
    cid = client.post("/cells", json={"project_id": pid, "cell_name": "c"}).json()[
        "cell_id"
    ]
    conn = sqlite3.connect(db)
    try:
        conn.execute(
            "INSERT INTO specification VALUES (?, ?, ?, ?)",
            ("spec-1", cid, "demo-spec", "2026-09-12T00:00:00+00:00"),
        )
        for i, (metric, operator, threshold) in enumerate(rules):
            conn.execute(
                "INSERT INTO constraint_rule VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    f"rule-{i}", "spec-1", "hard", metric, operator,
                    threshold, 0.0, i, None, "2026-09-12T00:00:00+00:00",
                ),
            )
        conn.commit()
    finally:
        conn.close()
    return "spec-1"


def _submit(
    client: httpx2.Client, spec: str, **kw: Any
) -> httpx2.Response:
    body: dict[str, object] = {
        "template_id": "common_source",
        "spec_id": spec,
        "space": SPACE,
        "seed": 7,
        "max_trials": 2,
        "objective": "mock",
    }
    body.update(kw)
    return client.post("/optimize", json=body)


def _wait_terminal(client: httpx2.Client, job_id: str, deadline_s: float) -> str:
    deadline = time.time() + deadline_s
    while True:
        status = client.get(f"/jobs/{job_id}").json()["status"]
        if status in ("succeeded", "failed", "cancelled"):
            return str(status)
        if time.time() > deadline:
            raise TimeoutError(f"study {job_id} unsettled after {deadline_s}s")
        time.sleep(1.0)


def test_submit_rejects_unknown_template(server: tuple[httpx2.Client, str]) -> None:
    client, db = server
    spec = _seed_spec(client, db, [("dc_gain", ">=", 5.0), ("bandwidth", ">=", 1e6)])
    resp = _submit(client, spec, template_id="nope")
    assert resp.status_code == 422
    assert "unknown template_id" in resp.json()["detail"]


def test_submit_rejects_unknown_spec(server: tuple[httpx2.Client, str]) -> None:
    client, _ = server
    resp = _submit(client, "spec-nope")
    assert resp.status_code == 422
    assert "unknown spec_id" in resp.json()["detail"]


def test_submit_rejects_bad_space(server: tuple[httpx2.Client, str]) -> None:
    client, db = server
    spec = _seed_spec(client, db, [("dc_gain", ">=", 5.0), ("bandwidth", ">=", 1e6)])
    for bad_space, needle in [
        ({}, "no parameters"),
        ({"w_n": [2.0e-06, 0.5e-06]}, "0 < low < high"),
        ({"w_n": [-1.0e-06, 2.0e-06]}, "0 < low < high"),
        ({"nope": [0.5e-06, 2.0e-06]}, "unknown parameter"),
    ]:
        resp = _submit(client, spec, space=bad_space)
        assert resp.status_code == 422, bad_space
        assert needle in resp.json()["detail"], bad_space


def test_submit_rejects_bad_budgets_and_objective(
    server: tuple[httpx2.Client, str],
) -> None:
    client, db = server
    spec = _seed_spec(client, db, [("dc_gain", ">=", 5.0), ("bandwidth", ">=", 1e6)])
    cases: list[tuple[dict[str, Any], str]] = [
        ({"max_trials": 0}, "1..30"),
        ({"max_trials": 31}, "1..30"),
        ({"trial_timeout_s": 0}, "positive"),
        ({"objective": "vibes"}, "unknown objective"),
    ]
    for kw, needle in cases:
        resp = _submit(client, spec, **kw)
        assert resp.status_code == 422, kw
        assert needle in resp.json()["detail"], kw


def test_submit_rejects_degenerate_specs(server: tuple[httpx2.Client, str]) -> None:
    client, db = server
    single = _seed_spec(client, db, [("dc_gain", ">=", 5.0)])
    resp = _submit(client, single)
    assert resp.status_code == 422
    assert "single-metric" in resp.json()["detail"]
    conn = sqlite3.connect(db)
    try:
        pid = client.post("/projects", json={"name": "sp2"}).json()["project_id"]
        cid = client.post(
            "/cells", json={"project_id": pid, "cell_name": "c2"}
        ).json()["cell_id"]
        conn.execute(
            "INSERT INTO specification VALUES (?, ?, ?, ?)",
            ("spec-2", cid, "bad", "2026-09-12T00:00:00+00:00"),
        )
        conn.execute(
            "INSERT INTO constraint_rule VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("rule-x", "spec-2", "hard", "slew_rate", ">=", 1.0,
             0.0, 0, None, "2026-09-12T00:00:00+00:00"),
        )
        conn.commit()
    finally:
        conn.close()
    resp = _submit(client, "spec-2")
    assert resp.status_code == 422
    assert "unmeasured metrics" in resp.json()["detail"]


def test_mock_study_completes_with_telemetry(
    server: tuple[httpx2.Client, str],
) -> None:
    client, _ = server
    spec = _seed_spec(
        server[0], server[1], [("dc_gain", ">=", 5.0), ("bandwidth", ">=", 1e6)]
    )
    out = _submit(client, spec).json()
    assert _wait_terminal(client, out["job_id"], 180.0) == "succeeded"
    trials = client.get(f"/studies/{out['study_id']}/trials").json()
    assert len(trials) == 2
    assert [t["trial"] for t in trials] == [0, 1]
    assert all(t["status"] == "succeeded" for t in trials)
    assert all(isinstance(t["score"], float) for t in trials)
    assert all(set(t["parameters"]) == {"w_n", "w_p"} for t in trials)


def test_cancel_mid_study(server: tuple[httpx2.Client, str]) -> None:
    client, _ = server
    spec = _seed_spec(
        server[0], server[1], [("dc_gain", ">=", 5.0), ("bandwidth", ">=", 1e6)]
    )
    out = _submit(
        client, spec, objective="mock-slow", max_trials=3
    ).json()
    deadline = time.time() + 90.0
    while True:
        if client.get(f"/jobs/{out['job_id']}").json()["status"] == "running":
            break
        if time.time() > deadline:
            raise TimeoutError("study never started running")
        time.sleep(1.0)
    body = client.post(f"/jobs/{out['job_id']}/cancel").json()
    assert body["status"] == "cancelled"
    assert _wait_terminal(client, out["job_id"], 60.0) == "cancelled"
    again = client.post(f"/jobs/{out['job_id']}/cancel").json()
    assert again["status"] == "cancelled"


def test_unknown_study_and_cancel_404(server: tuple[httpx2.Client, str]) -> None:
    client, _ = server
    assert client.get("/studies/nope/trials").status_code == 404
    assert client.post("/jobs/nope/cancel").status_code == 404


@NEEDS_LIB
def test_live_three_trial_cs_study(server: tuple[httpx2.Client, str]) -> None:
    client, _ = server
    spec = _seed_spec(
        server[0], server[1], [("dc_gain", ">=", 5.0), ("bandwidth", ">=", 1e6)]
    )
    out = _submit(
        client, spec, max_trials=3, objective="spec"
    ).json()
    assert _wait_terminal(client, out["job_id"], 1500.0) == "succeeded"
    trials = client.get(f"/studies/{out['study_id']}/trials").json()
    assert len(trials) == 3
    scores = [t["score"] for t in trials]
    assert all(isinstance(s, float) for s in scores)
    detail = client.get(f"/jobs/{out['job_id']}").json()
    result = json.loads(str(detail["result"]))
    assert result["trials_completed"] == 3
    assert result["best_score"] == max(scores)
