"""Stage 7A tests: EngineV01 strangler facade over existing modules.

Base suite covers project/cell creation, template instantiation, the
validation gate, deterministic netlists, fail-closed simulation without a
backend, and pinned NotImplementedError surfaces. Live simulation runs
under NEEDS_LIB (EDA only).
"""

from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

import pytest

from analog_ic_design.engine.design_engine import DesignEngine
from analog_ic_design.engine.engine_v01 import EngineV01
from analog_ic_design.sim.ngspice import SimError, libngspice_available

NEEDS_LIB = pytest.mark.skipif(
    not libngspice_available(),
    reason="libngspice absent (base image); covered by CI eda job",
)

RC_DECK = "\n".join(
    [
        "* rc probe",
        "V1 in 0 DC 0 PULSE(0 1.8 1n 1n 1n 10n 20n)",
        "R1 in out 1k",
        "C1 out 0 1p",
        ".tran 0.1n 30n",
        ".end",
        "",
    ]
)


@pytest.fixture()
def engine(tmp_path: Path) -> Generator[EngineV01, None, None]:
    eng = EngineV01(db_path=tmp_path / "engine.sqlite")
    yield eng
    eng.close()


def test_engine_v01_implements_abc_surface(engine: EngineV01) -> None:
    assert isinstance(engine, DesignEngine)
    assert engine.connect() == "default"


def test_create_project_and_cell_roundtrip(engine: EngineV01) -> None:
    pid = engine.create_project(name="p1")
    cid = engine.create_cell(project_id=pid, cell_name="c1")
    row = engine._conn.execute(
        "SELECT library.project_id FROM cell "
        "JOIN library ON library.id = cell.library_id WHERE cell.id = ?",
        (cid,),
    ).fetchone()
    assert row is not None and str(row[0]) == pid


def test_create_rejects_blank_and_unknown(engine: EngineV01) -> None:
    with pytest.raises(ValueError, match="Schema"):
        engine.create_project(name="  ")
    with pytest.raises(ValueError, match="Schema"):
        engine.create_cell(project_id="nope", cell_name="c")
    pid = engine.create_project(name="p")
    with pytest.raises(ValueError, match="Schema"):
        engine.create_cell(project_id=pid, cell_name="  ")


def test_instantiate_template_happy_path(engine: EngineV01) -> None:
    pid = engine.create_project(name="p")
    anchor = engine.create_cell(project_id=pid, cell_name="anchor")
    nid = engine.instantiate(cell_id=anchor, template_id="current_mirror", parameters={})
    valid, violations = engine.validate(cell_id=nid)
    assert valid is True
    assert violations == ()
    first = engine.netlist(cell_id=nid)
    assert engine.netlist(cell_id=nid) == first
    assert "nfet" in first


def test_instantiate_rejects_bad_input(engine: EngineV01) -> None:
    pid = engine.create_project(name="p")
    anchor = engine.create_cell(project_id=pid, cell_name="anchor")
    with pytest.raises(ValueError, match="Schema"):
        engine.instantiate(cell_id="nope", template_id="current_mirror", parameters={})
    with pytest.raises(ValueError, match="Schema"):
        engine.instantiate(cell_id=anchor, template_id="nope", parameters={})
    with pytest.raises(ValueError, match="Units"):
        engine.instantiate(
            cell_id=anchor, template_id="current_mirror", parameters={"w": -1.0}
        )
    with pytest.raises(ValueError, match="Schema"):
        engine.validate(cell_id="nope")
    with pytest.raises(ValueError, match="Schema"):
        engine.netlist(cell_id="nope")


def test_deferred_surfaces_raise(engine: EngineV01) -> None:
    pid = engine.create_project(name="p")
    cid = engine.create_cell(project_id=pid, cell_name="c")
    with pytest.raises(NotImplementedError):
        engine.check_constraints(cell_id=cid)
    with pytest.raises(NotImplementedError):
        engine.optimize(cell_id=cid, spec_id="s")
    with pytest.raises(NotImplementedError):
        engine.compare(first_id=cid, second_id=cid, tolerance=0.01)
    with pytest.raises(NotImplementedError):
        engine.run_drc(cell_name="c")
    with pytest.raises(NotImplementedError):
        engine.extract(cell_name="c")
    # R0-4a lifted the measure deferral: unknown metrics fail closed with
    # ValueError (Schema), not NotImplementedError. Full contract lives in
    # tests/test_measure.py.
    with pytest.raises(ValueError, match="Schema"):
        engine.measure(cell_id=cid, metric_id="gain")
    with pytest.raises(NotImplementedError):
        engine.run_erc(cell_name="c")
    with pytest.raises(NotImplementedError):
        engine.run_lvs(cell_name="c")


def test_simulate_fails_closed_on_garbage_netlist(tmp_path: Path) -> None:
    # Base: pre-check raises before spawning. EDA: backend rejects a deck
    # with no analysis. Both paths fail closed with SimError.
    eng = EngineV01(db_path=tmp_path / "e.sqlite")
    try:
        with pytest.raises(SimError):
            eng.simulate(netlist="* garbage\n.end\n", seed=0)
    finally:
        eng.close()


@NEEDS_LIB
def test_simulate_live_rc_deck(tmp_path: Path) -> None:
    eng = EngineV01(db_path=tmp_path / "live.sqlite")
    try:
        repro = eng.simulate(netlist=RC_DECK, seed=7)
        assert len(repro) == 64
        assert all(c in "0123456789abcdef" for c in repro)
    finally:
        eng.close()
