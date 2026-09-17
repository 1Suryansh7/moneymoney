"""FastAPI service over EngineV01 (Stage 7B-2: skeleton).

Every route delegates to exactly one engine method. Error mapping preserves
the taxonomy wording verbatim in the response detail: caller-usage faults
(ValueError: Schema/Units/...) become 422; simulator faults (SimError)
become 500. All physical quantities cross as SI base-unit JSON numbers;
human formatting lives in the frontend, never here.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from analog_ic_design.engine import ENGINE_API_VERSION
from analog_ic_design.engine.engine_v01 import EngineV01, SimError

_DEFAULT_DB: str = "openvirtuoso.sqlite"


class ProjectCreate(BaseModel):
    """Create-project request."""

    name: str


class ProjectOut(BaseModel):
    """Created project handle."""

    project_id: str


class CellCreate(BaseModel):
    """Create-cell request."""

    project_id: str
    cell_name: str


class CellOut(BaseModel):
    """Cell handle (created or template-instantiated)."""

    cell_id: str


class CellRenameIn(BaseModel):
    """Cell-rename request."""

    cell_name: str


class CellRenameOut(BaseModel):
    """Renamed cell handle."""

    cell_id: str
    cell_name: str


class InstantiateIn(BaseModel):
    """Template-instantiation request (SI values only)."""

    cell_id: str
    template_id: str
    parameters: dict[str, float]


class ValidateIn(BaseModel):
    """Validation-gate request."""

    cell_id: str


class ValidateOut(BaseModel):
    """Gate verdict plus violation messages."""

    valid: bool
    violations: list[str]


class NetlistIn(BaseModel):
    """Netlist-compilation request."""

    cell_id: str


class NetlistOut(BaseModel):
    """Deterministic SPICE netlist."""

    netlist: str


class SimulateIn(BaseModel):
    """Simulation request (deck carries SI units inside)."""

    netlist: str
    seed: int


class SimulateOut(BaseModel):
    """Reproducibility identity of the settled run."""

    reproducibility_id: str


class JobSummary(BaseModel):
    """Ledger summary for the Run Center (no payloads)."""

    job_id: str
    kind: str
    status: str
    created_at: str
    updated_at: str


class JobDetail(JobSummary):
    """Full ledger row, result payload included when present."""

    result: str | None
    error: str | None


class CellSummary(BaseModel):
    """Design-browser row (no payloads, mirrors /jobs summaries)."""

    cell_id: str
    cell_name: str
    library_name: str


class SchematicInstance(BaseModel):
    """One placed device with SI parameter floats."""

    instance_id: str
    instance_name: str
    symbol_name: str
    parameters: dict[str, float]


class SchematicPort(BaseModel):
    """One terminal hookup; null instance means a cell-level port."""

    port_name: str
    net_name: str
    instance_name: str | None


class SchematicOut(BaseModel):
    """Render-ready cell connectivity (empty string net = unconnected)."""

    cell_id: str
    cell_name: str
    instances: list[SchematicInstance]
    nets: list[str]
    ports: list[SchematicPort]


class HealthOut(BaseModel):
    """Service + engine contract identity."""

    status: str
    engine_api_version: str


class WaveformTrace(BaseModel):
    """One display trace: tran carries unit+y, AC carries magnitude/phase."""

    name: str
    unit: str | None = None
    y: list[float] | None = None
    magnitude_db: list[float] | None = None
    phase_deg: list[float] | None = None


class WaveformsOut(BaseModel):
    """PlotPane-ready vectors; SI floats, formatting lives in the frontend."""

    job_id: str
    analysis: str
    x_name: str
    x_unit: str
    x: list[float]
    traces: list[WaveformTrace]


class ExplainIn(BaseModel):
    """Copilot explanation request: one failed job id."""

    job_id: str


class ExplainOut(BaseModel):
    """Grounded explanation plus its provenance handle."""

    job_id: str
    category: str
    trigger: str
    prose: str
    cited_ids: list[str]
    action_id: str
    provider: str
    model: str


class ChatIn(BaseModel):
    """Tutor message: free text, routed by the keyword classifier."""

    message: str


class ChatOut(BaseModel):
    """Grounded answer (trail echoes action_id) or refusal (null trail)."""

    job_id: str | None
    category: str
    trigger: str
    prose: str
    cited_ids: list[str]
    action_id: str
    trail: str
    provider: str
    model: str


class DemoRunIn(BaseModel):
    """One-click demo simulation request (deck assembled server-side)."""

    name: str
    seed: int = 21


class DemoRunOut(BaseModel):
    """Job handle plus the cell the deck was built from."""

    job_id: str
    cell_id: str
    reproducibility_id: str


class CornersIn(BaseModel):
    """PVT sweep request: demo deck plus envelope corner ids (all if omitted)."""

    name: str = "inverter_tran"
    corners: list[str] | None = None
    seed: int = 21


class CornerRun(BaseModel):
    """One corner's outcome: ledger job handle or fail-soft error row."""

    corner: str
    process: str
    temp_c: float
    vdd_v: float
    job_id: str | None
    status: str
    message: str
    reproducibility_id: str | None


class CornersOut(BaseModel):
    """Full sweep: per-corner rows for dispersion display."""

    name: str
    runs: list[CornerRun]


class CompareIn(BaseModel):
    """Pre/post-layout comparison request: seed only (canonical stage)."""

    seed: int = 21


class StageMetrics(BaseModel):
    """One side of the comparison: SI floats, formatting downstream."""

    dc_gain: float
    ac_gain: float
    ugb_hz: float
    trip_v: float


class CompareOut(BaseModel):
    """Pre/post table plus degradation fractions for display."""

    pre: StageMetrics
    post: StageMetrics
    dc_rel_diff: float
    ac_rel_diff: float
    ugb_drop_frac: float


class MeasureIn(BaseModel):
    """Measurement request: one registered metric on one cell."""

    cell_id: str
    metric_id: str


class MeasureOut(BaseModel):
    """Measured SI value plus its unit symbol for display."""

    metric_id: str
    value: float
    unit: str


class OptimizeIn(BaseModel):
    """Study request: template, spec, space, budgets (returns in ms)."""

    template_id: str
    spec_id: str
    space: dict[str, list[float]]
    seed: int
    max_trials: int = 15
    trial_timeout_s: float = 300.0
    study_timeout_s: float | None = None
    objective: str = "spec"


class OptimizeOut(BaseModel):
    """Study handles: ledger job plus study identity."""

    job_id: str
    study_id: str


class TrialOut(BaseModel):
    """One trial's telemetry with recomputed score."""

    trial: int
    status: str
    parameters: dict[str, float]
    metrics: dict[str, float]
    verdict: str
    score: float
    reproducibility_id: str


class SpecCreateIn(BaseModel):
    """Specification authoring request (study targets)."""

    cell_id: str
    name: str
    rules: list[dict[str, Any]]


class SpecOut(BaseModel):
    """Created specification handle."""

    spec_id: str


class CancelOut(BaseModel):
    """Cancel verdict: terminal status stands, whatever it is."""

    job_id: str
    status: str


def _engine(request: Request) -> EngineV01:
    engine = request.app.state.engine
    assert isinstance(engine, EngineV01)
    return engine


def create_app(*, db_path: str | Path | None = None) -> FastAPI:
    """Build the service bound to one database file.

    The engine is created inside the lifespan handler, so construction,
    request handling, and teardown all share the server event-loop thread.
    Importing this module has zero filesystem side effects. Tests drive the
    ASGI app directly via httpx2 and shut the server down to trigger the
    lifespan close — no TestClient, no live server, no starlette test shims.
    """
    resolved = str(db_path) if db_path is not None else _DEFAULT_DB

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.engine = EngineV01(db_path=app.state.db_path)
        yield
        app.state.engine.close()

    app = FastAPI(title="OpenVirtuoso API", version=ENGINE_API_VERSION, lifespan=lifespan)
    app.state.db_path = resolved

    # Local-dev origins only: wildcard + credentials is rejected by
    # browsers, so the two loopback spellings are listed explicitly.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health", response_model=HealthOut)
    def health() -> dict[str, str]:
        return {"status": "ok", "engine_api_version": ENGINE_API_VERSION}

    @app.post("/projects", response_model=ProjectOut)
    def create_project(body: ProjectCreate, request: Request) -> dict[str, str]:
        try:
            return {"project_id": _engine(request).create_project(name=body.name)}
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.post("/cells", response_model=CellOut)
    def create_cell(body: CellCreate, request: Request) -> dict[str, str]:
        try:
            return {
                "cell_id": _engine(request).create_cell(
                    project_id=body.project_id, cell_name=body.cell_name
                )
            }
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.post("/instantiate", response_model=CellOut)
    def instantiate(body: InstantiateIn, request: Request) -> dict[str, str]:
        try:
            return {
                "cell_id": _engine(request).instantiate(
                    cell_id=body.cell_id,
                    template_id=body.template_id,
                    parameters=body.parameters,
                )
            }
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.post("/validate", response_model=ValidateOut)
    def validate(body: ValidateIn, request: Request) -> dict[str, Any]:
        try:
            valid, violations = _engine(request).validate(cell_id=body.cell_id)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return {"valid": valid, "violations": list(violations)}

    @app.post("/netlist", response_model=NetlistOut)
    def netlist(body: NetlistIn, request: Request) -> dict[str, str]:
        try:
            return {"netlist": _engine(request).netlist(cell_id=body.cell_id)}
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.post("/simulate", response_model=SimulateOut)
    def simulate(body: SimulateIn, request: Request) -> dict[str, str]:
        try:
            return {
                "reproducibility_id": _engine(request).simulate(
                    netlist=body.netlist, seed=body.seed
                )
            }
        except SimError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @app.get("/jobs", response_model=list[JobSummary])
    def list_jobs(request: Request) -> list[dict[str, str]]:
        return _engine(request).list_jobs()

    @app.get("/jobs/{job_id}", response_model=JobDetail)
    def get_job(job_id: str, request: Request) -> dict[str, str | None]:
        try:
            return _engine(request).job_result(job_id=job_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.get("/jobs/{job_id}/waveforms", response_model=WaveformsOut)
    def get_waveforms(job_id: str, request: Request) -> dict[str, Any]:
        try:
            return _engine(request).job_waveforms(job_id=job_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except SimError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @app.post("/copilot/explain", response_model=ExplainOut)
    def copilot_explain(body: ExplainIn, request: Request) -> dict[str, Any]:
        try:
            return _engine(request).explain_job(job_id=body.job_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.post("/copilot/chat", response_model=ChatOut)
    def copilot_chat(body: ChatIn, request: Request) -> dict[str, Any]:
        # Chat never raises: failure questions without failed jobs in
        # scope refuse, exactly like out-of-domain messages.
        return _engine(request).chat(message=body.message)

    @app.post("/testbenches/run", response_model=DemoRunOut)
    def run_demo_testbench(body: DemoRunIn, request: Request) -> dict[str, str]:
        try:
            return _engine(request).run_demo_testbench(name=body.name, seed=body.seed)
        except SimError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.post("/corners/run", response_model=CornersOut)
    def run_corners(body: CornersIn, request: Request) -> dict[str, Any]:
        # Per-corner faults stay in rows (fail-soft by design); only bad
        # requests raise.
        try:
            return _engine(request).run_corners(
                name=body.name, corners=body.corners, seed=body.seed
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.post("/postlayout/compare", response_model=CompareOut)
    def compare_postlayout(body: CompareIn, request: Request) -> dict[str, Any]:
        # Blocks ~2-3 min (documented; the UI holds RUNNING meanwhile).
        # Toolchain/backend absence surfaces taxonomy (500).
        try:
            return _engine(request).compare_prepost(seed=body.seed)
        except SimError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.post("/measure", response_model=MeasureOut)
    def measure(body: MeasureIn, request: Request) -> dict[str, object]:
        try:
            return _engine(request).measure_with_unit(
                cell_id=body.cell_id, metric_id=body.metric_id
            )
        except SimError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.post("/optimize", response_model=OptimizeOut, status_code=202)
    def submit_study(body: OptimizeIn, request: Request) -> dict[str, str]:
        try:
            return _engine(request).submit_study(
                template_id=body.template_id,
                spec_id=body.spec_id,
                space=body.space,
                seed=body.seed,
                max_trials=body.max_trials,
                trial_timeout_s=body.trial_timeout_s,
                study_timeout_s=body.study_timeout_s,
                objective=body.objective,
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.get("/studies/{study_id}/trials", response_model=list[TrialOut])
    def list_trials(study_id: str, request: Request) -> list[dict[str, object]]:
        try:
            return _engine(request).list_trials(study_id=study_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.post("/jobs/{job_id}/cancel", response_model=CancelOut)
    def cancel_job(job_id: str, request: Request) -> dict[str, str]:
        try:
            return _engine(request).cancel_job(job_id=job_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.post("/specs", response_model=SpecOut)
    def create_spec(body: SpecCreateIn, request: Request) -> dict[str, str]:
        try:
            return _engine(request).create_spec(
                cell_id=body.cell_id, name=body.name, rules=body.rules
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.get("/cells", response_model=list[CellSummary])
    def list_cells(request: Request) -> list[dict[str, str]]:
        return _engine(request).list_cells()

    @app.post("/cells/{cell_id}/rename", response_model=CellRenameOut)
    def rename_cell(cell_id: str, body: CellRenameIn, request: Request) -> dict[str, str]:
        try:
            return _engine(request).rename_cell(cell_id=cell_id, cell_name=body.cell_name)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.get("/cells/{cell_id}/schematic", response_model=SchematicOut)
    def get_schematic(cell_id: str, request: Request) -> dict[str, Any]:
        try:
            return _engine(request).schematic(cell_id=cell_id)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    return app


app: FastAPI = create_app()
