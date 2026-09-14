"""EngineV01: concrete DesignEngine over existing modules (Stage 7A).

Strangler facade — pure delegation, zero logic moves. Every method below
calls one existing module entry point; no validation, compilation,
simulation, or storage logic lives here.

Surface note: the `DesignEngine` ABC freezes exactly 11 methods (pinned by
`tests/test_engine_api.py`; ENGINE_API_VERSION stays "0.1"). The extra
methods here (`connect`, `measure`, `run_erc`, `run_lvs`, `list_jobs`,
`job_result`, `list_cells`, `schematic`, `job_waveforms`, `explain_job`,
`run_demo_testbench`, `rename_cell`, `measure_with_unit`, `submit_study`,
`cancel_job`, `list_trials`)
exist ONLY on this concrete class as additive extensions. Deferred methods
raise `NotImplementedError` with a `[defer]` owner instead of faking
behavior: `check_constraints`/`compare` need measurement orchestration,
`optimize` needs spec-to-target mapping,
`run_drc`/`run_erc`/`run_lvs`/`extract` need Stage 8/9 backends.
`measure` is implemented for dc_gain/ac_gain on inverter-shape cells;
every other metric_id fails closed until its testbench lands.
"""

from __future__ import annotations

import json
import multiprocessing as mp
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
from analog_ic_design.metrics.bandwidth import extract_bandwidth
from analog_ic_design.metrics.contract import METRIC_BY_ID
from analog_ic_design.metrics.gain import extract_ac_gain, extract_dc_gain
from analog_ic_design.optimize.scalarizer import TIMEOUT_PENALTY
from analog_ic_design.sim.inverter import build_inverter
from analog_ic_design.sim.jobs import JobRunner
from analog_ic_design.sim.ngspice import RawSim, SimError, libngspice_available
from analog_ic_design.sim.study import (
    OBJECTIVES,
    ORPHAN_AFTER_S,
    SPEC_OBJECTIVE,
    STUDY_KIND,
    _study_worker,
    load_spec_rules,
)
from analog_ic_design.sim.testbench import assemble_ac, assemble_dc_sweep, assemble_transient
from analog_ic_design.sim.waveform import ACWaveform, parse_ac, parse_transient
from analog_ic_design.store.schema import connect, migrate, new_id, utcnow_iso
from analog_ic_design.topology.templates import get_template, instantiate_template

_DEFAULT_LIB: str = "libngspice.so"
_DEFAULT_LIBRARY_NAME: str = "analog_lib"
_SIM_TIMEOUT_S: float = 300.0
# Fixed seed for measure() runs; recorded in each job payload row.
_MEASURE_SEED: int = 21
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


def _load_raw(result: str, job_id: str) -> RawSim:
    """Rebuild a RawSim from a stored ledger payload (complex pairs → complex)."""
    try:
        payload = json.loads(result)
        vectors = {k: [float(v) for v in vals]
                   for k, vals in payload["vectors"].items()}
        complex_vectors = {k: [complex(p[0], p[1]) for p in vals]
                           for k, vals in payload.get("complex_vectors", {}).items()}
    except (ValueError, KeyError, TypeError, IndexError) as exc:
        raise SimError(
            f"Schema: malformed ledger payload for job {job_id!r}: {exc}"
        ) from exc
    return RawSim(vectors=vectors, complex_vectors=complex_vectors, log="")


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
        self._reconcile_orphaned_studies()
        self._lib_path = _DEFAULT_LIB
        self._runner: JobRunner | None = None
        self._study_live: dict[str, mp.process.BaseProcess] = {}

    def _reconcile_orphaned_studies(self) -> None:
        """Fail jobs no live process can still own (boot after crash/restart).

        Only optimize jobs silent longer than ORPHAN_AFTER_S: live studies
        heartbeat every trial, so silence implies death. Timestamps compare
        in Python — ledger ISO text and SQLite datetime() text do not share
        a lexicographic order. Sim-job orphans are a known limitation
        (status quo, not a regression).
        """
        from datetime import UTC, datetime, timedelta

        cutoff = datetime.now(UTC) - timedelta(seconds=ORPHAN_AFTER_S)
        with self._lock:
            rows = self._conn.execute(
                "SELECT id, updated_at FROM job WHERE kind = ?"
                " AND status IN ('pending', 'running')",
                (STUDY_KIND,),
            ).fetchall()
            orphans = []
            for row in rows:
                try:
                    if datetime.fromisoformat(str(row[1])) < cutoff:
                        orphans.append(str(row[0]))
                except ValueError:
                    orphans.append(str(row[0]))
            for job_id in orphans:
                self._conn.execute(
                    "UPDATE job SET status = 'failed',"
                    " error = 'Schema: engine restarted with study running,"
                    " verdict unknown; resubmit', updated_at = ? WHERE id = ?",
                    (utcnow_iso(), job_id),
                )
            self._conn.commit()

    def close(self) -> None:
        """Shut down workers and release the database connection."""
        with self._lock:
            live = list(self._study_live)
        for job_id in live:
            try:
                self.cancel_job(job_id=job_id)
            except KeyError:
                continue
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
        raw = _load_raw(str(row["result"]), job_id)
        if raw.complex_vectors:
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

    def rename_cell(self, *, cell_id: str, cell_name: str) -> dict[str, str]:
        """Rename one cell (template instantiation names callers can't pick)."""
        if not cell_name.strip():
            raise ValueError("Schema: cell name must be non-empty")
        self._require_cell(cell_id)
        with self._lock:
            self._conn.execute(
                "UPDATE cell SET name = ? WHERE id = ?", (cell_name, cell_id)
            )
            self._conn.commit()
        return {"cell_id": cell_id, "cell_name": cell_name}

    def create_spec(
        self,
        *,
        cell_id: str,
        name: str,
        rules: list[dict[str, object]],
    ) -> dict[str, str]:
        """Author a specification with constraint rules (study targets).

        Each rule needs metric/operator/threshold; metric must be a
        canonical contract id, operator one of >=, <=, =. Tolerance and
        priority default to 0.0/0; weight stays null (unweighted). The
        study submitter narrows to measured, multi-metric specs.
        """
        self._require_cell(cell_id)
        if not name.strip():
            raise ValueError("Schema: spec name must be non-empty")
        parsed: list[tuple[str, str, float, float, int]] = []
        for index, rule in enumerate(rules):
            metric = rule.get("metric")
            operator = rule.get("operator")
            threshold = rule.get("threshold")
            if metric not in METRIC_BY_ID:
                raise ValueError(
                    f"Schema: rule {index} references unknown metric {metric!r}"
                )
            if operator not in (">=", "<=", "="):
                raise ValueError(
                    f"Schema: rule {index} has bad operator {operator!r}"
                )
            if isinstance(threshold, bool) or not isinstance(
                threshold, (int, float)
            ):
                raise ValueError(
                    f"Schema: rule {index} threshold must be numeric"
                )
            tolerance = rule.get("tolerance", 0.0)
            priority = rule.get("priority", 0)
            if not isinstance(tolerance, (int, float)) or isinstance(
                tolerance, bool
            ):
                raise ValueError(
                    f"Schema: rule {index} tolerance must be numeric"
                )
            if not isinstance(priority, int) or isinstance(priority, bool):
                raise ValueError(
                    f"Schema: rule {index} priority must be an int"
                )
            parsed.append((
                str(metric), str(operator), float(threshold),
                float(tolerance), int(priority),
            ))
        if not parsed:
            raise ValueError("Schema: spec defines no rules")
        spec_id = new_id()
        with self._lock:
            self._conn.execute(
                "INSERT INTO specification VALUES (?, ?, ?, ?)",
                (spec_id, cell_id, name, utcnow_iso()),
            )
            for index, (metric, operator, threshold, tolerance, priority) in enumerate(
                parsed
            ):
                self._conn.execute(
                    "INSERT INTO constraint_rule VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        new_id(), spec_id, "hard", metric, operator,
                        threshold, tolerance, priority, None, utcnow_iso(),
                    ),
                )
            self._conn.commit()
        return {"spec_id": spec_id}

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

    def cancel_job(self, *, job_id: str) -> dict[str, str]:
        """Terminate a live study or sim worker; settled jobs keep status.

        Study processes die by terminate/kill (their daemon sim workers
        die with them — no orphans by construction). Sim jobs cancel
        through this binding's runner when it owns them; other bindings'
        live sims are returned as-is (best-effort, documented). Unknown
        ids fail closed (KeyError).
        """
        with self._lock:
            proc = self._study_live.get(job_id)
            if proc is not None:
                if proc.is_alive():
                    proc.terminate()
                    proc.join(10)
                    if proc.is_alive():
                        proc.kill()
                        proc.join(10)
                    self._conn.execute(
                        "UPDATE job SET status = 'cancelled', updated_at = ?"
                        " WHERE id = ?",
                        (utcnow_iso(), job_id),
                    )
                    self._conn.commit()
                del self._study_live[job_id]
                row = self._conn.execute(
                    "SELECT status FROM job WHERE id = ?", (job_id,)
                ).fetchone()
                if row is None:
                    raise KeyError(f"unknown job {job_id!r}")
                return {"job_id": job_id, "status": str(row[0])}
        if self._runner is not None:
            return {"job_id": job_id, "status": self._runner.cancel(job_id)}
        row = self.job_result(job_id=job_id)
        return {"job_id": job_id, "status": str(row["status"])}

    def submit_study(
        self,
        *,
        template_id: str,
        spec_id: str,
        space: Mapping[str, list[float]],
        seed: int,
        max_trials: int = 15,
        trial_timeout_s: float = 300.0,
        study_timeout_s: float | None = None,
        objective: str = SPEC_OBJECTIVE,
    ) -> dict[str, str]:
        """Validate a study fail-fast, enqueue it, return handles in ms.

        Never waits, simulates, or touches Optuna: the supervisor process
        does that. Rejections (ValueError): unknown template/spec,
        spec without rules, rules on unmeasured metrics, single-metric
        specs (degenerate objectives), non-positive space bounds,
        max_trials outside 1..30, non-positive timeouts/seed, bad
        objective.         PDK-minima enforcement stays per-trial (validator
        fails out-of-limit suggestions closed, visible in telemetry).
        """
        template = get_template(template_id)
        template.validate_parameters({})
        if isinstance(seed, bool) or not isinstance(seed, int):
            raise ValueError(f"Schema: study seed must be an int, got {seed!r}")
        bounds: dict[str, list[float]] = {}
        defaults = template.validate_parameters({})
        for name, edges in space.items():
            if name not in defaults:
                raise ValueError(
                    f"Schema: unknown parameter {name!r} for template {template_id!r}"
                )
            if len(edges) != 2:
                raise ValueError(
                    f"Schema: space bound {name!r} needs [low, high], got {edges!r}"
                )
            low, high = float(edges[0]), float(edges[1])
            if not (low > 0.0 and high > low):
                raise ValueError(
                    f"Schema: space bound {name!r} must satisfy 0 < low < high"
                )
            bounds[name] = [low, high]
        if not bounds:
            raise ValueError("Schema: study space defines no parameters")
        if not isinstance(max_trials, int) or isinstance(max_trials, bool):
            raise ValueError(f"Schema: max_trials must be an int, got {max_trials!r}")
        if not 1 <= max_trials <= 30:
            raise ValueError(
                f"Schema: max_trials {max_trials!r} outside browser ceiling 1..30"
            )
        if not trial_timeout_s > 0.0:
            raise ValueError("Schema: trial_timeout_s must be positive")
        if study_timeout_s is None:
            study_timeout_s = float(max_trials) * float(trial_timeout_s)
        if not study_timeout_s > 0.0:
            raise ValueError("Schema: study_timeout_s must be positive")
        if objective not in OBJECTIVES:
            raise ValueError(
                f"Schema: unknown objective {objective!r} (want one of {OBJECTIVES})"
            )
        with self._lock:
            spec = self._conn.execute(
                "SELECT id FROM specification WHERE id = ?", (spec_id,)
            ).fetchone()
            if spec is None:
                raise ValueError(f"Schema: unknown spec_id {spec_id!r}")
            rules = load_spec_rules(self._conn, spec_id)
            if not rules:
                raise ValueError(f"Schema: spec {spec_id!r} defines no rules")
            measured = {"dc_gain", "ac_gain", "bandwidth"}
            have = {metric for metric, _, _ in rules}
            if not have <= measured:
                raise ValueError(
                    f"Schema: spec {spec_id!r} rules reference unmeasured metrics"
                    f" {sorted(have - measured)}"
                )
            if len(have) < 2:
                raise ValueError(
                    f"Schema: single-metric studies rejected (degenerate objectives);"
                    f" spec {spec_id!r} covers only {sorted(have)}"
                )
            study_id = new_id()
            job_id = new_id()
            payload = json.dumps({
                "study_id": study_id, "template_id": template_id,
                "spec_id": spec_id, "space": bounds, "seed": seed,
                "max_trials": max_trials, "trial_timeout_s": trial_timeout_s,
                "study_timeout_s": study_timeout_s, "objective": objective,
            }, sort_keys=True)
            self._conn.execute(
                "INSERT INTO job (id, kind, status, payload, result, error,"
                " created_at, updated_at) VALUES (?, ?, 'pending', ?, NULL, NULL, ?, ?)",
                (job_id, STUDY_KIND, payload, utcnow_iso(), utcnow_iso()),
            )
            self._conn.commit()
            ctx = mp.get_context("spawn")
            proc = ctx.Process(
                target=_study_worker,
                args=(self._db_path, job_id, study_id, template_id, spec_id,
                      bounds, seed, max_trials, float(trial_timeout_s),
                      float(study_timeout_s), objective),
                daemon=False,
            )
            proc.start()
            self._study_live[job_id] = proc
        return {"job_id": job_id, "study_id": study_id}

    def list_trials(self, *, study_id: str) -> list[dict[str, object]]:
        """Trial telemetry for one study with recomputed scores (no stored column)."""
        from analog_ic_design.optimize.ledger import list_experiments
        from analog_ic_design.optimize.scalarizer import score_trial

        with self._lock:
            found = None
            for row in self._conn.execute(
                "SELECT id, payload FROM job WHERE kind = ?", (STUDY_KIND,)
            ).fetchall():
                try:
                    payload = json.loads(str(row[1]))
                except ValueError:
                    continue
                if payload.get("study_id") == study_id:
                    found = payload
                    break
            if found is None:
                raise KeyError(f"unknown study {study_id!r}")
            rules = load_spec_rules(self._conn, str(found["spec_id"]))
            trials = list_experiments(self._conn, study_id)
        out = []
        for trial in trials:
            try:
                score = score_trial(trial.metrics, rules)
            except ValueError:
                score = TIMEOUT_PENALTY
            out.append({
                "trial": trial.trial,
                "status": trial.status,
                "parameters": trial.parameters,
                "metrics": trial.metrics,
                "verdict": trial.verdict,
                "score": score,
                "reproducibility_id": trial.reproducibility_id,
            })
        return out

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

    def _transfer_gain(
        self,
        fragment: str,
        cell_id: str,
        *,
        extra_lines: list[str],
        v_start: float,
        v_stop: float,
        sweep_net: str = "in",
        ac_in: str = "in",
        ac_out: str = "out",
        ac_extra_lines: list[str] | None = None,
    ) -> tuple[float, float, float, ACWaveform, str, str]:
        """DC sweep trip discovery plus AC at trip; returns gains, trip, wave, jobs.

        The DC deck stays exactly the proven bias recipe; the AC deck
        takes its own extras so a declared load capacitance can attach
        for bandwidth without perturbing the operating point.
        """
        libs = [(_SKY130_LIB, "tt")]
        self.simulate(
            netlist=assemble_dc_sweep(
                fragment, sweep_net=sweep_net, v_start=v_start, v_stop=v_stop,
                v_step=0.005, extra_lines=extra_lines, libs=libs,
            ),
            seed=_MEASURE_SEED,
        )
        dc_job = self.list_jobs()[0]["job_id"]
        dc_row = self.job_result(job_id=dc_job)
        try:
            dc_raw = _load_raw(str(dc_row["result"]), dc_job)
            vin = [float(v) for v in dc_raw.vectors[sweep_net]]
            vout = [float(v) for v in dc_raw.vectors[ac_out]]
            dc_gain = extract_dc_gain(vin, vout)
            slopes = [abs((vout[i + 1] - vout[i]) / (vin[i + 1] - vin[i]))
                      for i in range(len(vin) - 1)]
            trip = vin[slopes.index(max(slopes))]
        except (KeyError, IndexError, ZeroDivisionError) as exc:
            raise SimError(
                f"SPICE convergence: unusable DC transfer for cell {cell_id!r}: {exc}"
            ) from exc
        self.simulate(
            netlist=assemble_ac(
                fragment, in_net=ac_in, v_bias=trip,
                extra_lines=ac_extra_lines if ac_extra_lines is not None else extra_lines,
                libs=libs,
            ),
            seed=_MEASURE_SEED,
        )
        ac_job = self.list_jobs()[0]["job_id"]
        ac_row = self.job_result(job_id=ac_job)
        try:
            ac_wave = parse_ac(_load_raw(str(ac_row["result"]), ac_job))
            ac_gain = extract_ac_gain(ac_wave, in_node=ac_in, out_node=ac_out)
        except KeyError as exc:
            raise SimError(
                f"SPICE convergence: missing AC trace for cell {cell_id!r}: {exc}"
            ) from exc
        return dc_gain, ac_gain, trip, ac_wave, dc_job, ac_job

    def measure(self, *, cell_id: str, metric_id: str) -> float:
        """Measure one metric on registered cell structures (R0 Testbench Manager).

        Supported metric_ids: dc_gain, ac_gain, bandwidth. Structural
        allowlist (each earned with its own EDA proof):
        - inverter: one nfet_01v8 + one pfet_01v8, nets ⊆ {in,out,vdd,vss};
          full-rail sweep, no bias assumptions.
        - common_source: same pair plus a vbias net; fixed 0.9 V PMOS-gate
          bias (R0-3a recipe) with the 0.4-1.2 V sweep that avoids the
          M1-off trap below and rail parking above.
        - diff_pair: three nfet + two pfet with the eight-net mirror-load
          structure; single-ended 0.7-1.1 V sweep on inp (inn/vbias fixed
          0.9 V, R0-2b recipe) with the mirror/diode split as second anchor.
        Anything else fails closed. Gain needs DC/AC agreement within 10%
        (single-analysis gain lies, observed live in R0-3b); both gain rows
        persist. Bandwidth reads the same in-memory AC sweep — zero extra
        sims — with the Stage 3 declared 1 pF load attached, and fails
        closed per contract when even the loaded stimulus holds no unity
        crossing.
        """
        if metric_id not in ("dc_gain", "ac_gain", "bandwidth"):
            raise ValueError(
                "Schema: unknown metric_id"
                f" {metric_id!r} (measured: dc_gain, ac_gain, bandwidth)"
            )
        self._require_cell(cell_id)
        with self._lock:
            syms = sorted(
                str(r[0])
                for r in self._conn.execute(
                    "SELECT symbol.name FROM instance"
                    " JOIN symbol ON symbol.id = instance.symbol_id"
                    " WHERE instance.cell_id = ?",
                    (cell_id,),
                ).fetchall()
            )
            nets = {
                str(r[0])
                for r in self._conn.execute(
                    "SELECT name FROM net WHERE cell_id = ?", (cell_id,)
                ).fetchall()
            }
        # Shape dispatch: each branch binds deck bias knowledge earned with
        # its own EDA proof. split_limit names a second output that must
        # stay attenuated (differential-split trust anchor). AC extras carry
        # the declared 1 pF load (Stage 3 precedent) for bandwidth; the DC
        # deck stays exactly the proven bias recipe.
        split_limit: tuple[str, float] | None
        load = ["Cload out 0 1p"]
        if syms == ["nfet_01v8", "pfet_01v8"] and nets == {"in", "out", "vbias", "vdd", "vss"}:
            extra, v_start, v_stop = ["Vbias vbias 0 DC 0.9"], 0.4, 1.2
            sweep_net, ac_in, ac_out, split_limit = "in", "in", "out", None
            ac_extra = ["Vbias vbias 0 DC 0.9"] + load
        elif (
            syms == ["nfet_01v8", "pfet_01v8"]
            and "in" in nets
            and "out" in nets
            and nets <= {"in", "out", "vdd", "vss"}
        ):
            extra, v_start, v_stop = [], 0.0, 1.8
            sweep_net, ac_in, ac_out, split_limit = "in", "in", "out", None
            ac_extra = load
        elif (
            syms == ["nfet_01v8"] * 3 + ["pfet_01v8"] * 2
            and nets == {"inp", "inn", "outp", "outn", "tail", "vbias", "vdd", "vss"}
        ):
            extra = ["Vinn inn 0 DC 0.9", "Vbias vbias 0 DC 0.9"]
            v_start, v_stop = 0.7, 1.1
            sweep_net, ac_in, ac_out = "inp", "inp", "outn"
            split_limit = ("outp", 2.0)
            ac_extra = extra
        else:
            raise ValueError(
                f"Schema: no testbench registered for cell {cell_id!r}"
                f" (symbols={syms}, nets={sorted(nets)})"
            )
        valid, violations = self.validate(cell_id=cell_id)
        if not valid:
            raise ValueError(
                f"Schema: measure refused on invalid cell {cell_id!r}: {violations}"
            )
        fragment = self.netlist(cell_id=cell_id)
        dc_gain, ac_gain, _trip, ac_wave, dc_job, ac_job = self._transfer_gain(
            fragment, cell_id, extra_lines=extra, v_start=v_start,
            v_stop=v_stop, sweep_net=sweep_net, ac_in=ac_in, ac_out=ac_out,
            ac_extra_lines=ac_extra,
        )
        if split_limit is not None:
            try:
                split_gain = extract_ac_gain(
                    ac_wave, in_node=ac_in, out_node=split_limit[0]
                )
            except KeyError as exc:
                raise SimError(
                    f"SPICE convergence: missing split trace for cell {cell_id!r}: {exc}"
                ) from exc
            if not split_gain < split_limit[1]:
                raise SimError(
                    f"SPICE convergence: differential split broken"
                    f" ({split_limit[0]}={split_gain:.3f} V/V); no trust anchor"
                    f" for cell {cell_id!r}"
                )
        rel = abs(dc_gain - ac_gain) / dc_gain if dc_gain > 0 else float("inf")
        if rel > 0.10:
            raise SimError(
                f"SPICE convergence: dc/ac gain disagree ({dc_gain:.3f} vs"
                f" {ac_gain:.3f}); no trustworthy gain for cell {cell_id!r}"
            )
        with self._lock:
            self._conn.execute(
                "INSERT INTO measurement VALUES (?, ?, ?, ?, ?, ?)",
                (new_id(), dc_job, "dc_gain", dc_gain, "V/V", utcnow_iso()),
            )
            self._conn.execute(
                "INSERT INTO measurement VALUES (?, ?, ?, ?, ?, ?)",
                (new_id(), ac_job, "ac_gain", ac_gain, "V/V", utcnow_iso()),
            )
            self._conn.commit()
        if metric_id == "dc_gain":
            return dc_gain
        if metric_id == "ac_gain":
            return ac_gain
        # Bandwidth reads off the same in-memory AC sweep (zero extra
        # sims) and fails closed per contract when the stimulus holds no
        # unity crossing.
        ugbw = extract_bandwidth(ac_wave, in_node="in", out_node="out")
        with self._lock:
            self._conn.execute(
                "INSERT INTO measurement VALUES (?, ?, ?, ?, ?, ?)",
                (new_id(), ac_job, "bandwidth", ugbw, "Hz", utcnow_iso()),
            )
            self._conn.commit()
        return ugbw

    def measure_with_unit(self, *, cell_id: str, metric_id: str) -> dict[str, object]:
        """Measure plus the canonical contract unit symbol (wire-ready)."""
        value = self.measure(cell_id=cell_id, metric_id=metric_id)
        contract = METRIC_BY_ID.get(metric_id)
        unit = contract.units if contract is not None else ""
        return {"metric_id": metric_id, "value": value, "unit": unit}

    def run_erc(self, *, cell_name: str) -> tuple[bool, tuple[str, ...]]:
        """[defer Stage 8] Needs a LayoutBackend ERC adapter."""
        raise NotImplementedError("run_erc deferred to Stage 8 physical backends")

    def run_lvs(self, *, cell_name: str) -> tuple[bool, tuple[str, ...]]:
        """[defer Stage 8] Needs a LayoutBackend LVS adapter."""
        raise NotImplementedError("run_lvs deferred to Stage 8 physical backends")
