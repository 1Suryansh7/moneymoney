"""Stage 7B-5 tests: cell browser + schematic routes for the UI shell.

GET /cells (summaries, no payloads) and GET /cells/{id}/schematic
(instances with SI parameter floats, nets, terminal hookups). Tests drive
the ASGI app over real localhost HTTP via httpx2 + uvicorn — no TestClient.
Cells under test are built through POST /instantiate so the schematic
payload reflects real template rows, never hand-seeded storage.
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

CS_PARAMS = {"w_n": 1.0e-06, "l_n": 0.18e-06, "w_p": 2.0e-06, "l_p": 0.18e-06}


def _free_port() -> int:
    """Unbound localhost port (tiny bind-then-release race accepted)."""
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@pytest.fixture()
def server(tmp_path: Path) -> Generator[tuple[httpx2.Client, str], None, None]:
    db = str(tmp_path / "schematic.sqlite")
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


def _make_cs_cell(client: httpx2.Client) -> tuple[str, str]:
    pid = client.post("/projects", json={"name": "schem"}).json()["project_id"]
    anchor = client.post(
        "/cells", json={"project_id": pid, "cell_name": "anchor"}
    ).json()["cell_id"]
    cell_id = str(
        client.post(
            "/instantiate",
            json={
                "cell_id": anchor,
                "template_id": "common_source",
                "parameters": CS_PARAMS,
            },
        ).json()["cell_id"]
    )
    return str(anchor), cell_id


def test_cells_empty_initially(server: tuple[httpx2.Client, str]) -> None:
    client, _ = server
    assert client.get("/cells").json() == []


def test_instantiate_then_cells_and_schematic(
    server: tuple[httpx2.Client, str],
) -> None:
    client, _ = server
    anchor, cell_id = _make_cs_cell(client)
    cells = client.get("/cells").json()
    # Template instantiation also writes one master cell per device symbol,
    # so the browser honestly lists those too — assert membership, not count.
    assert {anchor, cell_id} <= {c["cell_id"] for c in cells}
    assert all(set(c) == {"cell_id", "cell_name", "library_name"} for c in cells)
    schem = client.get(f"/cells/{cell_id}/schematic").json()
    assert schem["cell_id"] == cell_id
    by_name = {i["instance_name"]: i for i in schem["instances"]}
    assert set(by_name) == {"m1", "m2"}
    assert by_name["m1"]["symbol_name"] == "nfet_01v8"
    assert by_name["m2"]["symbol_name"] == "pfet_01v8"
    assert by_name["m1"]["parameters"]["W"] == 1.0e-06
    assert isinstance(by_name["m1"]["parameters"]["W"], float)
    assert set(schem["nets"]) == {"in", "out", "vbias", "vdd", "vss"}
    hooks = {
        (p["instance_name"], p["port_name"], p["net_name"]) for p in schem["ports"]
    }
    assert ("m1", "d", "out") in hooks
    assert ("m1", "g", "in") in hooks
    assert ("m2", "g", "vbias") in hooks


def test_unknown_cell_schematic_422(server: tuple[httpx2.Client, str]) -> None:
    client, _ = server
    resp = client.get("/cells/nope/schematic")
    assert resp.status_code == 422
    assert "unknown cell_id" in resp.json()["detail"]
