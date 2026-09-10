"""Stage 7B-9 tests: cell rename for dialog-named template cells.

POST /cells/{id}/rename lets the UI honor the name typed in
NewCellDialog: template instantiation derives its own cell name,
so rename closes the loop without touching the frozen ABC surface.
Unknown cells and empty names fail closed (422, taxonomy wording).
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


def _free_port() -> int:
    """Unbound localhost port (tiny bind-then-release race accepted)."""
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@pytest.fixture()
def server(tmp_path: Path) -> Generator[httpx2.Client, None, None]:
    app = create_app(db_path=str(tmp_path / "cells.sqlite"))
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
    server.should_exit = True
    thread.join(timeout=15.0)


def _make_cell(client: httpx2.Client, name: str = "anchor") -> str:
    pid = client.post("/projects", json={"name": "ren"}).json()["project_id"]
    return str(
        client.post("/cells", json={"project_id": pid, "cell_name": name}).json()[
            "cell_id"
        ]
    )


def test_rename_roundtrip_server(server: httpx2.Client) -> None:
    cell_id = _make_cell(server)
    body = server.post(f"/cells/{cell_id}/rename", json={"cell_name": "my_amp"}).json()
    assert body == {"cell_id": cell_id, "cell_name": "my_amp"}
    cells = server.get("/cells").json()
    assert {c["cell_name"] for c in cells} == {"my_amp"}
    schem = server.get(f"/cells/{cell_id}/schematic").json()
    assert schem["cell_name"] == "my_amp"


def test_rename_unknown_cell_422(server: httpx2.Client) -> None:
    resp = server.post("/cells/nope/rename", json={"cell_name": "x"})
    assert resp.status_code == 422
    assert "unknown cell_id" in resp.json()["detail"]


def test_rename_empty_name_422(server: httpx2.Client) -> None:
    cell_id = _make_cell(server)
    resp = server.post(f"/cells/{cell_id}/rename", json={"cell_name": "  "})
    assert resp.status_code == 422
    assert "non-empty" in resp.json()["detail"]
