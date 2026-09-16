"""Stage 8 spike tests: backend tool smoke proofs (EDA only).

K (KLayout pya): single-NMOS geometry + OASIS round trip.
M (Magic batch): sky130A tech load + paint + save + DRC check.
N (Netgen batch LVS): self-match passes, gate/drain swap fails. d/s
swap PASSES by correct LVS semantics (`permute default` in
sky130A_setup.tcl treats MOS terminals as symmetric) — not a tool bug.
Base skips everything (no binaries in the base image); the EDA job
proves the paths. Geometry here is honest DRC-dirty demo material, not
PCells — placement rules arrive later.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

SPIKE = (
    Path(__file__).resolve().parent.parent / "scripts" / "layout_spike_nmos.py"
)
MAGIC_TCL = (
    Path(__file__).resolve().parent.parent / "scripts" / "magic_spike.tcl"
)
SKY130_TECH = "/usr/local/share/pdk/sky130A/libs.tech/magic/sky130A.tech"
SKY130_SETUP = "/usr/local/share/pdk/sky130A/libs.tech/netgen/sky130A_setup.tcl"
NEEDS_KLAYOUT = pytest.mark.skipif(
    shutil.which("klayout") is None,
    reason="klayout binary absent (base image); covered by CI eda job",
)
NEEDS_MAGIC = pytest.mark.skipif(
    shutil.which("magic") is None,
    reason="magic binary absent (base image); covered by CI eda job",
)
NEEDS_NETGEN = pytest.mark.skipif(
    shutil.which("netgen") is None,
    reason="netgen binary absent (base image); covered by CI eda job",
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


_LVS_WRAPPER = """\
* lvs smoke wrapper (test-only subckt shell, not a golden)
.subckt nmos_golden drain gate source vss
Xm1 {d} {g} {s} vss sky130_fd_pr__nfet_01v8 L=1.5e-07 W=1e-06
.ends
"""


def _lvs(
    proc_file: str,
    proc_cell: str,
    ref_file: str,
    ref_cell: str,
    run_dir: Path,
) -> subprocess.CompletedProcess[str]:
    # cwd pinned: netgen writes comp.out next to the invocation directory.
    return subprocess.run(
        ["netgen", "-batch", "lvs", f"{proc_file} {proc_cell}",
         f"{ref_file} {ref_cell}", SKY130_SETUP],
        capture_output=True,
        text=True,
        timeout=300,
        cwd=run_dir,
    )


@NEEDS_MAGIC
def test_magic_batch_tech_paint_save_drc(tmp_path: Path) -> None:
    with open(MAGIC_TCL, encoding="utf-8") as handle:
        script = handle.read()
    proc = subprocess.run(
        ["magic", "-dnull", "-noconsole", "-T", SKY130_TECH],
        input=script,
        capture_output=True,
        text=True,
        timeout=300,
        cwd=tmp_path,
    )
    assert proc.returncode == 0, proc.stderr[-2000:]
    assert 'Using technology "sky130A"' in proc.stdout
    assert "No errors found." in proc.stdout
    mag = tmp_path / "spike_magic.mag"
    assert mag.is_file()
    assert "metal1" in mag.read_text(encoding="utf-8")


@NEEDS_NETGEN
def test_netgen_self_lvs_matches_and_asymmetry_fails(tmp_path: Path) -> None:
    good = tmp_path / "a.spice"
    good.write_text(_LVS_WRAPPER.format(d="drain", g="gate", s="source"), encoding="utf-8")
    copy = tmp_path / "a_copy.spice"
    copy.write_text(_LVS_WRAPPER.format(d="drain", g="gate", s="source"), encoding="utf-8")
    # d/s swap passes: `permute default` treats MOS terminals symmetric.
    swapped = tmp_path / "swap_ds.spice"
    swapped.write_text(
        _LVS_WRAPPER.format(d="source", g="gate", s="drain"), encoding="utf-8"
    )
    # Gate/drain swap must fail: asymmetric pins, no permutation saves it.
    broken = tmp_path / "swap_gd.spice"
    broken.write_text(
        _LVS_WRAPPER.format(d="gate", g="drain", s="source"), encoding="utf-8"
    )
    same = _lvs(str(good), "nmos_golden", str(copy), "nmos_golden", tmp_path)
    assert same.returncode == 0
    assert "Circuits match uniquely." in same.stdout
    sym = _lvs(str(good), "nmos_golden", str(swapped), "nmos_golden", tmp_path)
    assert "Circuits match uniquely." in sym.stdout
    bad = _lvs(str(good), "nmos_golden", str(broken), "nmos_golden", tmp_path)
    assert "failed pin matching" in bad.stdout
