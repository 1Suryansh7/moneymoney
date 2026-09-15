"""Stage 8 spike K tests: KLayout single-NMOS geometry proof (EDA only).

Runs `scripts/layout_spike_nmos.py` under `klayout -b -r`, parses the
REPORT lines, and pins the measured shape counts. Base skips (no klayout
binary in the base image); the EDA job proves the API path. The geometry
is an honest DRC-dirty demo device, not a PCell — placement rules arrive
later. OASIS artifact lands in artifacts/layout/ (gitignored weight).
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

SPIKE = (
    Path(__file__).resolve().parent.parent / "scripts" / "layout_spike_nmos.py"
)
NEEDS_KLAYOUT = pytest.mark.skipif(
    shutil.which("klayout") is None,
    reason="klayout binary absent (base image); covered by CI eda job",
)


def _report(stdout: str) -> dict[str, str]:
    out = {}
    for line in stdout.splitlines():
        if line.startswith("REPORT "):
            key, _, value = line[len("REPORT "):].partition("=")
            out[key] = value
    return out


def test_spike_script_present() -> None:
    assert SPIKE.is_file()


@NEEDS_KLAYOUT
def test_pya_nmos_roundtrip(tmp_path: Path) -> None:
    oas = tmp_path / "spike_nmos.oas"
    proc = subprocess.run(
        ["klayout", "-b", "-r", str(SPIKE)],
        capture_output=True,
        text=True,
        timeout=300,
        cwd=tmp_path,
    )
    assert proc.returncode == 0, proc.stderr[-2000:]
    assert oas.is_file() and oas.stat().st_size > 0
    rep = _report(proc.stdout)
    assert rep["layers"] == "8"
    assert rep["boxes_total"] == "16"
    assert rep["dbu_um"] == "0.001"
    assert int(rep["file_bytes"]) > 0
    assert rep["roundtrip_ok"] == "True"
    assert rep["klayout_version"] != ""
