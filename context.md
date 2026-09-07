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

### Active Status: STAGES 0–3 COMMITTED & HUMAN-CONFIRMED — STAGE 4 IMPLEMENTED, UNCOMMITTED
> Stages 0–2 committed and human-confirmed 2026-09-05/06. Stage 3 (3A–3J)
> 100% complete and human-confirmed 2026-09-07: 3A contracts + v6, 3B AC/complex,
> 3C gain (9.1 V/V), 3D bandwidth (20.7 MHz @1pF), 3E phase margin (83.37°),
> 3F slew rate (unloaded 4.96e11, loaded 8.32e9 V/s @50fF), 3G power (0.55 µW),
> 3H offset (1.9e-10 V sym, -77 mV mismatch on diff_pair), 3I settling (26.2 ns @1pF),
> 3J specification evaluator (hard/soft/weighted FOM). Stage 4 (4A brief+v7 ledger,
> 4B ask/tell interface, 4C seeded Optuna TPE, 4D live cs_amp sizing: 8 trials
> seed 7, winner trial 5 w_n=2.198µm w_p=5.019µm, gain 9.139, UGB 13.44 MHz,
> spec passed, interior — advisory NOT triggered; winner re-simulated within
> 1e-6). Gate green: base 243+26, EDA 269/269, ruff + mypy strict clean
> (72 files). Next: commit 4A–4D, push, watch CI, then Stage 4.5.
> PDK deck boundary: micron geometry + scale=1e-6, explicit VSS ground (ADR-020); failing decks run
> in workers only (ADR-021). WSL2 Ubuntu is the sanctioned `make` shell
> (GNU Make 4.3 + Docker 29.6.2 verified); stock PowerShell has no `make`.

### Repository File Map
```text
C:\MONEY\Cad\codeeahhhhhhh\
├── final_prompt.md         # Master Playbook (v1.2) — Prompts, checkpoints, engine roster
├── final_build.md          # Master Build Plan (v3.2) — Architecture, contracts, stages 0-14
├── final_prod.pdf          # Reference specification PDF document
├── AGENTS.md               # Layer 1 Global Rules (The 4 laws, checkpoints, units, safety)
├── context.md              # [THIS FILE] System continuity handbook and state memory
├── To-Do.md                # Granular task tracker (updated before and after every step)
├── DECISIONS.md            # Architecture Decision Records (ADR-001 through ADR-022)
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
├── tests/test_schema.py      # migration + schema tests (1B, v1–v7)
├── tests/test_graph.py       # connectivity fact tests (1C)
├── tests/test_canonical.py   # canonical identity tests (1D)
├── tests/test_compiler.py    # netlist expectation tests (1E)
├── tests/test_validate.py    # gate rejection suite (1F)
├── tests/test_golden.py + tests/golden/nmos.cir  # golden fixture (1G, read-only)
├── tests/test_sim.py, test_jobs.py, test_reproduce.py, test_waveform.py, test_stress.py, test_inverter.py # Stage 2 tests
├── tests/test_metrics.py, test_gain.py, test_bandwidth.py, test_phase_margin.py, test_slew_rate.py  # Stage 3 tests (contracts→slew)
├── tests/test_power.py, test_offset.py, test_settling_time.py, test_evaluator.py  # Stage 3 tests (power→evaluator)
├── tests/test_schema.py (v7 experiment), test_optimize.py, test_optimize_demo.py  # Stage 4 tests (ledger, optimizer, demo)
├── examples/plot_inverter.py # Stage 2H waveform generation demo
├── src/analog_ic_design/     # ENGINE_API_VERSION=0.1; interfaces/, engine/,
│                             # units/ (quantity, display), store/ (schema v7),
│                             # circuit/ (graph, canonical, compiler, validator, pdk_limits),
│                             # sim/ (backend, ngspice, jobs, reproduce, waveform, testbench, inverter, cs_amp, diff_pair),
│                             # metrics/ (contract matrix, gain, bandwidth, phase_margin, slew_rate, power, offset, settling_time, evaluator),
│                             # optimize/ (optimizer interface, ledger, optuna TPE)
├── Tasks_Comp.md           # completed-tasks evidence ledger
├── docs/stages/stage-0.md  # Layer 2 stage brief (§7–§9: verification, audit, EDA)
├── docs/stages/stage-1.md  # Layer 2 stage brief (1A–1G + checkpoint)
├── docs/stages/stage-2.md  # Layer 2 stage brief (Simulation Kernel)
├── docs/stages/stage-3.md  # Layer 2 stage brief (Measurement & Specification Engine)
├── docs/stages/stage-4.md  # Layer 2 stage brief (Optimization Layer)
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
