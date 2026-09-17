"""Parasitic extraction readout: parsed coupled capacitances (Stage 9).

Pure functions over Magic `ext2spice` text — no simulator, no database.
`per_net_capacitance` attributes every capacitor's FULL value to each of
its terminal nets: a conservative per-net budget (upper bound, documented
as such — shared caps count on both sides), monotone in geometry, which
is exactly what the scaling proof needs. SPICE engineering suffixes
(f/p/n/u/m/k/meg/g/t) parse explicitly; anything else fails closed.
"""

from __future__ import annotations

import math
import re
from typing import Final

from analog_ic_design.sim.ngspice import SimError

_SUFFIX_SCALE = {
    "f": 1e-15,
    "p": 1e-12,
    "n": 1e-9,
    "u": 1e-6,
    "m": 1e-3,
    "k": 1e3,
    "meg": 1e6,
    "g": 1e9,
    "t": 1e12,
}

_CAP_RE = re.compile(r"^C\S+\s+(\S+)\s+(\S+)\s+([0-9.eE+-]+)([A-Za-z]*)\s*$")

#: Magic lambda for sky130A, quoted by the `.option scale=5m` line Magic
#: ext2spice itself emits for this technology. Length-like extracted
#: parameters scale by it, area-like by its square.
MAGIC_LAMBDA_M: Final = 5e-9

_LENGTH_PARAMS = frozenset({"w", "l", "pd", "ps"})
_AREA_PARAMS = frozenset({"ad", "as"})
_PARAM_RE = re.compile(r"([A-Za-z]+)\=([0-9.eE+-]+)([A-Za-z]*)")


def to_schematic_subckt(ext_spice: str, *, subckt_name: str) -> str:
    """Wrap an extracted device block as an SI-unit schematic subckt.

    Converts lambda-unit geometry to SI meters (lengths × λ, areas ×
    λ²), drops the `.option scale` line (poison in an SI deck), keeps
    capacitor values untouched (already absolute Farads), and rewraps
    the device + caps under `subckt_name` with the extracted port nets.
    Only single-device blocks with X-lines fail closed otherwise —
    this is the PCell device path, not a general hierarchical importer.
    """
    if not subckt_name or not subckt_name.strip():
        raise SimError("Schema: subckt name must be non-empty")
    dev_lines: list[str] = []
    cap_lines: list[str] = []
    for raw in ext_spice.splitlines():
        line = raw.strip()
        if not line or line.startswith(("*", ".", "+")):
            continue
        if line.startswith("X"):
            dev_lines.append(line)
        elif line.startswith("C"):
            cap_lines.append(line)
    if len(dev_lines) != 1:
        raise SimError(
            f"Schema: PEX wrap needs exactly one device line, found {len(dev_lines)}"
        )

    def convert(match: re.Match[str]) -> str:
        name, number, suffix = match.group(1).lower(), float(match.group(2)), match.group(3)
        if suffix and suffix.lower() not in _SUFFIX_SCALE:
            raise SimError(f"Schema: unknown geometry suffix {suffix!r}")
        scale = _SUFFIX_SCALE.get(suffix.lower(), 1.0) if suffix else 1.0
        if name in _LENGTH_PARAMS:
            return f"{match.group(1)}={number * scale * MAGIC_LAMBDA_M!r}"
        if name in _AREA_PARAMS:
            return f"{match.group(1)}={number * scale * MAGIC_LAMBDA_M**2!r}"
        return match.group(0)

    tokens = dev_lines[0].split()
    nets = tokens[1:5]
    model = tokens[5]
    params = _PARAM_RE.sub(convert, " ".join(tokens[6:]))
    lines = [f".subckt {subckt_name} {' '.join(nets)}"]
    lines.append(f"{tokens[0]} {' '.join(nets)} {model} {params}".strip())
    lines.extend(cap_lines)
    lines.append(".ends")
    return "\n".join(lines) + "\n"


def parse_capacitance_farads(token: str) -> float:
    """Parse one SPICE value token to Farads (suffix-explicit, fail-closed)."""
    match = re.fullmatch(r"([0-9.eE+-]+)([A-Za-z]*)", token.strip())
    if match is None:
        raise SimError(f"Schema: unparsable capacitance token {token!r}")
    number, suffix = float(match.group(1)), match.group(2).lower()
    if suffix and suffix not in _SUFFIX_SCALE:
        raise SimError(f"Schema: unknown capacitance suffix {suffix!r}")
    value = number * _SUFFIX_SCALE.get(suffix, 1.0)
    if not math.isfinite(value) or value < 0.0:
        raise SimError(f"Schema: non-physical capacitance {token!r}")
    return value


def per_net_capacitance(ext_spice: str) -> dict[str, float]:
    """Total attached capacitance per net, in Farads.

    Every `Cxx n1 n2 value` line contributes its full value to BOTH
    terminal nets (conservative budget semantics — see module docstring).
    Lines that are not two-terminal capacitors (devices, options,
    comments) are ignored; a netlist with zero capacitors fails closed
    (a silent all-zero extraction is a broken bench, not a clean one).
    """
    totals: dict[str, float] = {}
    found = 0
    for raw in ext_spice.splitlines():
        line = raw.strip()
        if not line or line.startswith(("*", ".", "+")):
            continue
        match = _CAP_RE.match(line)
        if match is None:
            continue
        value = parse_capacitance_farads(match.group(3) + match.group(4))
        for net in (match.group(1), match.group(2)):
            totals[net] = totals.get(net, 0.0) + value
        found += 1
    if not found:
        raise SimError("Schema: extraction contains no capacitors")
    return totals


__all__ = [
    "MAGIC_LAMBDA_M",
    "parse_capacitance_farads",
    "per_net_capacitance",
    "to_schematic_subckt",
]
