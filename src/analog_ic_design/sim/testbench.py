"""Transient testbench assembly (Stage 2 Commit 2H).

Wraps a compiled cell fragment with supplies, stimulus, analysis, model
includes, and `.end` into a runnable deck. DELIBERATELY thin demo glue:
stimulus design, corner axes, and measurement hooks belong to the Stage 3
Testbench engine, which will replace this module (the `testbench` /
`analysis` tables from 2B already reserve its home).

PDK-boundary unit convention (read before touching): canonical values in
the DB, compiler, and this function's arguments are SI base units (meters
for geometry). The Sky130 ngspice binned models match raw instance numbers
against micron-unit bin tables, so geometry parameters (`W`, `L`) are
emitted ×1e6 (microns) with `.option scale=1e-6`, per the ngspice-maintainer
recipe (ngspice-users: `.lib <sky130.lib.spice> tt` + `.param
mc_mm_switch=0` + micron geometry + `scale=1e-6`). Volts/seconds stay SI.
Proven by a 2x2 experiment 2026-09-06 in the pinned EDA image: SI-meter
device values fail binned-model lookup at ANY scale setting (`could not
find a valid modelname`), micron values + `scale=1e-6` run clean.
"""

from __future__ import annotations

import re
from collections.abc import Sequence

#: Geometry keys converted meters -> microns at deck emission (Sky130
#: binned-model lookup matches raw numbers in microns; see module docstring).
_GEOM_RE = re.compile(r"\b([WLwl])=(-?[0-9][0-9.eE+-]*)")
_MICRONS_PER_METER = 1e6


def _to_microns(line: str) -> str:
    """Scale `W=`/`L=` values meters -> microns on one fragment line."""

    def _one(match: re.Match[str]) -> str:
        return f"{match.group(1)}={float(match.group(2)) * _MICRONS_PER_METER!r}"

    return _GEOM_RE.sub(_one, line)


def assemble_transient(
    fragment: str,
    *,
    vdd_net: str = "vdd",
    vdd_volts: float = 1.8,
    vss_net: str = "vss",
    pulse_net: str = "in",
    pulse_volts: float = 1.8,
    tstop_s: float = 30e-9,
    includes: Sequence[str] = (),
    libs: Sequence[tuple[str, str]] = (),
) -> str:
    """Assemble a complete transient deck around a cell `fragment`.

    The fragment's trailing `.end` (emitted by the compiler) is replaced by
    model includes, `.lib 'file' section` corner selections, the PDK-required
    `.param mc_mm_switch=0` + `.option scale=1e-6`, micron-converted device
    lines (see module docstring), stimulus, analysis, and `.end`.
    Deterministic by construction.
    """
    body = fragment.splitlines()
    while body and not body[-1].strip():
        body.pop()
    if body and body[-1].strip().lower() == ".end":
        body.pop()
    title, rest = (body[0], body[1:]) if body else ("* testbench", [])
    lines = [title]
    lines += [f".include {path}" for path in includes]
    lines += [f".lib '{path}' {section}" for path, section in libs]
    lines.append(".param mc_mm_switch=0")
    lines.append(".option scale=1e-6")
    lines += [_to_microns(line) for line in rest]
    lines.append(f"VDD {vdd_net} 0 DC {vdd_volts}")
    # The compiler emits net names verbatim (no `vss` -> `0` magic), so the
    # fixture's return net needs its own explicit ground reference; without
    # it `vss` floats and the output shows feedthrough above the rail.
    lines.append(f"VSS {vss_net} 0 DC 0")
    lines.append(
        f"Vin {pulse_net} 0 DC 0 PULSE(0 {pulse_volts} 1n 1n 1n 10n 20n)"
    )
    lines.append(f".tran 0.1n {tstop_s}")
    lines.append(".end")
    return "\n".join(lines) + "\n"
