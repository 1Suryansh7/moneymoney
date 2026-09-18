"""DRC verdict parsing: KLayout report XML -> typed verdict (Stage 8).

Pure functions over the `drc.txt` report database the FEOL-enabled
sky130A deck emits — no KLayout, no database, no simulator. Rule names
arrive single-quoted (`'li.3'`, observed on EDA 2026-09-18: tap gap
0.30 um yields exactly two `li.3` edge-pair items); quotes are
stripped. Anything unparseable fails closed — a verdict is never
guessed. Magic `drc check` stdout parsing stays deferred until a
dirty-state fixture is observed (only "No errors found." is proven).
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass

from analog_ic_design.sim.ngspice import SimError


@dataclass(frozen=True)
class DrcVerdict:
    """Typed DRC verdict: clean flag, violation count, rules hit."""

    clean: bool
    violation_count: int
    rules: tuple[str, ...]


def parse_klayout_drc_xml(xml_text: str) -> DrcVerdict:
    """Parse a KLayout DRC report database into a `DrcVerdict`.

    Clean iff the `<items>` element holds zero `<item>` entries.
    `rules` dedupes the per-item `<category>` names in first-seen
    order. Malformed XML, a wrong root tag, or a missing `<items>`
    element raises `SimError` (Schema taxonomy).
    """
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        raise SimError(f"Schema: KLayout DRC report is not XML: {exc}") from exc
    if root.tag != "report-database":
        raise SimError("Schema: KLayout DRC report root must be report-database")
    items = root.find("items")
    if items is None:
        raise SimError("Schema: KLayout DRC report has no items element")
    rules: list[str] = []
    count = 0
    for item in items.findall("item"):
        count += 1
        rule = (item.findtext("category") or "").strip().strip("'\"")
        if rule and rule not in rules:
            rules.append(rule)
    return DrcVerdict(clean=count == 0, violation_count=count, rules=tuple(rules))
