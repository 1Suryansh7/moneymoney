"""Track B1 tests: PVT corner sweep over HTTP.

POST /corners/run simulates one canonical demo deck across the Stage 4.5
five-corner envelope, one ledger job per corner. Bad requests fail closed
(422); per-corner simulator faults stay in rows (fail-soft) so dispersion
display always has a complete sweep to render. Base asserts the fail-soft
shape with taxonomy messages and no jobs; the live EDA test asserts five
succeeded corner jobs whose waveforms prove real dispersion through the
existing waveforms route.
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

PROCESSES = ["tt", "ff", "ss", "fs", "sf"]


def _free_port() -> int:
    """Unbound localhost port (tiny bind-then-release race accepted)."""
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@pytest.fixture()
def server(tmp_path: Path) -> Generator[httpx2.Client, None, None]:
    app = create_app(db_path=str(tmp_path / "corners.sqlite"))
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
    # Sweep latency is ~20 s per corner (MEASURED live): five corners
    # exceed the 60 s single-sim client budget, so the fixture carries
    # 300 s. Test-only change per the R0-4b precedent (test.slow(), no
    # product change); the product stays synchronous by design.
    client = httpx2.Client(base_url=base, timeout=300.0)
    yield client
    client.close()
    server.should_exit = True
    thread.join(timeout=15.0)


def test_unknown_demo_422(server: httpx2.Client) -> None:
    resp = server.post("/corners/run", json={"name": "nope"})
    assert resp.status_code == 422
    assert "unknown demo testbench" in resp.json()["detail"]


def test_unknown_corner_422(server: httpx2.Client) -> None:
    resp = server.post("/corners/run", json={"corners": ["tt", "xx"]})
    assert resp.status_code == 422
    assert "unknown corner" in resp.json()["detail"]


def test_empty_corners_422(server: httpx2.Client) -> None:
    resp = server.post("/corners/run", json={"corners": []})
    assert resp.status_code == 422
    assert "at least one corner" in resp.json()["detail"]


def test_base_sweep_returns_fail_soft_rows(server: httpx2.Client) -> None:
    """No backend: five error rows with taxonomy, no jobs, nothing raised."""
    if libngspice_available():
        pytest.skip("backend present; fail-soft shape covered on base")
    body = server.post("/corners/run", json={}).json()
    assert body["name"] == "inverter_tran"
    assert [r["process"] for r in body["runs"]] == PROCESSES
    for run in body["runs"]:
        assert run["status"] == "error"
        assert run["job_id"] is None
        assert run["message"]
        assert run["reproducibility_id"] is None
    assert server.get("/jobs").json() == []


def test_subset_selection_honored(server: httpx2.Client) -> None:
    """Checkbox state maps to envelope ids; unselected corners never run."""
    if libngspice_available():
        pytest.skip("backend present; selection shape covered on base")
    body = server.post("/corners/run", json={"corners": ["tt", "ss"]}).json()
    assert [r["process"] for r in body["runs"]] == ["tt", "ss"]


@NEEDS_LIB
def test_live_envelope_sweeps_with_dispersion(server: httpx2.Client) -> None:
    """EDA: five succeeded corner jobs; waveforms show real dispersion."""
    body = server.post("/corners/run", json={}).json()
    assert [r["process"] for r in body["runs"]] == PROCESSES
    vout_spans = []
    for run in body["runs"]:
        assert run["status"] == "succeeded", run
        assert run["job_id"]
        assert run["reproducibility_id"] and len(run["reproducibility_id"]) == 64
        wave = server.get(f"/jobs/{run['job_id']}/waveforms").json()
        assert wave["analysis"] == "tran"
        vout = next(t for t in wave["traces"] if t["name"] == "out")
        vout_spans.append((min(vout["y"]), max(vout["y"])))
        assert min(vout["y"]) < 0.1
        # Rail tracks the corner supply (1.62/1.80/1.98 V), not a fixed
        # number — this is the dispersion fingerprint itself.
        assert abs(max(vout["y"]) - run["vdd_v"]) < 0.05
    # Dispersion is real: corner supplies differ, so at least one span
    # edge moves across the envelope (not five identical waves).
    assert len({round(lo, 6) for lo, _ in vout_spans}) > 1 or len(
        {round(hi, 6) for _, hi in vout_spans}
    ) > 1
