# context.md — Project State & Agent Continuity Handbook

> **Purpose**: This document stores the complete, persistent context of the project and current task. If an active AI agent fails, crashes, hits rate/context/token limits, or hands off to another session, any incoming agent reading this document can immediately resume execution with zero lost context.

---

## 1. Executive Summary & Mission

- **Project**: Open-Source AI-Native Analog IC Design Platform.
- **Target Audience**: Open-source silicon designers, analog IC researchers, and students.
- **Initial Technology Node**: SkyWater 130nm (`Sky130`) open-source PDK.
- **Toolchain Foundation**: `ngspice` (via `libngspice` C API) for electrical simulation, `KLayout` (+ `Magic` / `Netgen` adapters) for layout/DRC/LVS/PEX.
- **Architectural Philosophy**:
  - **Headless First**: Build and verify the complete closed design loop headlessly via code first (spec $\to$ topology $\to$ sizing $\to$ simulation $\to$ measurement $\to$ optimization $\to$ verification). The GUI is built last as a client.
  - **Strict Validation Gate**: Schema + connectivity + unit + model-binding validation MUST pass before reaching ngspice.
  - **The Golden Rule**: The agent proposes, the simulator decides, and the human commits.
  - **The Core Moat**: A persistent, reproducible Design Knowledge Base (Experiment Ledger) linking historical sizing, failures, and specifications to validated topology templates.

---

## 2. Core Architecture Stack

```text
┌─────────────────────────────────────────────────────────────┐
│                 Clients & Presentation Layer                │
│    CLI Tools    │  Schematic UI (Stage 7)  │   AI Copilot   │
└──────────────────────────────┬──────────────────────────────┘
                               │ (Calls ONLY)
┌──────────────────────────────▼──────────────────────────────┐
│                  DesignEngine v0.1 API                      │
│   create_project  │  create_cell   │  instantiate           │
│   validate        │  netlist       │  simulate              │
│   check_constraints optimize       │  run_drc               │
│   extract         │  compare                                │
└──────┬───────────────────────┬───────────────────────┬──────┘
       │                       │                       │
┌──────▼──────┐         ┌──────▼──────┐         ┌──────▼──────┐
│ PDKAdapter  │         │  Simulator  │         │LayoutBackend│
│ (Sky130)    │         │(libngspice) │         │ (KLayout)   │
└─────────────┘         └─────────────┘         └─────────────┘
```

- **Canonical Specification Authority**: The Design Engine owns `Specification`, `MetricContract`, `Measurement`, and `SimulationRun`. Third-party characterization engines (such as CACE) act strictly as adapters, never as second sources of truth for metric contracts or pass/fail criteria.
- **Strict SI Base Units**: All values in memory, DB, and APIs are SI base units ($F, \Omega, Hz, V, A, s, m, K$). String parsing occurs only in the UI presentation layer.
- **Worker-Process Isolation from Day One**: Simulator execution uses isolated worker processes (`Job Scheduler -> Worker Process -> single libngspice instance`) to eliminate C-level shared state and thread reentrancy hazards.
- **Atomic Commit Granularity**: Critical stages are decomposed into focused, single-purpose commits (e.g. Stage 1 is split into 1A through 1G) to guarantee precise failure localization.

---

## 3. Host System & Hardware Constraints

An incoming agent must respect the physical constraints of the host machine:
- **Operating System**: Windows 11 (OS Build with WSL2).
- **CPU / RAM**: Modern x86-64 host with **16 GB System RAM**.
- **GPU / VRAM**: NVIDIA GeForce RTX 4060 Laptop GPU (**8 GB VRAM**).
- **Free Disk Space**: ~100 GB free storage.
- **Container Environment**: Docker Desktop / Podman running with the **WSL2 backend** (never Hyper-V).
- **WSL2 Storage Discipline**:
  - WSL2 virtual disks (`ext4.vhdx`) grow dynamically and do not automatically reclaim freed space. Periodically run virtual disk compaction via PowerShell (`wsl --manage --compact` or `diskpart`).
  - Run `docker system prune` after every major image build.
  - Never download unnecessary local LLM weights or full standard-cell PDK libraries in early stages.

---

## 4. AI Engine Roster & Operational Routing

| Role | Engine / Model | Channel / Interface | Routing Notes |
|---|---|---|---|
| **Build Agent (Stages 0–4)** | OpenCode / Antigravity Agent | Gemini API via Google AI Studio (`GEMINI_STRONG_MODEL` / `GEMINI_FAST_MODEL`) | Reads `AGENTS.md` natively. Multi-file edit discipline with strict diffs. |
| **Architecture & Plan Review** | ChatGPT Plus (GPT-5 class) | Web chat / Manual paste | Reviewing major designs and stage handoffs. |
| **PDK Grounding & Deck Verification** | Gemini Pro (1M context) | AI Studio / Web | Grounding Sky130 model cards, spice subcircuits, and layer syntax. |
| **Adversarial Test Author** | **ChatGPT Plus** (different family) | Web chat / Copy-paste | Authors broken/failing test cases against the primary agent's code. |
| **Third Sanity Check** | Claude Chat | Web chat | Extra independent model family when checkpoints trigger. |
| **In-Product Copilot (Stage 5+)** | Pinned API / Local 7–8B 4-bit | `LLMProvider` abstraction | Narrow, grounded failure narration citing exact `ErrorRecord` IDs. |

### Model Capability Aliases Rule
Operational code and agent configuration NEVER hardcode model generation names (e.g., "gemini-1.5-pro", "gemini-3-flash"). They must resolve through configuration aliases:
- `GEMINI_STRONG_MODEL`: Current high-reasoning Gemini model.
- `GEMINI_FAST_MODEL`: Current fast/low-cost Gemini model.

---

## 5. Current Project Status & File Inventory

### Active Status: STAGES 0–6 + PHASE 0 + 7A + 7B-1→7B-8 + R0-1→R0-3 COMMITTED (push due)
> 6E sim-grounded Miller → 6F sizing (winner invalidated) → Phase 0 Steps 1–2
> (PM unwrap fix ADR-027, re-baseline ADR-028, empirical winner trial 17:
> gain 81.30dB / UGB 16.58MHz / PM 63.64°).
> Step-2 re-close verdict CONFIRMED by human 2026-09-09 (accept Trial-17,
> UGB shortfall recorded) — push gate lifted, R0-1→R0-3 pushed to origin/main.
> 7A lockdown (EngineV01 strangler facade ADR-030, Law-4 AST guard, schema v9
> checkpoint_registry + design_state) → 7B HTTP service (pinned
> fastapi/uvicorn/httpx2, threaded-server tests, thin-slice inverter wave
> over HTTP ADR-032) → 7B-4 job observability → Path B adopted 2026-09-10
> (ADR-033: close R0-3, wire the shell, B5–B7 stay deferred) → 7B-5 cells/
> schematic + 7B-6 waveforms + 7B-7 mock-copilot + 7B-8 demo-testbench
> routes (ADR-034 wire contract; 13 endpoints total).
> Gates: base 359+39 green; EDA B4 `-k b4` 2 passed + 1 skip, demo file
> 2 passed + 1 skip (live rail-to-rail inversion). CI Actions status unobserved
> from here (no gh/token) — verify green in the GitHub tab.
> Committed but UNPUSHED: `9118bfc` (7B-5), `f88a433` (7B-6), `c325030` (7B-7),
> `f86e7fa` (7B-8) — push on human go.
> Next: Step 3 shell binding (`store.tsx` runSimulation + SimulationExplorer
> de-faking + WaveformAnalyzer live PlotPane; TS unverifiable here — no node
> binary), then Step 4 `npm run dev` E2E. B5–B7 deferred; no node/tsc/vite
> verification possible in this environment.

### Repository File Map
```text
C:\MONEY\Cad\codeeahhhhhhh\
├── final_prompt.md         # Master Playbook (v1.2) — Prompts, checkpoints, engine roster
├── final_build.md          # Master Build Plan (v3.2) — Architecture, contracts, stages 0-14
├── final_prod.pdf          # Reference specification PDF document
├── AGENTS.md               # Layer 1 Global Rules (The 4 laws, checkpoints, units, safety)
├── context.md              # [THIS FILE] System continuity handbook and state memory
├── To-Do.md                # Granular task tracker (updated before and after every step)
├── DECISIONS.md            # Architecture Decision Records (ADR-001 through ADR-034)
├── PREREQUISITES.md        # Complete Stage 0 prerequisite specifications & verification
├── Dockerfile              # Layered build: base verified / eda GREEN (ADR-015/017)
├── docker-compose.yml      # app (base) + app-eda (eda profile) services
├── Makefile                # exactly [setup, test, run-example], container-authority
├── pyproject.toml          # packaging + strict pytest/ruff/mypy config
├── config/models.json      # GEMINI_* capability aliases (UNCONFIGURED pre-Stage-5)
├── scripts/check_models.py # no-network alias health check
├── examples/smoke.py       # packaging baseline verification
├── tests/test_smoke.py     # packaging contract tests (6)
├── tests/test_interfaces.py  # Law 4 backend contract tests (Commit 2)
├── tests/test_engine_api.py  # DesignEngine v0.1 freeze tests (Commit 2)
├── tests/test_units.py       # SI unit contract tests (1A)
├── tests/test_schema.py      # migration + schema tests (1B, v1–v9)
├── tests/test_graph.py       # connectivity fact tests (1C)
├── tests/test_canonical.py   # canonical identity tests (1D)
├── tests/test_compiler.py    # netlist expectation tests (1E)
├── tests/test_validate.py    # gate rejection suite (1F)
├── tests/test_golden.py + tests/golden/nmos.cir  # golden fixture (1G, read-only)
├── tests/test_sim.py, test_jobs.py, test_reproduce.py, test_waveform.py, test_stress.py, test_inverter.py # Stage 2 tests
├── tests/test_metrics.py, test_gain.py, test_bandwidth.py, test_phase_margin.py, test_slew_rate.py  # Stage 3 tests (contracts→slew)
├── tests/test_power.py, test_offset.py, test_settling_time.py, test_evaluator.py  # Stage 3 tests (power→evaluator)
├── tests/test_schema.py (v9 checkpoint_registry + design_state)  # migrations incl v9
├── tests/test_optimize.py, test_optimize_demo.py  # Stage 4 tests (ledger, optimizer, demo)
├── tests/test_engine_v01.py + test_api_service.py + test_api_thin_slice.py + test_api_jobs.py  # 7A/7B engine, API, slice, jobs
├── tests/test_api_schematic.py + test_api_waveforms.py + test_api_copilot.py + test_api_testbench.py  # 7B-5→7B-8 wire-contract routes
├── tests/test_design_state.py + test_architecture_boundary.py  # v9 tables, Law-4 AST guard
├── tests/test_bench.py  # R0 AnalogBench registry + B0–B4 executable (B5–B7 deferred per ADR-033)
├── src/analog_ic_design/     # ENGINE_API_VERSION=0.1; interfaces/, engine/ (ABC + EngineV01), api/ (FastAPI service),
│                             # units/ (quantity, display), store/ (schema v9),
│                             # circuit/ (graph, canonical, compiler, validator, pdk_limits),
│                             # sim/ (backend, ngspice, jobs, reproduce, waveform, testbench, inverter, mirror, diff_pair, cs_amp, cascode),
│                             # metrics/ (contract matrix, gain, bandwidth, phase_margin, slew_rate, power, offset, settling_time, evaluator),
│                             # optimize/ (optimizer interface, ledger, optuna TPE),
│                             # robust/ (corners, MC sampler, statistical protocol),
│                             # ai/ (taxonomy, provenance, provider, residency, explainer),
│                             # bench/ (AnalogBench registry + runner; B0–B4 executable, B5–B7 deferred per ADR-033),
│                             # topology/ (templates, KB, retriever, proposals),
├── AGENT2.md             # v1.0-frozen implementation constitution + §19 UI adoption contract
├── mockups/              # static selection artifacts (NOT product code): midnight-lab HTML, lovable showcase HTML
├── UI\ design\ 1/        # adopted Lovable Axiom shell (Stage 7 UI baseline, ADR-031; untracked vendor-style drop)
├── tests/test_corner.py, test_pvt_sim.py, test_mc_spike.py, test_protocol.py  # Stage 4.5 tests (corners, matrix, sampler, protocol)
├── tests/test_ai_classify.py, test_ai_provider.py, test_ai_explain.py  # Stage 5 tests (classifier, provider, explainer)
├── examples/plot_inverter.py # Stage 2H waveform generation demo
├── src/analog_ic_design/     # ENGINE_API_VERSION=0.1; interfaces/, engine/,
│                             # units/ (quantity, display), store/ (schema v8),
│                             # circuit/ (graph, canonical, compiler, validator, pdk_limits),
│                             # sim/ (backend, ngspice, jobs, reproduce, waveform, testbench, inverter, mirror, diff_pair, cs_amp, cascode),
│                             # metrics/ (contract matrix, gain, bandwidth, phase_margin, slew_rate, power, offset, settling_time, evaluator),
│                             # optimize/ (optimizer interface, ledger, optuna TPE),
│                             # robust/ (corners, MC sampler, statistical protocol),
│                             # ai/ (taxonomy, provenance, provider, residency, explainer),
│                             # robust/ (corners, MC sampler, statistical protocol)
├── Tasks_Comp.md           # completed-tasks evidence ledger
├── docs/stages/stage-0.md  # Layer 2 stage brief (§7–§9: verification, audit, EDA)
├── docs/stages/stage-1.md  # Layer 2 stage brief (1A–1G + checkpoint)
├── docs/stages/stage-2.md  # Layer 2 stage brief (Simulation Kernel)
├── docs/stages/stage-3.md  # Layer 2 stage brief (Measurement & Specification Engine)
├── docs/stages/stage-4.md  # Layer 2 stage brief (Optimization Layer)
├── docs/stages/stage-4.5.md  # Layer 2 stage brief (Robustness: PVT + Monte Carlo)
├── docs/stages/stage-5.md  # Layer 2 stage brief (AI Diagnostics & Copilot)
└── docs/stage-0-layered-debt.md  # CLOSED (R-1..R-8 checked off)
```

---

## 6. How an Incoming Agent Must Resume Work

If you are a new agent taking over this conversation or workspace, execute these exact steps in order:

1. **Acknowledge Rules**: Read [`AGENTS.md`](file:///c:/MONEY/Cad/codeeahhhhhhh/AGENTS.md) and confirm the Four Laws back to the user in one sentence each:
   - *Law 1*: Human signs off on stage completion; agent never marks it done.
   - *Law 2*: Never invent Sky130 model syntax; read PDK reference files.
   - *Law 3*: Pre-simulation validation gate has zero bypass.
   - *Law 4*: Everything routes through `DesignEngine v0.1`; no direct side doors.
2. **Consult Task Tracker**: Open [`To-Do.md`](file:///c:/MONEY/Cad/codeeahhhhhhh/To-Do.md) to inspect what is completed and what is currently pending.
3. **Verify Prerequisite Status**: Inspect [`PREREQUISITES.md`](file:///c:/MONEY/Cad/codeeahhhhhhh/PREREQUISITES.md) to confirm all host tools (WSL2, Docker, Python 3.11, strict typing, linters) are ready before executing any Stage 0 build commands.
4. **Log Decisions**: Any architectural decision made during your turn MUST be documented as a new ADR entry in [`DECISIONS.md`](file:///c:/MONEY/Cad/codeeahhhhhhh/DECISIONS.md).
5. **Update To-Do**: Update [`To-Do.md`](file:///c:/MONEY/Cad/codeeahhhhhhh/To-Do.md) **BEFORE** modifying files and **AFTER** finishing tasks.
6. **Trigger Human Checkpoints**: If any action touches a checkpoint category from `AGENTS.md` §8 for the first time, stop immediately and emit the blocking alert.
