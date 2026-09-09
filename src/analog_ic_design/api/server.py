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


class HealthOut(BaseModel):
    """Service + engine contract identity."""

    status: str
    engine_api_version: str


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

    return app


app: FastAPI = create_app()
