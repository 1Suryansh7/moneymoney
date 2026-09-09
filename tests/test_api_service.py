"""Stage 7B tests: FastAPI service strictly over EngineV01.

httpx2 drives the ASGI app directly (no TestClient, no live server, no
starlette test shims — that path trips deprecation-as-error under our
filterwarnings gate). Each test owns one tmp database; the engine is
closed explicitly. SI base-unit floats cross the wire; the rejection of
unit strings is asserted, not assumed.
"""

from __future__ import annotations

import socket
import threading
import time
from collections.abc import Generator
from pathlib import Path

import httpx2
import pytest
import uvicorn

from analog_ic_design import ENGINE_API_VERSION
from analog_ic_design.api.server import create_app


def _free_port() -> int:
    """Unbound localhost port (tiny bind-then-release race accepted)."""
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@pytest.fixture()
def client(tmp_path: Path) -> Generator[httpx2.Client, None, None]:
    app = create_app(db_path=tmp_path / "api.sqlite")
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
    yield client
    client.close()
    # Lifespan shutdown (engine close) runs in the server thread on exit.
    server.should_exit = True
    thread.join(timeout=15.0)


def test_health_reports_contract_version(client: httpx2.Client) -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok", "engine_api_version": ENGINE_API_VERSION}


def test_project_cell_instantiate_validate_netlist(client: httpx2.Client) -> None:
    pid = client.post("/projects", json={"name": "p1"}).json()["project_id"]
    assert isinstance(pid, str) and pid
    cid = client.post(
        "/cells", json={"project_id": pid, "cell_name": "anchor"}
    ).json()["cell_id"]
    nid = client.post(
        "/instantiate",
        json={"cell_id": cid, "template_id": "current_mirror", "parameters": {}},
    ).json()["cell_id"]
    verdict = client.post("/validate", json={"cell_id": nid}).json()
    assert verdict == {"valid": True, "violations": []}
    first = client.post("/netlist", json={"cell_id": nid}).json()["netlist"]
    assert client.post("/netlist", json={"cell_id": nid}).json()["netlist"] == first
    assert "nfet" in first


def test_caller_faults_map_to_422_with_taxonomy(client: httpx2.Client) -> None:
    resp = client.post("/projects", json={"name": "  "})
    assert resp.status_code == 422
    assert "Schema" in resp.json()["detail"]
    resp = client.post("/validate", json={"cell_id": "nope"})
    assert resp.status_code == 422
    assert "Schema" in resp.json()["detail"]
    pid = client.post("/projects", json={"name": "p"}).json()["project_id"]
    cid = client.post(
        "/cells", json={"project_id": pid, "cell_name": "a"}
    ).json()["cell_id"]
    resp = client.post(
        "/instantiate",
        json={"cell_id": cid, "template_id": "nope", "parameters": {}},
    )
    assert resp.status_code == 422
    assert "Schema" in resp.json()["detail"]


def test_unit_strings_rejected_at_wire(client: httpx2.Client) -> None:
    """SI floats only: '2u' must fail pydantic validation, never parse."""
    pid = client.post("/projects", json={"name": "p"}).json()["project_id"]
    cid = client.post(
        "/cells", json={"project_id": pid, "cell_name": "a"}
    ).json()["cell_id"]
    resp = client.post(
        "/instantiate",
        json={"cell_id": cid, "template_id": "current_mirror", "parameters": {"w": "2u"}},
    )
    assert resp.status_code == 422


def test_simulate_garbage_fails_closed_with_simerror(client: httpx2.Client) -> None:
    """Base (no lib): pre-check raises. EDA: backend rejects empty analysis."""
    resp = client.post("/simulate", json={"netlist": "* garbage\n.end\n", "seed": 0})
    assert resp.status_code == 500
    assert "SimError" in resp.json()["detail"] or "Schema" in resp.json()["detail"]
