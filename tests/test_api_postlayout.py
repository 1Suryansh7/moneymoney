"""Dashboard B1 tests: pre/post-layout comparison over HTTP.

POST /postlayout/compare characterizes the canonical CS stage with the
schematic M1 and the extracted-SI PCell M1, returning the degradation
table the Explorer renders. Base asserts the fail-closed shape (no
toolchain/backend: taxonomy 500, nothing raised past the route); the
live EDA test pins the honest bands (DC control, UGB drop).
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
    app = create_app(db_path=str(tmp_path / "postlayout.sqlite"))
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
    client = httpx2.Client(base_url=base, timeout=600.0)
    yield client
    client.close()
    server.should_exit = True
    thread.join(timeout=15.0)


def test_base_compare_fails_closed(server: httpx2.Client) -> None:
    """No toolchain/backend on base: taxonomy 500, route intact."""
    if libngspice_available():
        pytest.skip("backend present; fail-closed shape covered on base")
    resp = server.post("/postlayout/compare", json={})
    assert resp.status_code == 500
    assert resp.json()["detail"]


@NEEDS_LIB
def test_live_compare_reports_degradation(server: httpx2.Client) -> None:
    """EDA: DC control holds, UGB drops within the honest band."""
    body = server.post("/postlayout/compare", json={}).json()
    assert set(body) == {"pre", "post", "dc_rel_diff", "ac_rel_diff", "ugb_drop_frac"}
    assert body["dc_rel_diff"] < 0.05
    assert body["ac_rel_diff"] < 0.05
    assert 0.05 < body["ugb_drop_frac"] < 0.30
    assert body["pre"]["ugb_hz"] > 0.0
    assert body["post"]["ugb_hz"] > 0.0
