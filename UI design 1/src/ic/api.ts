// Typed transport client for the OpenVirtuoso FastAPI service.
//
// Transport only: no physics, no metric math, no unit conversion.
// Every physical quantity arrives as an SI base-unit JSON number;
// human formatting lives in display components, never here.

const DEFAULT_BASE = "http://127.0.0.1:8000";

let override: string | null = null;

/** Pin the service root (used by tests and the E2E demo). */
export function setApiBase(url: string): void {
  override = url;
}

function base(): string {
  if (override) return override;
  const fromEnv = import.meta.env.VITE_API_BASE as string | undefined;
  if (fromEnv) return fromEnv;
  return DEFAULT_BASE;
}

export class ApiError extends Error {
  readonly status: number;
  readonly detail: string;

  constructor(status: number, detail: string) {
    super(`API ${status}: ${detail}`);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let resp: Response;
  try {
    resp = await fetch(base() + path, {
      ...init,
      headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    });
  } catch (err) {
    throw new ApiError(0, `backend unreachable at ${base()}: ${String(err)}`);
  }
  let body: unknown = null;
  try {
    body = await resp.json();
  } catch {
    body = null;
  }
  if (!resp.ok) {
    const detail =
      typeof body === "object" && body !== null && "detail" in body
        ? String((body as { detail: unknown }).detail)
        : resp.statusText;
    throw new ApiError(resp.status, detail);
  }
  return body as T;
}

function post<T>(path: string, payload: unknown): Promise<T> {
  return request<T>(path, { method: "POST", body: JSON.stringify(payload) });
}

export type Health = { status: string; engine_api_version: string };
export type ProjectOut = { project_id: string };
export type CellOut = { cell_id: string };
export type ValidateOut = { valid: boolean; violations: string[] };
export type NetlistOut = { netlist: string };
export type SimulateOut = { reproducibility_id: string };
export type JobSummary = {
  job_id: string;
  kind: string;
  status: string;
  created_at: string;
  updated_at: string;
};
export type JobDetail = JobSummary & { result: string | null; error: string | null };
export type CellSummary = { cell_id: string; cell_name: string; library_name: string };
export type SchematicInstance = {
  instance_id: string;
  instance_name: string;
  symbol_name: string;
  parameters: Record<string, number>;
};
export type SchematicPort = {
  port_name: string;
  net_name: string;
  instance_name: string | null;
};
export type Schematic = {
  cell_id: string;
  cell_name: string;
  instances: SchematicInstance[];
  nets: string[];
  ports: SchematicPort[];
};
export type WaveformTrace = {
  name: string;
  unit: string | null;
  y: number[] | null;
  magnitude_db: number[] | null;
  phase_deg: number[] | null;
};
export type Waveforms = {
  job_id: string;
  analysis: string;
  x_name: string;
  x_unit: string;
  x: number[];
  traces: WaveformTrace[];
};
export type ExplainOut = {
  job_id: string;
  category: string;
  trigger: string;
  prose: string;
  cited_ids: string[];
  action_id: string;
  provider: string;
  model: string;
};
export type DemoRunOut = { job_id: string; cell_id: string; reproducibility_id: string };

export const health = (): Promise<Health> => request<Health>("/health");
export const listJobs = (): Promise<JobSummary[]> => request<JobSummary[]>("/jobs");
export const getJob = (jobId: string): Promise<JobDetail> =>
  request<JobDetail>(`/jobs/${encodeURIComponent(jobId)}`);
export const getWaveforms = (jobId: string): Promise<Waveforms> =>
  request<Waveforms>(`/jobs/${encodeURIComponent(jobId)}/waveforms`);
export const listCells = (): Promise<CellSummary[]> => request<CellSummary[]>("/cells");
export const getSchematic = (cellId: string): Promise<Schematic> =>
  request<Schematic>(`/cells/${encodeURIComponent(cellId)}/schematic`);
export const runDemo = (name: string, seed = 21): Promise<DemoRunOut> =>
  post<DemoRunOut>("/testbenches/run", { name, seed });
export const explainJob = (jobId: string): Promise<ExplainOut> =>
  post<ExplainOut>("/copilot/explain", { job_id: jobId });
export const createProject = (name: string): Promise<ProjectOut> =>
  post<ProjectOut>("/projects", { name });
export const createCell = (projectId: string, cellName: string): Promise<CellOut> =>
  post<CellOut>("/cells", { project_id: projectId, cell_name: cellName });
export const instantiate = (
  cellId: string,
  templateId: string,
  parameters: Record<string, number>,
): Promise<CellOut> =>
  post<CellOut>("/instantiate", {
    cell_id: cellId,
    template_id: templateId,
    parameters,
  });
export const validate = (cellId: string): Promise<ValidateOut> =>
  post<ValidateOut>("/validate", { cell_id: cellId });
export const netlist = (cellId: string): Promise<NetlistOut> =>
  post<NetlistOut>("/netlist", { cell_id: cellId });
export const simulate = (deck: string, seed: number): Promise<SimulateOut> =>
  post<SimulateOut>("/simulate", { netlist: deck, seed });
