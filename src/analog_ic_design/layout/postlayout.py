"""Pre/post-layout comparison runner: schematic twin vs extracted twin.

Canonical B3 CS fixture, characterized twice: once with the schematic
M1, once with M1 swapped for the Magic-extracted SI subckt of the PCell
NMOS. The frontend sends nothing but an optional seed and renders the
returned table — all physics lives here (ADR-031 dumb-frontend rule).

Toolchain (klayout + magic + PDK tech) and simulator absences fail
closed with taxonomy-worded `SimError`; the runner returns data, never
raises on simulation faults beyond that. `EngineV01` is imported lazily
(established pattern) to keep the engine->layout import one-directional.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Final

from analog_ic_design.layout.pcells import LAYERS, PIN_LAYERS, mos_labels, nmos_rects
from analog_ic_design.layout.pex import to_schematic_subckt
from analog_ic_design.metrics.bandwidth import extract_bandwidth
from analog_ic_design.metrics.gain import extract_ac_gain, extract_dc_gain
from analog_ic_design.sim.cs_amp import build_cs_amplifier
from analog_ic_design.sim.ngspice import RawSim, SimError, libngspice_available
from analog_ic_design.sim.testbench import assemble_ac, assemble_dc_sweep
from analog_ic_design.sim.waveform import parse_ac
from analog_ic_design.store.schema import connect, migrate

SKY130_LIB = "/usr/local/share/pdk/sky130A/libs.tech/ngspice/sky130.lib.spice"
SKY130_TECH = "/usr/local/share/pdk/sky130A/libs.tech/magic/sky130A.tech"
_BIAS_EXTRA: Final = ["Vbias vbias 0 DC 0.9"]
_AC_LOAD_F: Final = 2.0


def _repo_scripts() -> Path:
    root = Path(__file__).resolve().parent.parent.parent.parent
    scripts = root / "scripts"
    for name in ("layout_pcell_emit.py", "magic_pex.tcl"):
        if not (scripts / name).is_file():
            raise SimError(f"Schema: layout script {name} missing beside the package")
    return scripts


def _extract_spice_text(workdir: Path) -> str:
    """Emit the canonical PCell, extract with parasitics, return ext text."""
    if shutil.which("klayout") is None or shutil.which("magic") is None:
        raise SimError("Schema: layout toolchain absent (klayout/magic required)")
    if not Path(SKY130_TECH).is_file():
        raise SimError("Schema: Magic tech file absent (EDA image required)")
    scripts = _repo_scripts()
    rects = nmos_rects(w_m=1e-6, l_m=0.15e-6, fingers=1)
    labels = mos_labels(w_m=1e-6, l_m=0.15e-6, fingers=1)
    spec = {
        "layers": {name: list(lv) for name, lv in LAYERS.items()},
        "pin_layers": {name: list(lv) for name, lv in PIN_LAYERS.items()},
        "rects": {name: [list(r) for r in boxes] for name, boxes in rects.items()},
        "labels": [list(label) for label in labels],
    }
    (workdir / "rects.json").write_text(json.dumps(spec), encoding="utf-8")
    emit = subprocess.run(
        ["klayout", "-b", "-r", str(scripts / "layout_pcell_emit.py")],
        capture_output=True,
        text=True,
        timeout=300,
        cwd=workdir,
    )
    if emit.returncode != 0:
        raise SimError(f"SPICE convergence: emitter failed: {emit.stderr[-500:]}")
    magic = subprocess.run(
        ["magic", "-dnull", "-noconsole", "-T", SKY130_TECH],
        input=(scripts / "magic_pex.tcl").read_text(encoding="utf-8"),
        capture_output=True,
        text=True,
        timeout=600,
        cwd=workdir,
    )
    if magic.returncode != 0:
        raise SimError(f"SPICE convergence: extraction failed: {magic.stderr[-500:]}")
    spice = workdir / "pcell_nmos.spice"
    if not spice.is_file():
        raise SimError("Schema: extraction produced no netlist")
    return spice.read_text(encoding="utf-8")


def _swap_m1(frag: str, sub: str) -> str:
    """Replace the compiled Xm1 device line with the extracted subckt."""
    lines = frag.splitlines()
    m1 = next((text for text in lines[1:] if re.match(r"^Xm1\s", text)), None)
    if m1 is None:
        raise SimError("Schema: CS fixture has no Xm1 device line")
    nets = m1.split()[1:5]
    body = [
        text for text in lines[1:]
        if not re.match(r"^Xm1\s", text) and text.strip().lower() != ".end"
    ]
    inst = f"Xpex1 {' '.join(nets)} pex_nmos"
    return lines[0] + "\n" + sub + "\n".join(body) + "\n" + inst + "\n.end\n"


def compare_prepost(*, seed: int = 21) -> dict[str, Any]:
    """Characterize the canonical CS stage pre- and post-layout.

    Returns `{"pre": {...}, "post": {...}, "ugb_drop_frac",
    "dc_rel_diff", "ac_rel_diff"}` with SI floats. Raises `SimError`
    (taxonomy-worded) when tools, PDK, or backend are absent, or any
    simulation faults — the route maps it, the UI renders it.
    """
    from analog_ic_design.engine.engine_v01 import EngineV01

    if not libngspice_available():
        raise SimError("Schema: simulator backend absent (libngspice required)")
    with tempfile.TemporaryDirectory() as td:
        workdir = Path(td) / "pex"
        workdir.mkdir()
        ext = _extract_spice_text(workdir)
        sub = to_schematic_subckt(ext, subckt_name="pex_nmos")
        db = str(Path(td) / "prepost.sqlite")
        setup = connect(db)
        try:
            migrate(setup)
            cell = build_cs_amplifier(setup)
        finally:
            setup.close()
        eng = EngineV01(db_path=db)
        try:
            frag = eng.netlist(cell_id=cell)

            def characterize(deck_frag: str) -> dict[str, float]:
                eng.simulate(
                    netlist=assemble_dc_sweep(
                        deck_frag, sweep_net="in", v_start=0.4, v_stop=1.2,
                        v_step=0.005, extra_lines=_BIAS_EXTRA, libs=[(SKY130_LIB, "tt")],
                    ),
                    seed=seed,
                )
                jobs = eng.list_jobs()
                vecs = json.loads(
                    str(eng.job_result(job_id=jobs[0]["job_id"])["result"]
                ))["vectors"]
                vin = [float(v) for v in vecs["in"]]
                vout = [float(v) for v in vecs["out"]]
                dc = extract_dc_gain(vin, vout)
                slopes = [
                    abs((vout[i + 1] - vout[i]) / (vin[i + 1] - vin[i]))
                    for i in range(len(vin) - 1)
                ]
                trip = vin[slopes.index(max(slopes))]
                eng.simulate(
                    netlist=assemble_ac(
                        deck_frag, in_net="in", v_bias=trip,
                        extra_lines=_BIAS_EXTRA + [f"Cload2 out 0 {_AC_LOAD_F}f"],
                        libs=[(SKY130_LIB, "tt")],
                    ),
                    seed=seed,
                )
                jobs = eng.list_jobs()
                payload = json.loads(
                    str(eng.job_result(job_id=jobs[0]["job_id"])["result"])
                )
                cx = {
                    k: [complex(p[0], p[1]) for p in v]
                    for k, v in payload.get("complex_vectors", {}).items()
                }
                wave = parse_ac(
                    RawSim(vectors=payload["vectors"], complex_vectors=cx, log="")
                )
                return {
                    "dc_gain": dc,
                    "ac_gain": extract_ac_gain(wave, in_node="in", out_node="out"),
                    "ugb_hz": extract_bandwidth(wave, in_node="in", out_node="out"),
                    "trip_v": trip,
                }

            pre = characterize(frag)
            post = characterize(_swap_m1(frag, sub))
        finally:
            eng.close()
    dc_rel = abs(post["dc_gain"] - pre["dc_gain"]) / pre["dc_gain"]
    ac_rel = abs(post["ac_gain"] - pre["ac_gain"]) / pre["ac_gain"]
    return {
        "pre": pre,
        "post": post,
        "dc_rel_diff": dc_rel,
        "ac_rel_diff": ac_rel,
        "ugb_drop_frac": (pre["ugb_hz"] - post["ugb_hz"]) / pre["ugb_hz"],
    }


__all__ = ["compare_prepost"]
