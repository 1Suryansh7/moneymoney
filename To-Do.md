# To-Do.md — Master Task & Execution Tracker

> **CRITICAL OPERATIONAL DIRECTIVE FOR ALL AGENTS**:  
> You MUST inspect and update this tracker **BEFORE** beginning any task or modifying any files, and update it again **IMMEDIATELY AFTER** completing any task. Mark tasks `[ ]` (pending), `[-]` (in progress), or `[x]` (completed). Never skip steps or batch multiple stages into a single prompt.

---

## Current Status Overview
- **Active Phase**: Stage 0 — Architecture & Packaging (human-authorized 2026-09-05)
- **Stage 0 Code Status**: 🟡 **IN PROGRESS — Commit 1** (packaging + CI; Commit 2 interfaces next; EDA follow-up before Stage 1G per ADR-015).

---

## Phase 0: Repository Governance, Rules & Stage 0 Preparation

- [x] **0.1 Deep Architecture & Playbook Analysis**
  - [x] Parse and cross-reference `final_prompt.md` (v1.2) and `final_build.md` (v3.2).
  - [x] Extract all non-negotiable rules, checkpoints, taxonomy, contracts, and addendums.
- [x] **0.2 Governance & Rules Constitution**
  - [x] Create comprehensive [`AGENTS.md`](file:///c:/MONEY/Cad/codeeahhhhhhh/AGENTS.md) at repository root.
  - [x] Document the Four Laws, strict SI base unit system, and scope control rules.
  - [x] Codify the 12-category failure taxonomy and mandatory Human Checkpoint protocol.
  - [x] Integrate AI provenance (`LLMProvider`, `AIAction`), AI data residency modes, and model capability aliases.
- [x] **0.3 System State Continuity Handbook**
  - [x] Create [`context.md`](file:///c:/MONEY/Cad/codeeahhhhhhh/context.md) capturing full project mission, architecture stack, host constraints, and engine roster.
  - [x] Define step-by-step resume protocol for incoming agents.
- [x] **0.4 Master Task Tracker**
  - [x] Create [`To-Do.md`](file:///c:/MONEY/Cad/codeeahhhhhhh/To-Do.md) with hierarchical task checklists and strict pre-task update policy.
- [x] **0.5 Architecture Decision Records (ADR)**
  - [x] Create [`DECISIONS.md`](file:///c:/MONEY/Cad/codeeahhhhhhh/DECISIONS.md) documenting ADR-001 through ADR-014.
- [x] **0.6 Stage 0 Prerequisite Specifications**
  - [x] Create [`PREREQUISITES.md`](file:///c:/MONEY/Cad/codeeahhhhhhh/PREREQUISITES.md) detailing exact pinned toolchain versions, WSL2 tuning, strict typing, MCP servers, and validation commands.
- [ ] **0.7 Human Signoff of Phase 0**
  - [ ] Present completed governance and prerequisite set to human for review.

---

## Stage 0: Architecture & Packaging (Authorized 2026-09-05 — In Progress)

> **Commit Granularity**: Must land as two separate, cleanly isolated commits per master plan §10 addendum.
> **Predecessor rule (ADR-015)**: Stage-0 EDA follow-up must go green BEFORE Stage 1G; no Stage 2 prompt before that.

### Commit 1: System Packaging & CI Smoke Test
- [-] **1.1 Container Specification (`Dockerfile`)** — layered per ADR-015: `base` pinned `python:3.11-slim-bookworm` (verified); `eda` pins declared (`NGSPICE_VERSION=46`, `KLAYOUT_VERSION=0.30.12` per ADR-016; Magic/Netgen carry-over unverified; `OPEN_PDKS_GIT_REF` fail-closed UNPINNED).
  - [x] Pin exact base image (Python 3.11-slim-bookworm tag; digest recorded at build).
  - [x] Pin exact Python version (3.11 container authority; host 3.13 editing-only).
  - [ ] Pin ngspice with shared library (`libngspice`) build — DECLARED, EDA follow-up builds.
  - [ ] Pin SkyWater 130nm PDK primitive device models (`sky130A` commit hash) — UNPINNED, EDA follow-up freezes.
  - [x] Pin KLayout (0.30.12 declared per ADR-016; build in EDA follow-up).
  - [x] Pin Magic (8.3.456) and Netgen (1.5.270) as UNVERIFIED defaults (ADR-015 D-7).
- [-] **1.2 Container Orchestration (`docker-compose.yml`)** — `app` (base, verified) + `app-eda` (`eda` profile, pending).
  - [x] Configure local volume mounts, user UID/GID mapping.
- [-] **1.3 Makefile Automation** — exactly `[setup, test, run-example]` (asserted in test).
  - [x] Implement `make setup` (build container, run pytest + smoke inside container).
  - [x] Implement `make test` (ruff + mypy strict + pytest, all inside container).
  - [x] Implement `make run-example` (baseline smoke verification).
- [-] **1.4 CI Smoke Test Pipeline**
  - [x] Create GitHub Actions workflow (`.github/workflows/ci.yml`) to build container and run `make test`.
  - [ ] Validate `act` configuration for local CI execution — DEFERRED (`act` not installed on host; CI runs on GitHub).
- [x] **1.5 Commit 1 Verification & Signoff**
  - [x] Verify fresh clone sequence: `make setup && make test` passes with ZERO manual steps. (OBSERVED 2026-09-05 via WSL: setup 6 passed + SMOKE OK; test ruff clean + mypy strict clean (3 files) + 6 passed.)

### Commit 2: Abstract Interfaces & Design Engine API Skeleton
- [x] **2.1 Core Abstract Interface Stubs** (OBSERVED 2026-09-05: gate green)
  - [x] Define abstract `Simulator` interface (typed, SI docstrings, raising `NotImplementedError`).
  - [x] Define abstract `LayoutBackend` interface (typed, SI docstrings, raising `NotImplementedError`).
  - [x] Define abstract `PDKAdapter` interface (typed, SI docstrings, raising `NotImplementedError`).
- [x] **2.2 Design Engine API Skeleton (`DesignEngine v0.1`)** (11 methods, keyword-only, version constant)
  - [x] Define `create_project()` signature and types.
  - [x] Define `create_cell()` signature and types.
  - [x] Define `instantiate()` signature and types.
  - [x] Define `validate()` signature and types (schema + connectivity + units + models).
  - [x] Define `netlist()` signature and types.
  - [x] Define `simulate()` signature and types.
  - [x] Define `check_constraints()` signature and types.
  - [x] Define `optimize()` signature and types.
  - [x] Define `run_drc()` signature and types.
  - [x] Define `extract()` signature and types.
  - [x] Define `compare()` signature and types.
- [x] **2.3 Physical Units Module Skeleton**
  - [x] Create units module stub (strictly empty of domain logic in Stage 0).
- [x] **2.4 Commit 2 Automated Tests**
  - [x] Implement pytest suite asserting interface stubs raise `NotImplementedError` and have valid type annotations. (12 passed; ruff clean; mypy strict clean, 13 files.)
- [ ] **2.5 Stage 0 Completion Verification**
  - [ ] Human verification of stranger-runs-this command sequence and committed API signatures.

---

## Future Stages Roadmap (High-Level Checklist)

- [ ] **Stage 1 — Circuit Kernel (Decomposed into Commits 1A–1G)**
  - [ ] **Commit 1A**: Typed SI unit system (`Quantity`, `Farad`, `Ohm`, `Volt`, etc.) + boundary converters $\to$ unit tests.
  - [ ] **Commit 1B**: Minimal SQLite schema/entities (Project, Library, Cell, Symbol, Instance, Port, Net) $\to$ schema migration tests.
  - [ ] **Commit 1C**: Design connectivity graph & net representation $\to$ connectivity tests.
  - [ ] **Commit 1D**: Deterministic canonical ordering & canonicalization $\to$ canonical-hash tests.
  - [ ] **Commit 1E**: SPICE netlist compiler $\to$ expected netlist tests.
  - [ ] **Commit 1F**: Pre-simulation validator (schema + connectivity + unit + model binding) $\to$ invalid-design rejection suite.
  - [ ] **Commit 1G**: Hand-built NMOS golden fixture netlist $\to$ 🔴 **HUMAN CHECKPOINT**: Hand-verified NMOS golden reference netlist.
  - [ ] ChatGPT Plus adversarial test authoring pass.
- [ ] **Stage 2 — Simulation Kernel**
  - [ ] `NgspiceBackend` implementation using `libngspice` C API.
  - [ ] Local single-machine `Job` runner with **worker-process isolation architecture from Day One** (`Job Scheduler -> Worker Process -> libngspice instance`).
  - [ ] SQLite execution status ledger.
  - [ ] Canonical 4-part reproducibility hash system (`design_identity_hash`, `execution_environment_hash`, `reproducibility_id`, `comparison_policy_id`).
  - [ ] Waveform parser returning SI-typed data structures.
  - [ ] Multi-worker process isolation & concurrency validation suite (1-, 2-, 4-job workloads asserting zero cross-run state contamination).
  - [ ] 🔴 **HUMAN CHECKPOINT**: First inverter transient waveform PNG verification.
- [ ] **Stage 3 — Measurement & Specification Engine**
  - [ ] Formal `MetricContract` matrix definition.
  - [ ] Implement 7 canonical metrics one by one (DC/AC gain, bandwidth, PM, slew, power, offset, settling).
  - [ ] 🔴 **HUMAN CHECKPOINT**: Hand-calculation verification once per metric contract.
  - [ ] Specification pass/fail, soft objective, and weighted objective evaluation.
- [ ] **Stage 4 — Optimization Layer**
  - [ ] `Optimizer` interface & `OptunaOptimizer` implementation.
  - [ ] Experiment Ledger recording every trial (success and failure).
  - [ ] Common-source amplifier reproducible sizing against specification.
  - [ ] 🟡 **HUMAN CHECKPOINT (Advisory)**: Search-space boundary or rapid convergence audit.
- [ ] **Stage 4.5 — Robustness**
  - [ ] PVT corner definitions bound to PDKAdapter.
  - [ ] Monte Carlo sampling using authentic PDK variation models.
  - [ ] Versioned `StatisticalProtocol` definition.
  - [ ] 🔴 **HUMAN CHECKPOINT**: Mandatory signoff on any statistical percentage headline.
- [ ] **Stage 5 — AI Diagnostics & Copilot**
  - [ ] Deterministic failure classifier based on 12-category taxonomy.
  - [ ] Grounded explainer with strict citation check (returns refusal if uncited).
  - [ ] `LLMProvider` implementation with `GeminiProvider` and `MockProvider`.
  - [ ] `AIAction` provenance logging.
- [ ] **Stage 6 — Topology Intelligence**
  - [ ] Parametric topology templates for 6 standard analog building blocks.
  - [ ] Experiment Ledger retrieval linking templates to sizing history.
  - [ ] LangGraph state machine for AI proposals.
  - [ ] 🔴 **HUMAN CHECKPOINT**: Mandatory human approval for every topology proposal.
- [ ] **Stage 7 — Schematic UI**
  - [ ] Interactive UI client calling `DesignEngine v0.1` API exclusively.
  - [ ] Playwright automated equivalence test (UI vs Python API netlist hash match).
- [ ] **Stage 8 — Physical Design**
  - [ ] Single-device backend technology spike (KLayout vs Magic vs Netgen).
  - [ ] `LayoutBackend` PCell placement, DRC, and LVS flow.
  - [ ] 🔴 **HUMAN CHECKPOINT**: Visual layout inspection in KLayout on first clean DRC/LVS.
- [ ] **Stage 9 — Post-Layout Physical Verification Loop**
  - [ ] Extracted parasitics fed back to Stage 3 measurement engine.
  - [ ] Side-by-side pre- vs post-layout degradation reporting.
- [ ] **Stage 10 — Multi-PDK & Sandboxing**
  - [ ] Hard container sandboxing (CPU, memory, timeout, network limits).
  - [ ] Second PDK adapter integration (GF180 / IHP).
