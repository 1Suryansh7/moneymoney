"""Stage 7B-3 tests: thin-slice inverter end-to-end over HTTP.

UI run control -> FastAPI -> DesignEngine -> worker sim -> parsed
waveform. The inverter cell is seeded with the Stage 2 prototype builder
(direct DB fixture setup is test scaffolding, not product code); every
design operation under test crosses HTTP. Base suite covers validate +
deterministic netlist; the live waveform runs under NEEDS_LIB (EDA).
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
from analog_ic_design.sim.inverter import build_inverter
from analog_ic_design.sim.ngspice import RawSim, libngspice_available
from analog_ic_design.sim.testbench import assemble_transient
from analog_ic_design.sim.waveform import parse_transient
from analog_ic_design.store.schema import connect, migrate

NEEDS_LIB = pytest.mark.skipif(
    not libngspice_available(),
    reason="libngspice absent (base image); covered by CI eda job",
)
SKY130_LIB = "/usr/local/share/pdk/sky130A/libs.tech/ngspice/sky130.lib.spice"


def _free_port() -> int:
    """Unbound localhost port (tiny bind-then-release race accepted)."""
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@pytest.fixture()
def slicedb(tmp_path: Path) -> Generator[tuple[httpx2.Client, str], None, None]:
    """Live API server over a DB pre-seeded with the inverter prototype."""
    db = str(tmp_path / "slice.sqlite")
    setup = connect(db)
    try:
        migrate(setup)
        cell = build_inverter(setup)
    finally:
        setup.close()
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
    yield client, cell
    client.close()
    server.should_exit = True
    thread.join(timeout=15.0)


def test_thin_slice_validate_netlist_over_http(
    slicedb: tuple[httpx2.Client, str],
) -> None:
    """Inverter validates and compiles deterministically through the API."""
    client, cell = slicedb
    verdict = client.post("/validate", json={"cell_id": cell}).json()
    assert verdict == {"valid": True, "violations": []}
    first = client.post("/netlist", json={"cell_id": cell}).json()["netlist"]
    assert client.post("/netlist", json={"cell_id": cell}).json()["netlist"] == first
    assert "sky130_fd_pr__nfet_01v8" in first
    assert "sky130_fd_pr__pfet_01v8" in first


@NEEDS_LIB
def test_thin_slice_live_waveform_over_http(
    slicedb: tuple[httpx2.Client, str], tmp_path: Path
) -> None:
    """Full slice: HTTP netlist -> HTTP simulate -> parsed rail-to-rail wave."""
    client, cell = slicedb
    frag = client.post("/netlist", json={"cell_id": cell}).json()["netlist"]
    deck = assemble_transient(frag, tstop_s=30e-9, libs=[(SKY130_LIB, "tt")])
    repro = client.post("/simulate", json={"netlist": deck, "seed": 21}).json()[
        "reproducibility_id"
    ]
    assert len(repro) == 64
    assert all(c in "0123456789abcdef" for c in repro)

    db_path = str(tmp_path / "slice.sqlite")
    probe = sqlite3.connect(db_path)
    try:
        row = probe.execute(
            "SELECT result FROM job ORDER BY created_at DESC LIMIT 1"
        ).fetchone()
    finally:
        probe.close()
    assert row is not None and row[0] is not None
    raw = json.loads(str(row[0]))["vectors"]
    wave = parse_transient(RawSim(vectors=dict(raw), log=""))
    vin = [float(v) for v in wave.trace("in").values]
    vout = [float(v) for v in wave.trace("out").values]
    assert min(vout) < 0.1
    assert max(vout) > 1.7
    high_in = [o for i, o in zip(vin, vout, strict=True) if i > 1.62]
    low_in = [o for i, o in zip(vin, vout, strict=True) if i < 0.18]
    assert high_in and all(o < 0.18 for o in high_in)
    assert low_in and all(o > 1.62 for o in low_in)
