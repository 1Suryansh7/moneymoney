"""EngineV01: concrete DesignEngine over existing modules (Stage 7A).

Strangler facade — pure delegation, zero logic moves. Every method below
calls one existing module entry point; no validation, compilation,
simulation, or storage logic lives here.

Surface note: the `DesignEngine` ABC freezes exactly 11 methods (pinned by
`tests/test_engine_api.py`; ENGINE_API_VERSION stays "0.1"). The extra
methods here (`connect`, `measure`, `run_erc`, `run_lvs`, `list_jobs`,
`job_result`, `list_cells`, `schematic`) exist ONLY on this concrete class
as additive extensions. Deferred methods raise
`NotImplementedError` with a `[defer]` owner instead of faking behavior:
`measure` needs the R0 Testbench Manager, `check_constraints`/`compare` need
measurement orchestration, `optimize` needs spec-to-target mapping,
`run_drc`/`run_erc`/`run_lvs`/`extract` need Stage 8/9 backends.
"""

from __future__ import annotations

import json
import threading
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from analog_ic_design.ai.explainer import explain_failure
from analog_ic_design.ai.provider import MockProvider
from analog_ic_design.ai.residency import ProviderGuard
from analog_ic_design.ai.taxonomy import classify_failure
from analog_ic_design.circuit.compiler import compile_netlist
from analog_ic_design.circuit.validator import validate as validate_cell
from analog_ic_design.engine.design_engine import DesignEngine
from analog_ic_design.sim.inverter import build_inverter
from analog_ic_design.sim.jobs import JobRunner
from analog_ic_design.sim.ngspice import RawSim, SimError, libngspice_available
from analog_ic_design.sim.testbench import assemble_transient
from analog_ic_design.sim.waveform import parse_ac, parse_transient
from analog_ic_design.store.schema import connect, migrate, new_id, utcnow_iso
from analog_ic_design.topology.templates import get_template, instantiate_template

_DEFAULT_LIB: str = "libngspice.so"
_DEFAULT_LIBRARY_NAME: str = "analog_lib"
_SIM_TIMEOUT_S: float = 300.0
# Container PDK path. Debt note: this literal is copy-pasted across bench,
# examples, and tests (15 copies); normalizing them is out of scope here —
# this copy serves the demo-testbench path only.
_SKY130_LIB: str = "/usr/local/share/pdk/sky130A/libs.tech/ngspice/sky130.lib.spice"

# Demo testbenches the UI Run button may trigger. Single entry on purpose:
# each addition is its own commit with its own EDA proof. (Seed of the R0
# Testbench Manager; measure/check_constraints stay deferred.)
_DEMO_TESTBENCHES: tuple[str, ...] = ("inverter_tran",)

# Engine surface: the facade plus its error contract (callers import
# SimError here, never from the simulator backend directly).
__all__ = ["EngineV01", "SimError"]


class EngineV01(DesignEngine):
    """Single canonical entry point, bound to one migrated database file.

    Threading contract: HTTP servers call these methods from worker threads,
    so every database touch runs serialized behind an RLock over a
    `check_same_thread=False` connection. Worker-process isolation for
    simulation itself is unchanged. Limitation (documented, not hidden):
    one in-flight simulation per engine binding — concurrent API scheduling
    arrives with the R0 scheduler.
    """

    def __init__(self, *, db_path: str | Path) -> None:
        self._db_path = str(db_path)
        self._lock = threading.RLock()
        self._conn = connect(self._db_path, check_same_thread=False)
        migrate(self._conn)
        self._lib_path = _DEFAULT_LIB
        self._runner: JobRunner | None = None

    def close(self) -> None:
        """Shut down workers and release the database connection."""
        with self._lock:
            if self._runner is not None:
                self._runner.shutdown()
                self._runner = None
            self._conn.close()

    def _require_cell(self, cell_id: str) -> tuple[str, str]:
        with self._lock:
            row = self._conn.execute(
                "SELECT cell.name, cell.library_id FROM cell WHERE cell.id = ?",
                (cell_id,),
            ).fetchone()
        if row is None:
            raise ValueError(f"Schema: unknown cell_id {cell_id!r}")
        return str(row[0]), str(row[1])

    def create_project(self, *, name: str) -> str:
        """Insert a project row; returns the project id."""
        if not name.strip():
            raise ValueError("Schema: project name must be non-empty")
        pid = new_id()
        with self._lock:
            self._conn.execute(
                "INSERT INTO project VALUES (?, ?, ?)", (pid, name, utcnow_iso())
            )
            self._conn.commit()
        return pid

    def create_cell(self, *, project_id: str, cell_name: str) -> str:
        """Insert a cell under the project's library (created if absent)."""
        with self._lock:
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
        with self._lock:
            return instantiate_template(self._conn, template_id, params=merged)

    def validate(self, *, cell_id: str) -> tuple[bool, tuple[str, ...]]:
        """Run the pre-simulation gate; returns (valid, violation messages)."""
        self._require_cell(cell_id)
        with self._lock:
            report = validate_cell(self._conn, cell_id)
        return report.valid, tuple(v.message for v in report.violations)

    def netlist(self, *, cell_id: str) -> str:
        """Compile the cell to its deterministic SPICE netlist."""
        self._require_cell(cell_id)
        with self._lock:
            return compile_netlist(self._conn, cell_id)

    def connect(self, *, lib_path: str = _DEFAULT_LIB) -> str:
        """Bind the worker-runner to a simulator library; returns handle id."""
        with self._lock:
            self._lib_path = lib_path
            if self._runner is not None:
                self._runner.shutdown()
            self._runner = JobRunner(db_path=self._db_path, lib_path=lib_path)
        return "default"

    def list_jobs(self) -> list[dict[str, str]]:
        """Newest-first job ledger summaries for the Run Center (no payloads)."""
        with self._lock:
            rows = self._conn.execute(
                "SELECT id, kind, status, created_at, updated_at FROM job"
                " ORDER BY created_at DESC, id DESC"
            ).fetchall()
        return [
            {
                "job_id": str(row[0]),
                "kind": str(row[1]),
                "status": str(row[2]),
                "created_at": str(row[3]),
                "updated_at": str(row[4]),
            }
            for row in rows
        ]

    def job_result(self, *, job_id: str) -> dict[str, str | None]:
        """Full ledger row for one job, result payload included when present."""
        with self._lock:
            row = self._conn.execute(
                "SELECT id, kind, status, result, error, created_at, updated_at"
                " FROM job WHERE id = ?",
                (job_id,),
            ).fetchone()
        if row is None:
            raise KeyError(f"unknown job {job_id!r}")
        return {
            "job_id": str(row[0]),
            "kind": str(row[1]),
            "status": str(row[2]),
            "result": None if row[3] is None else str(row[3]),
            "error": None if row[4] is None else str(row[4]),
            "created_at": str(row[5]),
            "updated_at": str(row[6]),
        }

    def job_waveforms(self, *, job_id: str) -> dict[str, Any]:
        """Render-ready vectors for one succeeded job (PlotPane wire format).

        Transient jobs yield SI time + per-trace SI samples with unit
        symbols; AC jobs yield SI frequency + magnitude_db/phase_deg per
        trace (wrapped phase, exactly as the parser returns — unwrapping
        is a metric concern, not a display one). Unknown jobs fail closed
        via job_result (KeyError); non-succeeded jobs surface the stored
        taxonomy error verbatim instead of inventing vectors.
        """
        row = self.job_result(job_id=job_id)
        if row["status"] != "succeeded" or not row["result"]:
            stored = row["error"] or f"Schema: job {job_id!r} is {row['status']!r}"
            raise SimError(str(stored))
        try:
            payload = json.loads(str(row["result"]))
            vectors = {k: [float(v) for v in vals]
                       for k, vals in payload["vectors"].items()}
            complex_vectors = {k: [complex(p[0], p[1]) for p in vals]
                               for k, vals in payload.get("complex_vectors", {}).items()}
        except (ValueError, KeyError, TypeError, IndexError) as exc:
            raise SimError(
                f"Schema: malformed ledger payload for job {job_id!r}: {exc}"
            ) from exc
        raw = RawSim(vectors=vectors, complex_vectors=complex_vectors, log="")
        if complex_vectors:
            wave = parse_ac(raw)
            return {
                "job_id": job_id,
                "analysis": "ac",
                "x_name": "frequency",
                "x_unit": "Hz",
                "x": [float(f) for f in wave.frequency],
                "traces": [
                    {
                        "name": t.name,
                        "unit": None,
                        "y": None,
                        "magnitude_db": list(t.magnitude_db()),
                        "phase_deg": list(t.phase_deg()),
                    }
                    for t in wave.traces
                ],
            }
        wave_t = parse_transient(raw)
        return {
            "job_id": job_id,
            "analysis": "tran",
            "x_name": "time",
            "x_unit": "s",
            "x": [float(t) for t in wave_t.time],
            "traces": [
                {
                    "name": t.name,
                    "unit": t.values[0].symbol if t.values else "V",
                    "y": [float(v) for v in t.values],
                    "magnitude_db": None,
                    "phase_deg": None,
                }
                for t in wave_t.traces
            ],
        }

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

    def list_cells(self) -> list[dict[str, str]]:
        """All cells across libraries for the design browser (no payloads)."""
        with self._lock:
            rows = self._conn.execute(
                "SELECT cell.id, cell.name, library.name FROM cell"
                " JOIN library ON library.id = cell.library_id"
                " ORDER BY library.name, cell.name, cell.id"
            ).fetchall()
        return [
            {"cell_id": str(row[0]), "cell_name": str(row[1]),
             "library_name": str(row[2])}
            for row in rows
        ]

    def schematic(self, *, cell_id: str) -> dict[str, Any]:
        """Serialize one cell for schematic rendering.

        Instances carry their symbol name plus SI parameter floats;
        ports resolve to net names (cell-level ports have no instance).
        Unknown cells fail closed via _require_cell (Schema).
        """
        cell_name, _ = self._require_cell(cell_id)
        with self._lock:
            inst_rows = self._conn.execute(
                "SELECT instance.id, instance.name, symbol.name FROM instance"
                " JOIN symbol ON symbol.id = instance.symbol_id"
                " WHERE instance.cell_id = ? ORDER BY instance.name, instance.id",
                (cell_id,),
            ).fetchall()
            param_rows = self._conn.execute(
                "SELECT parameter.instance_id, parameter.name, parameter.value"
                " FROM parameter JOIN instance ON instance.id = parameter.instance_id"
                " WHERE instance.cell_id = ?",
                (cell_id,),
            ).fetchall()
            net_rows = self._conn.execute(
                "SELECT id, name FROM net WHERE cell_id = ? ORDER BY name, id",
                (cell_id,),
            ).fetchall()
            port_rows = self._conn.execute(
                "SELECT port.name, port.net_id, instance.name FROM port"
                " LEFT JOIN instance ON instance.id = port.instance_id"
                " LEFT JOIN net ON net.id = port.net_id"
                " WHERE port.cell_id = ? OR instance.cell_id = ?"
                " ORDER BY port.name",
                (cell_id, cell_id),
            ).fetchall()
        nets = {str(row[0]): str(row[1]) for row in net_rows}
        params: dict[str, dict[str, float]] = {}
        for iid, pname, value in param_rows:
            params.setdefault(str(iid), {})[str(pname)] = float(value)
        instances: list[dict[str, Any]] = [
            {
                "instance_id": str(row[0]),
                "instance_name": str(row[1]),
                "symbol_name": str(row[2]),
                "parameters": params.get(str(row[0]), {}),
            }
            for row in inst_rows
        ]
        ports: list[dict[str, Any]] = [
            {
                "port_name": str(row[0]),
                "net_name": nets.get(str(row[1]), "") if row[1] is not None else "",
                "instance_name": None if row[2] is None else str(row[2]),
            }
            for row in port_rows
        ]
        return {
            "cell_id": cell_id,
            "cell_name": cell_name,
            "instances": instances,
            "nets": sorted(nets.values()),
            "ports": ports,
        }

    def explain_job(self, *, job_id: str) -> dict[str, Any]:
        """Grounded copilot explanation for one failed job (mock model only).

        The HTTP service serves deterministic MockProvider explanations:
        hosted models stay out until a human opt-in flow exists (residency
        law §9.4). Classification runs on the stored taxonomy-prefixed
        error with the job itself as evidence; succeeded/pending jobs and
        unclassifiable errors fail closed. The AIAction row is written by
        the explainer before anything returns (provenance law §9.3).
        """
        row = self.job_result(job_id=job_id)
        if row["status"] != "failed" or not row["error"]:
            raise ValueError(
                f"Schema: job {job_id!r} is {row['status']!r}; nothing to explain"
            )
        stored = str(row["error"]).splitlines()[0]
        message = stored[len("SimError: "):] if stored.startswith("SimError: ") else stored
        classification = classify_failure(message=message, evidence=(job_id,))
        provider = MockProvider(
            default_reply=(
                f"Mock analysis of {job_id}: classified [{classification.category}]"
                f" via {classification.trigger}; recorded ledger text stands —"
                " connect a hosted model for prose."
            )
        )
        with self._lock:
            explanation = explain_failure(
                self._conn,
                classification=classification,
                provider=provider,
                guard=ProviderGuard(),
            )
        return {
            "job_id": job_id,
            "category": classification.category,
            "trigger": classification.trigger,
            "prose": explanation.prose,
            "cited_ids": list(explanation.cited_ids),
            "action_id": explanation.action_id,
            "provider": provider.provider_name,
            "model": provider.model_name,
        }

    def run_demo_testbench(self, *, name: str, seed: int = 21) -> dict[str, str]:
        """Build, validate, netlist, and simulate one canonical demo deck.

        The deck is assembled server-side from the Stage 2 fixture, so the
        frontend never authors netlists: it sends a name and polls the
        returned job. Unknown names fail closed (Schema); simulator faults
        surface as SimError with taxonomy wording.
        """
        if name not in _DEMO_TESTBENCHES:
            raise ValueError(f"Schema: unknown demo testbench {name!r}")
        with self._lock:
            cell_id = build_inverter(self._conn)
            report = validate_cell(self._conn, cell_id)
            if not report.valid:
                raise ValueError(
                    "Schema: demo fixture failed validation: "
                    + "; ".join(v.message for v in report.violations)
                )
            fragment = compile_netlist(self._conn, cell_id)
        deck = assemble_transient(
            fragment, tstop_s=30e-9, libs=[(_SKY130_LIB, "tt")]
        )
        reproducibility_id = self.simulate(netlist=deck, seed=seed)
        jobs = self.list_jobs()
        if not jobs:
            raise SimError(f"SPICE convergence: no ledger row after demo {name!r}")
        return {
            "job_id": jobs[0]["job_id"],
            "cell_id": cell_id,
            "reproducibility_id": reproducibility_id,
        }

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
