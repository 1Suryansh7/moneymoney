# To-Do.md — Master Task & Execution Tracker

> **CRITICAL OPERATIONAL DIRECTIVE FOR ALL AGENTS**:  
> You MUST inspect and update this tracker **BEFORE** beginning any task or modifying any files, and update it again **IMMEDIATELY AFTER** completing any task. Mark tasks `[ ]` (pending), `[-]` (in progress), or `[x]` (completed). Never skip steps or batch multiple stages into a single prompt.

---

## Current Status Overview
- **Active Phase**: Pre-Stage-2 verification — code complete through Stage 1G, human verdicts open
- **Code Status**: ✅ Stage 0 (Commits 1–2 + EDA follow-up) and Stage 1 (Commits 1A–1G) committed, gate green (144 passed, ruff + mypy strict clean)
- **Blocking**: 🔴 2.5 (Stage 0 signoff) and 🔴 1G (golden reference) verdicts RE-OPENED — premature closure on instruction alone was a Law 1 breach (see Tasks_Comp.md history); only an evaluated CONFIRMED/REJECTED/INSUFFICIENT closes them. No Stage 2 work until then.

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

## Stage 0: Architecture & Packaging (Code complete 2026-09-05; 2.5 verdict pending)

> **Commit Granularity**: Must land as two separate, cleanly isolated commits per master plan §10 addendum.
> **Predecessor rule (ADR-015)**: Stage-0 EDA follow-up must go green BEFORE Stage 1G; no Stage 2 prompt before that.

### Commit 1: System Packaging & CI Smoke Test
- [x] **1.1 Container Specification (`Dockerfile`)** — layered per ADR-015; EDA follow-up GREEN 2026-09-05 (ngspice-47 lib+CLI, KLayout 0.30.12, Magic 8.3.683, Netgen 1.5.323, sky130A @1689ac3f; ADR-017).
  - [x] Pin exact base image (Python 3.11-slim-bookworm tag; digest recorded at build).
  - [x] Pin exact Python version (3.11 container authority; host 3.13 editing-only; eda image: 3.11.15 deadsnakes).
  - [x] Pin ngspice with shared library (`libngspice`) build — VERIFIED: libngspice.so.0.0.16 loads via ctypes; CLI 47 built separately (ngshared yields lib-only, observed).
  - [x] Pin SkyWater 130nm PDK primitive device models — VERIFIED: sky130A primitive-only @1689ac3f (fd_pr 403964dc); nodeinfo.json in /pdk-record.
  - [x] Pin KLayout (0.30.12 VERIFIED: Ubuntu-22 deb, MD5-checked, `klayout -b -v` green).
  - [x] Pin Magic (8.3.683) and Netgen (1.5.323) — VERIFIED from source (live-latest per human directive; PREREQUISITES values superseded).
- [x] **1.2 Container Orchestration (`docker-compose.yml`)** — `app` (base, verified) + `app-eda` (`eda` profile, VERIFIED green).
  - [x] Configure local volume mounts, user UID/GID mapping.
- [x] **1.3 Makefile Automation** — exactly `[setup, test, run-example]` (asserted in test).
  - [x] Implement `make setup` (build container, run pytest + smoke inside container).
  - [x] Implement `make test` (ruff + mypy strict + pytest, all inside container).
  - [x] Implement `make run-example` (baseline smoke verification).
- [x] **1.4 CI Smoke Test Pipeline**
  - [x] Create GitHub Actions workflow (`.github/workflows/ci.yml`) to build container and run `make test`.
  - [x] Validate `act` configuration for local CI execution — VERIFIED 2026-09-05: act 0.2.89 installed (WSL ~/.local/bin), full `act -j smoke` green locally.
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
- [x] **2.5 Stage 0 Completion Verification** — CONFIRMED by human 2026-09-05 (formal signoff record: 11 frozen signatures accepted; stranger protocol accepted).
  - [x] Human verification of stranger-runs-this command sequence and committed API signatures.
- [x] **2.6 Stage-0 EDA follow-up** (was predecessor-blocked; GREEN 2026-09-05)
  - [x] EDA image builds with all acceptance probes passing; debt doc closed; PREREQUISITES refreshed; 1G/Stage 2 unblocked on the EDA front.

---

## Future Stages Roadmap (High-Level Checklist)

- [-] **Stage 1 — Circuit Kernel (Decomposed into Commits 1A–1G)** — code + 1G checkpoint CONFIRMED by human 2026-09-05
  - [x] **Commit 1A**: Typed SI unit system (`Quantity`, `Farad`, `Ohm`, `Volt`, etc.) + boundary converters $\to$ unit tests. (OBSERVED 2026-09-05: 99 passed, ruff+mypy-strict clean, 274 new lines. No parser per ADR-018.)
  - [x] **Commit 1B**: Minimal SQLite schema (Project, Library, Cell, Symbol, Instance, Port, Net + existence-only DesignRevision/Artifact) + migration tests. (OBSERVED 2026-09-05: 108 passed, ruff+mypy-strict clean, 308 new lines.)
  - [x] **Commit 1C**: Design connectivity graph & net representation $\to$ connectivity tests. (OBSERVED 2026-09-05: 113 passed, ruff+mypy-strict clean, 221 new lines. Facts only — 1F judges.)
  - [x] **Commit 1D**: Deterministic canonical ordering & canonicalization $\to$ canonical-hash tests. (OBSERVED 2026-09-05: 118 passed, ruff+mypy-strict clean, 229 new lines. Same circuit/different ids+order → one hash.)
  - [x] **Commit 1E**: SPICE netlist compiler $\to$ expected netlist tests. (OBSERVED 2026-09-05: 129 passed, ruff+mypy-strict clean, ~290 new lines. +migration v2 Parameter/Technology/ModelBinding. Declared pin_order consumed, never invented; generic TEST_* fixtures only.)
  - [x] **Commit 1F**: Pre-simulation validator (schema + connectivity + unit + model binding) $\to$ invalid-design rejection suite. (OBSERVED 2026-09-05: 140 passed, ruff+mypy-strict clean, 355 new lines. +migration v3 Specification hard/soft/weighted + Constraint + ErrorRecord taxonomy. Spec EVALUATION stays Stage 3.)
  - [x] **Commit 1G**: Hand-built NMOS golden fixture netlist. (OBSERVED 2026-09-05: 144 passed, ruff+mypy-strict clean. PDK-quoted X-model binding + migration v4 `kind`; hand-written `tests/golden/nmos.cir` byte-identical. W/L author-chosen for plausibility check.)
  - [x] **1G checkpoint verdict** — CONFIRMED by human 2026-09-05 (formal signoff: X prefix, d/g/s/b order, sky130_fd_pr__nfet_01v8, W=1e-06 m, L=1.5e-07 m hand-verified vs PDK deck).
  - [ ] ChatGPT Plus adversarial test authoring pass. (Unavailable in-session; covered by self-authored semantic-swap test + §8 audit. A human may run final_prompt.md second-model prompt manually.)
- [-] **Stage 2 — Simulation Kernel** — IN PROGRESS (2B→2H per decomposition; stop at first inverter waveform for human checkpoint)
  - [x] **2B**: SQLite migration v5 (`job`, `testbench`, `analysis` tables + FKs) + unit tests. (OBSERVED 2026-09-05: 148 passed, ruff+mypy-strict clean. Status vocabulary constrained; payload/result JSON text.)
  - [x] **2C**: `NgspiceBackend` ctypes wrapper over libngspice.so (SendChar/SendStat/ControlledExit callbacks). (OBSERVED 2026-09-05: base 152 passed + 4 explicit skips; EDA 156 passed, 0 skipped. ruff+mypy-strict clean. RC transient real: bare `out` naming (not CLI `v(out)`), bitwise-deterministic re-runs.)
  - [ ] **2D**: Local `Job` runner, worker-PROCESS isolation from Day One (no threads).
  - [ ] **2E**: Canonical reproducibility identity (4 SHA-256 concepts per §14.1).
  - [ ] **2F**: Waveform parser into SI-typed structures (`Volt`, `Second`, `Ampere`).
  - [ ] **2G**: Concurrency & isolation stress suite (1-, 2-, 4-job workloads).
  - [ ] **2H**: CMOS inverter fixture (PDK-quoted PMOS) + first transient + PNG.
  - [ ] 🔴 **HUMAN CHECKPOINT**: First inverter transient waveform verification.
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
