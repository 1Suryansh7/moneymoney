"""Stage 7B-8 tests: one-click demo testbench for the UI Run button.

POST /testbenches/run assembles the canonical inverter transient deck
server-side from the Stage 2 fixture — the frontend sends a name and
polls the job, never authors netlists. Unknown names fail closed
(422); missing backends surface taxonomy (500). The live EDA test
runs the deck and asserts rail-to-rail inversion through the
waveforms route, mirroring the 7B-3 thin slice over the demo path.
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
from analog_ic_design.sim.ngspice import libngspice_available

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
def server(tmp_path: Path) -> Generator[httpx2.Client, None, None]:
    app = create_app(db_path=str(tmp_path / "demo.sqlite"))
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


def test_unknown_demo_422(server: httpx2.Client) -> None:
    resp = server.post("/testbenches/run", json={"name": "nope", "seed": 21})
    assert resp.status_code == 422
    assert "unknown demo testbench" in resp.json()["detail"]


def test_demo_without_backend_500_taxonomy(server: httpx2.Client) -> None:
    if libngspice_available():
        pytest.skip("backend present; the 500 path is base-only")
    resp = server.post("/testbenches/run", json={"name": "inverter_tran", "seed": 21})
    assert resp.status_code == 500
    assert "Schema: simulate requires libngspice" in resp.json()["detail"]


@NEEDS_LIB
def test_live_demo_inverts_rail_to_rail(server: httpx2.Client) -> None:
    body = server.post(
        "/testbenches/run", json={"name": "inverter_tran", "seed": 21}
    ).json()
    assert body["cell_id"]
    assert len(body["reproducibility_id"]) == 64
    wave = server.get(f"/jobs/{body['job_id']}/waveforms").json()
    assert wave["analysis"] == "tran"
    by_name = {t["name"]: t for t in wave["traces"]}
    v_in, v_out = by_name["in"]["y"], by_name["out"]["y"]
    assert min(v_in) < 0.1 and max(v_in) > 1.7
    assert min(v_out) < 0.1 and max(v_out) > 1.7
    assert (v_in[0] < 0.9) != (v_out[0] < 0.9)
