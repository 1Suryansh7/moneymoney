"""R0-4a tests: EngineV01.measure for dc_gain/ac_gain on inverter cells.

The v1 Testbench Manager measures structural-allowlist cells only
(one nfet + one pfet, nets from {in, out, vdd, vss}); anything else
fails closed so no testbench is ever improvised. Both analyses run
and must agree within 10%; both Measurement rows persist in V/V.
Base proves every fail-closed path; EDA proves a live number.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from analog_ic_design.engine.engine_v01 import EngineV01, SimError
from analog_ic_design.sim.cs_amp import build_cs_amplifier
from analog_ic_design.sim.diff_pair import build_diff_pair
from analog_ic_design.sim.inverter import build_inverter
from analog_ic_design.sim.ngspice import libngspice_available
from analog_ic_design.store.schema import connect

NEEDS_LIB = pytest.mark.skipif(
    not libngspice_available(),
    reason="libngspice absent (base image); covered by CI eda job",
)


def _engine_with_inverter(tmp_path: Path) -> tuple[EngineV01, str]:
    db = str(tmp_path / "measure.sqlite")
    eng = EngineV01(db_path=db)
    setup = connect(db)
    try:
        cell = build_inverter(setup)
        setup.commit()
    finally:
        setup.close()
    return eng, cell


def _engine_with_cs(tmp_path: Path) -> tuple[EngineV01, str]:
    db = str(tmp_path / "measure_cs.sqlite")
    eng = EngineV01(db_path=db)
    setup = connect(db)
    try:
        cell = build_cs_amplifier(setup)
        setup.commit()
    finally:
        setup.close()
    return eng, cell


def _engine_with_diff(tmp_path: Path) -> tuple[EngineV01, str]:
    db = str(tmp_path / "measure_diff.sqlite")
    eng = EngineV01(db_path=db)
    setup = connect(db)
    try:
        cell = build_diff_pair(setup)
        setup.commit()
    finally:
        setup.close()
    return eng, cell


def test_unknown_metric_fails_closed(tmp_path: Path) -> None:
    eng = EngineV01(db_path=str(tmp_path / "m.sqlite"))
    try:
        with pytest.raises(ValueError, match="unknown metric_id"):
            eng.measure(cell_id="whatever", metric_id="gain")
    finally:
        eng.close()


def test_unregistered_structure_fails_closed(tmp_path: Path) -> None:
    eng = EngineV01(db_path=str(tmp_path / "m.sqlite"))
    try:
        pid = eng.create_project(name="p")
        cid = eng.create_cell(project_id=pid, cell_name="empty")
        with pytest.raises(ValueError, match="no testbench registered"):
            eng.measure(cell_id=cid, metric_id="dc_gain")
    finally:
        eng.close()


def test_measure_without_backend_reports_taxonomy(tmp_path: Path) -> None:
    if libngspice_available():
        pytest.skip("backend present; the taxonomy path is base-only")
    eng, cell = _engine_with_inverter(tmp_path)
    try:
        with pytest.raises(SimError, match="Schema: simulate requires libngspice"):
            eng.measure(cell_id=cell, metric_id="dc_gain")
    finally:
        eng.close()


@NEEDS_LIB
def test_live_inverter_gain_agrees_and_persists(tmp_path: Path) -> None:
    eng, cell = _engine_with_inverter(tmp_path)
    try:
        dc = eng.measure(cell_id=cell, metric_id="dc_gain")
        ac = eng.measure(cell_id=cell, metric_id="ac_gain")
        assert dc > 5.0
        assert ac > 5.0
        conn = sqlite3.connect(str(tmp_path / "measure.sqlite"))
        try:
            rows = conn.execute(
                "SELECT metric_id, value, units FROM measurement"
            ).fetchall()
        finally:
            conn.close()
        by_metric = {r[0]: (r[1], r[2]) for r in rows}
        assert set(by_metric) == {"dc_gain", "ac_gain"}
        assert by_metric["dc_gain"][1] == "V/V"
        assert by_metric["dc_gain"][0] == dc
        assert by_metric["ac_gain"][0] == ac
    finally:
        eng.close()


@NEEDS_LIB
def test_live_inverter_bandwidth_loaded(tmp_path: Path) -> None:
    """Under the declared 1 pF load the inverter rolls off in-range:
    MEASURED 56.9 MHz pre-commit (unloaded it honestly refuses at 6.5)."""
    eng, cell = _engine_with_inverter(tmp_path)
    try:
        ugbw = eng.measure(cell_id=cell, metric_id="bandwidth")
        assert 1.0e7 < ugbw < 1.0e9
        conn = sqlite3.connect(str(tmp_path / "measure.sqlite"))
        try:
            rows = conn.execute(
                "SELECT metric_id, units FROM measurement WHERE metric_id='bandwidth'"
            ).fetchall()
        finally:
            conn.close()
        assert rows and all(r[1] == "Hz" for r in rows)
    finally:
        eng.close()


@NEEDS_LIB
def test_live_cs_gain_agrees_and_persists(tmp_path: Path) -> None:
    """Common-source with the R0-3a bias recipe (0.9 V gate, 0.4-1.2 V
    sweep): DC == AC near 9.1 with rail-to-rail swing, both rows kept."""
    eng, cell = _engine_with_cs(tmp_path)
    try:
        dc = eng.measure(cell_id=cell, metric_id="dc_gain")
        ac = eng.measure(cell_id=cell, metric_id="ac_gain")
        assert 8.0 < dc < 10.0
        assert 8.0 < ac < 10.0
        conn = sqlite3.connect(str(tmp_path / "measure_cs.sqlite"))
        try:
            rows = conn.execute(
                "SELECT metric_id, value, units FROM measurement"
            ).fetchall()
        finally:
            conn.close()
        by_metric = {r[0]: (r[1], r[2]) for r in rows}
        assert set(by_metric) == {"dc_gain", "ac_gain"}
        assert by_metric["dc_gain"][0] == dc
    finally:
        eng.close()


@NEEDS_LIB
def test_live_cs_bandwidth_loaded(tmp_path: Path) -> None:
    """CS under 1 pF must reproduce the Stage 3 observation (2.07e7 Hz)
    through the engine path; the Stage 3 window (1e6-1e9) applies."""
    eng, cell = _engine_with_cs(tmp_path)
    try:
        ugbw = eng.measure(cell_id=cell, metric_id="bandwidth")
        assert 1.0e6 < ugbw < 1.0e9
    finally:
        eng.close()


def test_diff_without_backend_reports_taxonomy(tmp_path: Path) -> None:
    if libngspice_available():
        pytest.skip("backend present; the taxonomy path is base-only")
    eng, cell = _engine_with_diff(tmp_path)
    try:
        with pytest.raises(SimError, match="Schema: simulate requires libngspice"):
            eng.measure(cell_id=cell, metric_id="dc_gain")
    finally:
        eng.close()


@NEEDS_LIB
def test_live_diff_gain_agrees_split_holds_and_persists(tmp_path: Path) -> None:
    """Diff-pair with single-ended drive: DC slope == AC mirror-side gain
    near 8.1 with the diode side attenuated, both rows kept."""
    eng, cell = _engine_with_diff(tmp_path)
    try:
        dc = eng.measure(cell_id=cell, metric_id="dc_gain")
        ac = eng.measure(cell_id=cell, metric_id="ac_gain")
        assert 5.0 < dc < 15.0
        assert 5.0 < ac < 15.0
        conn = sqlite3.connect(str(tmp_path / "measure_diff.sqlite"))
        try:
            rows = conn.execute(
                "SELECT metric_id, value, units FROM measurement"
            ).fetchall()
        finally:
            conn.close()
        by_metric = {r[0]: (r[1], r[2]) for r in rows}
        assert set(by_metric) == {"dc_gain", "ac_gain"}
        assert by_metric["dc_gain"][0] == dc
    finally:
        eng.close()
