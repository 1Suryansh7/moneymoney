"""R0-4b backend tests: POST /measure over the threaded HTTP service.

Unknown metrics, unknown cells, and unregistered structures fail
closed at 422 with taxonomy wording; missing backends surface at
500. The live EDA test measures a real inverter cell end to end
and pins value plus canonical unit on the wire.
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

from analog_ic_design.api.server import create_app
from analog_ic_design.sim.inverter import build_inverter
from analog_ic_design.sim.ngspice import libngspice_available
from analog_ic_design.store.schema import connect

NEEDS_LIB = pytest.mark.skipif(
    not libngspice_available(),
    reason="libngspice absent (base image); covered by CI eda job",
)


def _free_port() -> int:
    """Unbound localhost port (tiny bind-then-release race accepted)."""
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@pytest.fixture()
def server(tmp_path: Path) -> Generator[tuple[httpx2.Client, str], None, None]:
    db = str(tmp_path / "measure.sqlite")
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


def _build_inverter_cell(db: str) -> str:
    setup = connect(db)
    try:
        cell = build_inverter(setup)
        setup.commit()
        return cell
    finally:
        setup.close()


def test_unknown_metric_422(server: tuple[httpx2.Client, str]) -> None:
    client, _ = server
    resp = client.post("/measure", json={"cell_id": "x", "metric_id": "gain"})
    assert resp.status_code == 422
    assert "unknown metric_id" in resp.json()["detail"]


def test_unknown_cell_422(server: tuple[httpx2.Client, str]) -> None:
    client, _ = server
    resp = client.post("/measure", json={"cell_id": "nope", "metric_id": "dc_gain"})
    assert resp.status_code == 422
    assert "unknown cell_id" in resp.json()["detail"]


def test_unregistered_structure_422(server: tuple[httpx2.Client, str]) -> None:
    client, _ = server
    pid = client.post("/projects", json={"name": "p"}).json()["project_id"]
    cid = client.post("/cells", json={"project_id": pid, "cell_name": "empty"}).json()[
        "cell_id"
    ]
    resp = client.post("/measure", json={"cell_id": cid, "metric_id": "dc_gain"})
    assert resp.status_code == 422
    assert "no testbench registered" in resp.json()["detail"]


def test_measure_without_backend_500_taxonomy(
    server: tuple[httpx2.Client, str],
) -> None:
    if libngspice_available():
        pytest.skip("backend present; the 500 path is base-only")
    client, db = server
    cell = _build_inverter_cell(db)
    resp = client.post("/measure", json={"cell_id": cell, "metric_id": "dc_gain"})
    assert resp.status_code == 500
    assert "Schema: simulate requires libngspice" in resp.json()["detail"]


@NEEDS_LIB
def test_live_measure_dc_gain(server: tuple[httpx2.Client, str]) -> None:
    client, db = server
    cell = _build_inverter_cell(db)
    body = client.post("/measure", json={"cell_id": cell, "metric_id": "dc_gain"}).json()
    assert body["metric_id"] == "dc_gain"
    assert body["unit"] == "V/V"
    assert body["value"] > 5.0
