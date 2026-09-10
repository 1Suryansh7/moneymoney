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

    @app.get("/cells", response_model=list[CellSummary])
    def list_cells(request: Request) -> list[dict[str, str]]:
        return _engine(request).list_cells()

    @app.get("/cells/{cell_id}/schematic", response_model=SchematicOut)
    def get_schematic(cell_id: str, request: Request) -> dict[str, Any]:
        try:
            return _engine(request).schematic(cell_id=cell_id)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    return app


app: FastAPI = create_app()
