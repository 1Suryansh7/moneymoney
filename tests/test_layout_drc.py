"""DRC verdict parser tests (base, no EDA tools).

Fixtures mirror the real `drc.txt` report databases observed on EDA
2026-09-18 (FEOL-enabled sky130A deck over the PCell NMOS OASIS):
clean has an empty `<items>` element; gap 0.30 um yields exactly two
`'li.3'` edge-pair items (values verbatim). Envelope trimmed to what
the parser reads (root tag + items); item blocks are untrimmed.
"""

from __future__ import annotations

import pytest

from analog_ic_design.layout.drc import DrcVerdict, parse_klayout_drc_xml
from analog_ic_design.sim.ngspice import SimError

_CLEAN_XML = """<?xml version="1.0" encoding="utf-8"?>
<report-database>
 <description>SKY130 DRC runset</description>
 <top-cell>pcell_nmos</top-cell>
 <categories>
  <category>
   <name>li.3</name>
   <description>li.3 : min. li spacing : 0.17um</description>
   <categories>
   </categories>
  </category>
 </categories>
 <items>
 </items>
</report-database>
"""

_DIRTY_XML = """<?xml version="1.0" encoding="utf-8"?>
<report-database>
 <description>SKY130 DRC runset</description>
 <top-cell>pcell_nmos</top-cell>
 <items>
  <item>
   <tags/>
   <category>'li.3'</category>
   <cell>pcell_nmos</cell>
   <visited>false</visited>
   <multiplicity>1</multiplicity>
   <comment/>
   <image/>
   <values>
    <value>edge-pair: (-0.185,-0.75;-0.095,-0.75)|(-0.175,-0.6;-0.265,-0.6)</value>
   </values>
  </item>
  <item>
   <tags/>
   <category>'li.3'</category>
   <cell>pcell_nmos</cell>
   <visited>false</visited>
   <multiplicity>1</multiplicity>
   <comment/>
   <image/>
   <values>
    <value>edge-pair: (0.095,-0.75;0.185,-0.75)|(0.265,-0.6;0.175,-0.6)</value>
   </values>
  </item>
 </items>
</report-database>
"""


def test_clean_report_parses_clean() -> None:
    verdict = parse_klayout_drc_xml(_CLEAN_XML)
    assert verdict == DrcVerdict(clean=True, violation_count=0, rules=())


def test_dirty_report_counts_and_strips_rule_quotes() -> None:
    verdict = parse_klayout_drc_xml(_DIRTY_XML)
    assert verdict.clean is False
    assert verdict.violation_count == 2
    assert verdict.rules == ("li.3",)


def test_malformed_xml_fails_closed() -> None:
    with pytest.raises(SimError, match="not XML"):
        parse_klayout_drc_xml("this is not xml <")


def test_wrong_root_fails_closed() -> None:
    with pytest.raises(SimError, match="report-database"):
        parse_klayout_drc_xml("<report><items></items></report>")


def test_missing_items_fails_closed() -> None:
    with pytest.raises(SimError, match="no items element"):
        parse_klayout_drc_xml("<report-database></report-database>")
