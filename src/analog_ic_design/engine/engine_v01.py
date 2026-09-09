"""EngineV01: concrete DesignEngine over existing modules (Stage 7A).

Strangler facade — pure delegation, zero logic moves. Every method below
calls one existing module entry point; no validation, compilation,
simulation, or storage logic lives here.

Surface note: the `DesignEngine` ABC freezes exactly 11 methods (pinned by
`tests/test_engine_api.py`; ENGINE_API_VERSION stays "0.1"). The four extra
methods here (`connect`, `measure`, `run_erc`, `run_lvs`) exist ONLY on this
concrete class as additive extensions. Deferred methods raise
`NotImplementedError` with a `[defer]` owner instead of faking behavior:
`measure` needs the R0 Testbench Manager, `check_constraints`/`compare` need
measurement orchestration, `optimize` needs spec-to-target mapping,
`run_drc`/`run_erc`/`run_lvs`/`extract` need Stage 8/9 backends.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path

from analog_ic_design.circuit.compiler import compile_netlist
from analog_ic_design.circuit.validator import validate as validate_cell
from analog_ic_design.engine.design_engine import DesignEngine
from analog_ic_design.sim.jobs import JobRunner
from analog_ic_design.sim.ngspice import SimError, libngspice_available
from analog_ic_design.store.schema import connect, migrate, new_id, utcnow_iso
from analog_ic_design.topology.templates import get_template, instantiate_template

_DEFAULT_LIB: str = "libngspice.so"
_DEFAULT_LIBRARY_NAME: str = "analog_lib"
_SIM_TIMEOUT_S: float = 300.0


class EngineV01(DesignEngine):
    """Single canonical entry point, bound to one migrated database file."""

    def __init__(self, *, db_path: str | Path) -> None:
        self._db_path = str(db_path)
        self._conn = connect(self._db_path)
        migrate(self._conn)
        self._lib_path = _DEFAULT_LIB
        self._runner: JobRunner | None = None

    def close(self) -> None:
        """Shut down workers and release the database connection."""
        if self._runner is not None:
            self._runner.shutdown()
            self._runner = None
        self._conn.close()

    def _require_cell(self, cell_id: str) -> tuple[str, str]:
        row = self._conn.execute(
            "SELECT cell.name, cell.library_id FROM cell WHERE cell.id = ?", (cell_id,)
        ).fetchone()
        if row is None:
            raise ValueError(f"Schema: unknown cell_id {cell_id!r}")
        return str(row[0]), str(row[1])

    def create_project(self, *, name: str) -> str:
        """Insert a project row; returns the project id."""
        if not name.strip():
            raise ValueError("Schema: project name must be non-empty")
        pid = new_id()
        self._conn.execute(
            "INSERT INTO project VALUES (?, ?, ?)", (pid, name, utcnow_iso())
        )
        self._conn.commit()
        return pid

    def create_cell(self, *, project_id: str, cell_name: str) -> str:
        """Insert a cell under the project's library (created if absent)."""
        exists = self._conn.execute(
            "SELECT id FROM project WHERE id = ?", (project_id,)
        ).fetchone()
        if exists is None:
            raise ValueError(f"Schema: unknown project_id {project_id!r}")
        if not cell_name.strip():
            raise ValueError("Schema: cell name must be non-empty")
        lib = self._conn.execute(
            "SELECT id FROM library WHERE project_id = ? AND name = ?",
            (project_id, _DEFAULT_LIBRARY_NAME),
        ).fetchone()
        lib_id = str(lib[0]) if lib is not None else new_id()
        if lib is None:
            self._conn.execute(
                "INSERT INTO library VALUES (?, ?, ?, ?)",
                (lib_id, project_id, _DEFAULT_LIBRARY_NAME, utcnow_iso()),
            )
        cell_id = new_id()
        self._conn.execute(
            "INSERT INTO cell VALUES (?, ?, ?, ?)",
            (cell_id, lib_id, cell_name, utcnow_iso()),
        )
        self._conn.commit()
        return cell_id

    def instantiate(
        self, *, cell_id: str, template_id: str, parameters: Mapping[str, float]
    ) -> str:
        """Validate the anchor cell + parameters, then run the template flow.

        Stage 6 templates create their own project/cell rows, so the return
        is the created cell id (not an instance row); the anchor `cell_id`
        is Schema-checked but not mutated.
        """
        self._require_cell(cell_id)
        template = get_template(template_id)
        merged = template.validate_parameters(dict(parameters))
        return instantiate_template(self._conn, template_id, params=merged)

    def validate(self, *, cell_id: str) -> tuple[bool, tuple[str, ...]]:
        """Run the pre-simulation gate; returns (valid, violation messages)."""
        self._require_cell(cell_id)
        report = validate_cell(self._conn, cell_id)
        return report.valid, tuple(v.message for v in report.violations)

    def netlist(self, *, cell_id: str) -> str:
        """Compile the cell to its deterministic SPICE netlist."""
        self._require_cell(cell_id)
        return compile_netlist(self._conn, cell_id)

    def connect(self, *, lib_path: str = _DEFAULT_LIB) -> str:
        """Bind the worker-runner to a simulator library; returns handle id."""
        self._lib_path = lib_path
        if self._runner is not None:
            self._runner.shutdown()
        self._runner = JobRunner(db_path=self._db_path, lib_path=lib_path)
        return "default"

    def simulate(self, *, netlist: str, seed: int) -> str:
        """Submit `netlist` to an isolated worker; returns reproducibility id."""
        if not libngspice_available():
            raise SimError(
                "Schema: simulate requires libngspice; "
                "no simulator backend on this image"
            )
        runner = self._runner or JobRunner(db_path=self._db_path, lib_path=self._lib_path)
        self._runner = runner
        job_id = runner.submit_simulation(netlist=netlist, seed=seed)
        try:
            result = runner.wait(job_id, timeout=_SIM_TIMEOUT_S)
        except TimeoutError as exc:
            raise SimError(
                f"SPICE convergence: job {job_id!r} still running "
                f"after {_SIM_TIMEOUT_S}s"
            ) from exc
        if result.status != "succeeded" or not result.result:
            raise SimError(str(result.error or "SPICE convergence: empty job verdict"))
        try:
            payload = json.loads(result.result)
            return str(payload["reproducibility_id"])
        except (ValueError, KeyError, TypeError) as exc:
            raise SimError(
                f"Schema: malformed worker payload for job {job_id!r}: {exc}"
            ) from exc

    def check_constraints(self, *, cell_id: str) -> tuple[bool, tuple[str, ...]]:
        """[defer R0] Needs measurement orchestration (Testbench Manager)."""
        raise NotImplementedError("check_constraints deferred to R0 Testbench Manager")

    def optimize(self, *, cell_id: str, spec_id: str) -> str:
        """[defer R0] Needs spec-to-target mapping over registered templates."""
        raise NotImplementedError("optimize deferred to R0 measurement orchestration")

    def run_drc(self, *, cell_name: str) -> tuple[bool, tuple[str, ...]]:
        """[defer Stage 8] Needs a LayoutBackend DRC adapter."""
        raise NotImplementedError("run_drc deferred to Stage 8 physical backends")

    def extract(self, *, cell_name: str) -> str:
        """[defer Stage 9] Needs a PEX extraction backend."""
        raise NotImplementedError("extract deferred to Stage 9 PEX loop")

    def compare(self, *, first_id: str, second_id: str, tolerance: float) -> bool:
        """[defer R0] Needs tolerance-aware netlist/float comparison."""
        raise NotImplementedError("compare deferred to R0 comparison policies")

    def measure(self, *, cell_id: str, metric_id: str) -> float:
        """[defer R0] Needs per-metric testbench selection + simulation."""
        raise NotImplementedError("measure deferred to R0 Testbench Manager")

    def run_erc(self, *, cell_name: str) -> tuple[bool, tuple[str, ...]]:
        """[defer Stage 8] Needs a LayoutBackend ERC adapter."""
        raise NotImplementedError("run_erc deferred to Stage 8 physical backends")

    def run_lvs(self, *, cell_name: str) -> tuple[bool, tuple[str, ...]]:
        """[defer Stage 8] Needs a LayoutBackend LVS adapter."""
        raise NotImplementedError("run_lvs deferred to Stage 8 physical backends")
