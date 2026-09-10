# To-Do.md — Master Task & Execution Tracker

> **CRITICAL OPERATIONAL DIRECTIVE FOR ALL AGENTS**:  
> You MUST inspect and update this tracker **BEFORE** beginning any task or modifying any files, and update it again **IMMEDIATELY AFTER** completing any task. Mark tasks `[ ]` (pending), `[-]` (in progress), or `[x]` (completed). Never skip steps or batch multiple stages into a single prompt.

---

## Current Status Overview
- **Active Phase**: Stage 3 — Measurement & Specification Engine (100% COMPLETE & VERIFIED: 3A–3J all landed, 257 tests passing in EDA, all checkpoints confirmed)
- **Code Status**: ✅ Stages 0–3 committed & verified. Gate green (base 232 passed + 25 skips, ruff + mypy strict clean on 66 files; EDA 257 passed, 0 failed).
- **Blocking**: Ready for Stage 4 (Optimization Layer).

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
  - [x] Create [`DECISIONS.md`](file:///c:/MONEY/Cad/codeeahhhhhhh/DECISIONS.md) documenting ADR-001 through ADR-021.
- [x] **0.6 Stage 0 Prerequisite Specifications**
  - [x] Create [`PREREQUISITES.md`](file:///c:/MONEY/Cad/codeeahhhhhhh/PREREQUISITES.md) detailing exact pinned toolchain versions, WSL2 tuning, strict typing, MCP servers, and validation commands.
- [x] **0.7 Human Signoff of Phase 0** — CONFIRMED by human 2026-09-06.
  - [x] Present completed governance and prerequisite set to human for review.

---

## Stage 0: Architecture & Packaging (Code complete + 2.5 CONFIRMED 2026-09-05; EDA follow-up GREEN)

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

## Housekeeping (completed 2026-09-06, no stage scope)

- [x] **H1**: GitHub connection — `origin` → `RobinBroG/moneymoney`, branch `main`, all commits pushed (remote HEAD verified equal). Human to confirm Actions green + default branch.
- [x] **H2**: `actions/checkout@v4` pinned to immutable SHA `11d5960a…` (PGP-verified v4); act dry-run plans clean.
- [x] **H3**: Automated PDK W/L-minima checks — `circuit/pdk_limits.py` (nfet 3.6e-07/1.5e-07, pfet 4.2e-07/1.5e-07 m, extracted from pinned PDK bins); validator enforces as `schema`; unknown symbols unchecked. Evidence: base 205+20, EDA 225/225.
- [x] **H4**: Adversarial self-review per §14.5 (same-family, not independent): clean — no SI leaks, side doors, gate bypasses, byte-equality on sim output, fabricated numbers, or taxonomy violations. Nits recorded: cs_amp docstring lacks bin citation; 3A/3C over 400-line cap; dead `state["complex"]` flag; `.fft` in no-analysis guard list (not a real card; harmless).
- [x] **H5**: First GitHub CI run failed BOTH jobs at pytest cache-write teardown (all tests green) — container UID 1000 vs runner-owned files (Errno 13). Fix: hermetic caches (`-p no:cacheprovider`, ruff/mypy cache-dir → /tmp) + exact dep pins; proven via read-only-workspace replica + fresh `--no-cache` build. Evidence: base 205+20, EDA 225/225, ro-replica green. Remotely proven: GitHub ci #2 GREEN on the fix commit, #3–#5 GREEN after it.

---

## Future Stages Roadmap (High-Level Checklist)

- [x] **Stage 1 — Circuit Kernel (Decomposed into Commits 1A–1G)** — code + 1G checkpoint CONFIRMED by human 2026-09-05
  - [x] **Commit 1A**: Typed SI unit system (`Quantity`, `Farad`, `Ohm`, `Volt`, etc.) + boundary converters $\to$ unit tests. (OBSERVED 2026-09-05: 99 passed, ruff+mypy-strict clean, 274 new lines. No parser per ADR-018.)
  - [x] **Commit 1B**: Minimal SQLite schema (Project, Library, Cell, Symbol, Instance, Port, Net + existence-only DesignRevision/Artifact) + migration tests. (OBSERVED 2026-09-05: 108 passed, ruff+mypy-strict clean, 308 new lines.)
  - [x] **Commit 1C**: Design connectivity graph & net representation $\to$ connectivity tests. (OBSERVED 2026-09-05: 113 passed, ruff+mypy-strict clean, 221 new lines. Facts only — 1F judges.)
  - [x] **Commit 1D**: Deterministic canonical ordering & canonicalization $\to$ canonical-hash tests. (OBSERVED 2026-09-05: 118 passed, ruff+mypy-strict clean, 229 new lines. Same circuit/different ids+order → one hash.)
  - [x] **Commit 1E**: SPICE netlist compiler $\to$ expected netlist tests. (OBSERVED 2026-09-05: 129 passed, ruff+mypy-strict clean, ~290 new lines. +migration v2 Parameter/Technology/ModelBinding. Declared pin_order consumed, never invented; generic TEST_* fixtures only.)
  - [x] **Commit 1F**: Pre-simulation validator (schema + connectivity + unit + model binding) $\to$ invalid-design rejection suite. (OBSERVED 2026-09-05: 140 passed, ruff+mypy-strict clean, 355 new lines. +migration v3 Specification hard/soft/weighted + Constraint + ErrorRecord taxonomy. Spec EVALUATION stays Stage 3.)
  - [x] **Commit 1G**: Hand-built NMOS golden fixture netlist. (OBSERVED 2026-09-05: 144 passed, ruff+mypy-strict clean. PDK-quoted X-model binding + migration v4 `kind`; hand-written `tests/golden/nmos.cir` byte-identical. W/L author-chosen for plausibility check.)
  - [x] **1G checkpoint verdict** — CONFIRMED by human 2026-09-05 (formal signoff: X prefix, d/g/s/b order, sky130_fd_pr__nfet_01v8, W=1e-06 m, L=1.5e-07 m hand-verified vs PDK deck).
  - [ ] ChatGPT Plus adversarial test authoring pass. (Unavailable in-session; covered by self-authored semantic-swap test + §8 audit. A human may run final_prompt.md second-model prompt manually.)
- [x] **Stage 2 — Simulation Kernel** — COMPLETE 2026-09-06 (2B→2H + error-log hardening; first-waveform checkpoint CONFIRMED)
  - [x] **2B**: SQLite migration v5 (`job`, `testbench`, `analysis` tables + FKs) + unit tests. (OBSERVED 2026-09-05: 148 passed, ruff+mypy-strict clean. Status vocabulary constrained; payload/result JSON text.)
  - [x] **2C**: `NgspiceBackend` ctypes wrapper over libngspice.so (SendChar/SendStat/ControlledExit callbacks). (OBSERVED 2026-09-05: base 152 passed + 4 explicit skips; EDA 156 passed, 0 skipped. ruff+mypy-strict clean. RC transient real: bare `out` naming (not CLI `v(out)`), bitwise-deterministic re-runs.)
  - [x] **2D**: Local `Job` runner, worker-PROCESS isolation from Day One (no threads). (OBSERVED 2026-09-05: base 154 passed + 7 explicit skips; EDA jobs+sim 13 passed. One spawn process per job; timeout/cancel/crash-safe; races designed out, strict asserts.)
  - [x] **2E**: Canonical reproducibility identity (4 SHA-256 concepts per §14.1). (OBSERVED 2026-09-05: base 160 passed + 7 skips; EDA 167 passed, 0 skipped. Pure functions; backend `_identity` repointed; tolerance is policy, not identity.)
  - [x] **2F**: Waveform parser into SI-typed structures (`Volt`, `Second`, `Ampere`). (OBSERVED 2026-09-05: base 165 passed + 7 skips; EDA 172 passed, 0 skipped. Pure `parse_transient`; `#branch` → Ampere; non-finite → SimError.)
  - [x] **2G**: Concurrency & isolation stress suite (1-, 2-, 4-job workloads). (OBSERVED 2026-09-05: base 165 passed + 12 skips; EDA 177 passed, 0 skipped. Simultaneous diverse decks/seeds/sizes; exact attribution; SIGKILL containment. Fixed en route: double-encoded result JSON; crash-marking for pre-running deaths.)
  - [x] **2H**: CMOS inverter fixture (PDK-quoted PMOS) + first transient + PNG. (COMMITTED 2026-09-06: `sim/testbench.py` assembler + `sim/inverter.py` prototype builder; EDA 182 passed; plot reproduced deterministically.)
  - [x] 🔴 **HUMAN CHECKPOINT**: First inverter transient waveform verification. — CONFIRMED by human 2026-09-06 (rails 0–1.8V, correct inversion, 326 pts, EDA 182 passed).
- [x] **Stage 3 — Measurement & Specification Engine** — COMPLETE (3A–3J all committed & human-confirmed 2026-09-07)
  - [x] **3A**: Canonical `MetricContract` dataclass + 7-metric matrix + SQLite Migration v6 (`measurement` table) + tests.
  - [x] **3B**: AC small-signal & complex vector support in `NgspiceBackend` + `waveform.py` + tests.
  - [x] **3C**: Metric 1 — DC/AC Gain contract + Common-Source benchmark + tests.
  - [x] 🔴 **HUMAN CHECKPOINT**: DC/AC Gain hand-calculation verification. — CONFIRMED by human 2026-09-06 (DC 9.1061 == AC 9.1059 V/V, rel_diff 0.0000 < 0.05; base 196+19, EDA 215/215).
  - [x] **3D**: Metric 2 — Bandwidth contract + -3dB crossing extraction + tests. (COMMITTED 2026-09-06: `metrics/bandwidth.py` UGB interp + `tests/test_bandwidth.py`; EDA UGB 2.07e7 Hz @1pF; base 200+20, EDA 220/220.)
  - [x] 🔴 **HUMAN CHECKPOINT**: Bandwidth hand-calculation verification. — CONFIRMED by human 2026-09-06 (0dB-absolute reading, declared 1pF load).
  - [x] **3E**: Metric 3 — Phase Margin contract + return-ratio / loop-gain benchmark + tests. (COMMITTED 2026-09-07: `metrics/phase_margin.py` + `sim/testbench.py` Tian loop; base 209+21, EDA 230/230).
  - [x] 🔴 **HUMAN CHECKPOINT**: Phase Margin hand-calculation verification. — CONFIRMED by human 2026-09-07 (PM 83.37 deg @1pF load, DC-trip slope match <5%).
  - [x] **3F**: Metric 4 — Slew Rate contract + step transient extraction + tests. (COMMITTED 2026-09-07 `0d4eff6`: `metrics/slew_rate.py` + `sim/testbench.py` step response).
  - [x] 🔴 **HUMAN CHECKPOINT**: Slew Rate hand-calculation verification. — CONFIRMED WITH NOTE 2026-09-07 (unloaded 4.96e11 V/s, loaded 8.32e9 V/s @50fF).
  - [x] **3G**: Metric 5 — Power contract + supply current averaging + tests. (COMMITTED 2026-09-07 `032e6a7`: `metrics/power.py`, branch sign probed on 1k load; live inverter 0.55 µW steady to 0.5%).
  - [x] 🔴 **HUMAN CHECKPOINT**: Power hand-calculation verification. — CONFIRMED by human 2026-09-07 (0.55 µW inverter power, probed sign convention).
  - [x] **3H**: Metric 6 — Offset contract + differential DC balance + tests. (COMMITTED 2026-09-07 `cc827b4`: `metrics/offset.py` Vid-at-Vod-zero + `sim/diff_pair.py` mirror-load fixture; symmetric 1.9e-10 V, 2:1 mismatch −77 mV correct sign.)
  - [x] 🔴 **HUMAN CHECKPOINT**: Offset hand-calculation verification. — CONFIRMED by human 2026-09-07 (symmetric 1.9e-10 V, 2:1 mismatch -77 mV).
  - [x] **3I**: Metric 7 — Settling Time contract + error-band staying extraction + tests. (COMMITTED 2026-09-07 `6e11964`: `metrics/settling_time.py` last-violation + staying rule + `assemble_closed_loop_step`; live ts=26.2 ns @1pF. Unloaded settles in 20 ps via source feedthrough — benchmark declared loaded.)
  - [x] 🔴 **HUMAN CHECKPOINT**: Settling Time hand-calculation verification. — CONFIRMED by human 2026-09-07 (26.2 ns @ 1 pF, feedthrough finding verified).
  - [x] **3J**: Specification evaluation (hard pass/fail, soft scoring, weighted Figure-of-Merit). (COMMITTED: `metrics/evaluator.py` over `constraint_rule` rows + `tests/test_evaluator.py`, pure-logic base-green. No checkpoint due.)
- [x] **Stage 4 — Optimization Layer** — COMPLETE (4A–4D; demo green, no advisory trigger)
  - [x] `Optimizer` interface & `OptunaOptimizer` implementation. (4B ask/tell ABC + SI SearchSpace; 4C seeded TPE, determinism proven without sims; optuna==5.0.0 plan-mandated dep.)
  - [x] Experiment Ledger recording every trial (success and failure). (4A migration v7 `experiment` table; 4B ledger writer/reader; failed trials recorded with failure class.)
  - [x] Common-source amplifier reproducible sizing against specification. (4D: 8-trial study seed 7, winner trial 5 w_n=2.198µm w_p=5.019µm, gain 9.139, UGB 13.44 MHz, spec passed; winner re-simulated within 1e-6; base 243+26, EDA 269/269.)
  - [x] 🟡 **HUMAN CHECKPOINT (Advisory)**: Search-space boundary or rapid convergence audit. — NOT TRIGGERED (winner interior on both axes; 8-trial seeded-TPE startup, no order-of-magnitude jump claimed).
- [x] **Stage 4.5 — Robustness** — COMPLETE (4.5A–4.5C; envelope + MC report green, yield checkpoint CONFIRMED 2026-09-07)
  - [x] PVT corner definitions bound to PDKAdapter. (4.5A: `Corner` SI dataclass + 5-envelope + 45-matrix (defined only) + deck plumbing; live TT/FF/SS/FS/SF matrix, UGB_FF 63M > UGB_SS 12M, per-corner ledger rows.)
  - [x] Monte Carlo sampling using authentic PDK variation models. (4.5B: ngspice-native MC proven unseedable across workers → seeded geometric perturbation with declared sigmas; PDK corner files + bins retained for PVT.)
  - [x] Versioned `StatisticalProtocol` definition. (4.5C: frozen dataclass N/seeds/corners/supplies/temps/mechanisms/method/thresholds/CI + pure Wilson CI + report builder. Live N=8 DC-gain MC report.)
  - [x] 🔴 **HUMAN CHECKPOINT**: Mandatory signoff on any statistical percentage headline. — CONFIRMED by human 2026-09-07 (N=8, 8/8, CI 0.676–1.000 @95%; thin-N caveat noted).
- [x] **Stage 5 — AI Diagnostics & Copilot** — COMPLETE (5A–5C; demos green, advisory noted below)
  - [x] Deterministic failure classifier based on 12-category taxonomy. (5A: prefix/category/spec mapping, fail-closed on unknown; `ai/taxonomy.py`.)
  - [x] Grounded explainer with strict citation check (returns refusal if uncited). (5C: substring citation semantics, refusal string exact, provenance-first; failed-run + opt-run Mock demos.)
  - [x] `LLMProvider` implementation with `GeminiProvider` and `MockProvider`. (5B: stdlib-urllib transport, injectable for tests; Mock deterministic; aliases resolve explicit > env > config, UNCONFIGURED fails closed.)
  - [x] `AIAction` provenance logging. (5A migration v8; every call — including refusals — records before returning.)
  - [x] Residency guard + secret filter. (5B: DISABLED/LOCAL_ONLY(default)/HOSTED_ALLOWED, opt-in records, immediate reversion, redaction; base 276+28.)
  - [x] 🟡 **Advisory (AI explanations)**: explainer narrations cite actual IDs or refuse — NOT TRIGGERED as a failure (refusal path proven by test); first live hosted narration remains new-pattern evidence when a key exists.
- [-] **Stage 6 — Topology Intelligence** — 6A–6C verified; 6D reworked as 6E (sim-grounded) then sized to spec in 6F; awaiting human signoff
  - [x] Parametric topology templates for 6 standard analog building blocks (6A `3bbc21b`).
  - [x] Experiment Ledger retrieval linking templates to sizing history + AI-03 adversarial ranking (6B `68c8c14`).
  - [x] `CandidateCircuitIR` and proposal state machine with immediate `ai_action` provenance (6C `9eceb1c`).
  - [x] Two-stage Miller verification reworked simulator-grounded (6E `ababde1`): analytical estimator deleted (fail-closed), single-ended AC drive, phasors rebuilt from complex_vectors, taxonomy-worded errors, DB commit fixes worker lock. Gates: base 305+29, EDA 334 passed.
  - [x] Real-sim Optuna sizing push to spec (6F): expanded 12-dim space (L params), PM-aware cost, per-trial failure tolerance (failed trials recorded, never abort). Winner MEASURED gain 75.16dB / UGB 62.41MHz / PM 152.4deg — all spec targets pass. 🟡 Advisory: winning Rz=7953Ω sits at the 8000Ω bound; PM margin (+92deg) makes it moot — proceeding flagged.
  - [x] Phase 0 Step 1 (VERIFY-PM-001): unwrap-first signed PM (`d494d7c`, ADR-027). Old 6F PM 152.4 re-measured live at +27.58 MARGINAL — kind story confirmed, committed PASS refuted (180-27.58=152.42 closes exactly). Contract aligned to lag formulation; wrap suite permanent in CI.
  - [x] Phase 0 Step 2 re-baseline: 16-trial wide re-run (best cost 214.71, no close) + 20-trial physics-focused study (seed 200, gm2-boosted W_out, Rz~=1/gm2, Cc 0.8-1.5pF). Empirical winner trial 17 MEASURED gain 81.30dB / UGB 16.58MHz / PM 63.64deg — gain+PM honestly pass, UGB shorts 40MHz. Demo rewritten to honesty properties (no spec assertions). Near-miss trial 9 (38dB/32.4MHz/57.7°) recorded as future direction.
  - [x] 🔴 **HUMAN CHECKPOINT**: re-baselined proposal (gain+PM pass, UGB short) + re-close decision executed per verdict (adopt empirical winner, ADR-028). — CONFIRMED by human 2026-09-09: accept Trial-17 as honest empirical baseline (gain 81.30dB PASS, PM 63.64° PASS, UGB 16.58MHz shortfall recorded); push to origin/main authorized.
- [x] **Stage 7A — Architecture Lockdown** (`8f51c90`, `2d25985`, `06669bb`; base 325+30)
  - [x] 7A-1 `EngineV01` strangler facade: project/cell/instantiate/validate/netlist/simulate/connect delegate to existing modules; ABC 11-method surface untouched (v0.1 intact; extensions concrete-only); remainder raise NotImplementedError with defer owners, pinned by tests. EDA engine file 8 passed incl live RC deck.
  - [x] 7A-2 Law 4 boundary CI guard: AST test fails ui/cli/sdk surfaces importing engine-side internals; engine-side + suite explicitly out of scope (strangler direction); checker self-proven incl documented relative-import blind spot.
  - [x] 7A-3 migration v9: `checkpoint_registry` (blocking/advisory, five-vocabulary verdicts) + `design_state` (ten-state CHECK, per-cell UNIQUE, FK cascade); v8 upgrade preserves data; pin 8→9 acknowledged alongside genuine migration. Writers deferred to callers.
  - [x] 🔴 **HUMAN CHECKPOINT**: Step-2 re-close verdict CONFIRMED 2026-09-09 (accept Trial-17) — push gate lifted by human.
- [-] **Stage 7B — HTTP API service** (7B-1 `03635a8`, 7B-2a `1cc858f`, 7B-2b `5b8c80d`, 7B-3 `ca155c4`)
  - [x] 7B-1 pins: fastapi 0.141.1 + uvicorn 0.52.4 runtime, httpx2 2.12.0 dev (httpx rejected: starlette TestClient trips deprecation-as-error); image rebuild evidence green.
  - [x] 7B-2 service skeleton: lifespan-managed app factory, routes for health/projects/cells/instantiate/validate/netlist/simulate (engine-implemented only); taxonomy-preserving error map; SimError/version re-exported through engine surface; AST guard extended to `api/` + own-package allowance; threaded-server tests over real localhost HTTP.
  - [x] Threading found live by the suite: RLock-serialized engine/job ledger over check_same_thread=False (store.connect additive kwarg); documented one-in-flight-sim limit until R0 scheduler.
  - [x] 7B-3 thin slice: HTTP validate/netlist (base) + live transient sim parsed to rail-to-rail inversion assertions (EDA 2 passed in 21s). Gates: base 331+31.
  - [x] 7B-4 job observability (`f949200`): concrete-only `list_jobs`/`job_result` (ABC untouched); routes GET /jobs + GET /jobs/{job_id} with 404 mapping; base seeds ledger rows directly, EDA reads back a live RC sim through both routes. Gates: base 334+32, EDA jobs file 4 passed.
  - [x] 7B-5 Path-B cell browser + schematic routes: concrete-only `EngineV01.list_cells`/`schematic` (Law 4: api/ may import engine-side only, so serialization lives on the facade, ABC untouched); GET /cells + GET /cells/{cell_id}/schematic with SI-float parameters, NULL-net terminals surviving as empty-string nets, unknown cells 422 with taxonomy wording. Base 349+37 green.
  - [x] 7B-6 Path-B waveforms route: concrete-only `EngineV01.job_waveforms` (Option 1, dumb-frontend rule — no SPICE semantics in TypeScript); GET /jobs/{job_id}/waveforms serves tran SI samples with unit symbols or AC magnitude_db/phase_deg (wrapped, exactly as parsed); failed jobs surface stored taxonomy verbatim, unknowns 404. Base 353+38 green (live RC charging shape EDA-only).
  - [x] 7B-7 Path-B copilot route: concrete-only `EngineV01.explain_job`; POST /copilot/explain classifies the stored taxonomy error with the job as evidence, narrates via MockProvider only (hosted models refused until a human opt-in flow exists — residency law); AIAction row written before return, action_id on the wire; succeeded/unclassifiable fail closed with zero provenance rows. Base 357+38 green.
  - [x] 7B-8 Path-B demo testbench: concrete-only `EngineV01.run_demo_testbench` + POST /testbenches/run (single `inverter_tran` deck assembled server-side from the Stage 2 fixture so the Run button never authors netlists); unknown names 422, SimError-before-ValueError except-ordering (SimError subclasses ValueError — caught live by the suite). Base 359+39, EDA file 2 passed + 1 skip with live rail-to-rail inversion.
  - [x] 7B-9 cell rename: concrete-only `EngineV01.rename_cell` + POST /cells/{id}/rename (ABC untouched — template instantiation derives its own name, rename closes the loop for dialog naming). Base 364+40 green.
  - [-] **R0-4 Testbench Manager — measure** (first metric live)
  - [x] R0-4a `EngineV01.measure` dc_gain/ac_gain on inverter-shape cells only (structural allowlist, all else fail-closed); dual-analysis 10% cross-check; first Measurement rows in V/V; shared `_load_raw` refactor of job_waveforms path. MEASURED inverter 15.240/15.244 (agree 0.03%). Base 367+41; EDA measure + waveforms files 8 passed + 1 skip. Deferral test in test_engine_v01.py transparently updated (NotImplementedError → ValueError).
  - [x] R0-4b POST /measure + live Outputs gain: `measure_with_unit` (units from the canonical contract registry, never hardcoded) + route with SimError-first ordering; api.ts wrapper; run loop measures post-waveforms with warn-degradation; Explorer DC Gain row shows V/V + dB with MEASURED status (no spec claim). Base 371+42; EDA file 4+1; Playwright 4/4 (gain row 15.24 V/V live). Debugging note: two red runs were the 60s Playwright test timeout vs ~90s backend measure latency — fixed with test.slow(), no product change; CORS/hardware theories falsified with header + timing evidence.
  - [x] R0-4c bandwidth (contract unity-gain crossing, NOT -3dB): read off the same in-memory AC sweep, zero extra sims; persists only when the stimulus holds a crossing. Measured live: unloaded inverter still 6.52 V/V at 10 GHz, so inverter bandwidth honestly refuses per contract; first live number needs the cs_amp golden fixture (R0-4d). Caught and fixed own bug: unconditional extraction would have broken dc/ac measurement. UI attempts bandwidth post-gain (warn-degrades to NOT RUN). Base 371+43; EDA measure file 4+1; tsc 0; vite build green.
  - [x] R0-4d common-source testbench (the graduation milestone): second structural fingerprint (pair + vbias net) with the R0-3a bias recipe (0.9 V gate, 0.4–1.2 V sweep avoiding the M1-off trap); shared transfer helper, no duplicated flow. MEASURED CS 9.106/9.106 (4-decimal agreement), rails 0.037–1.800; bandwidth refuses (2.45 V/V @10GHz, declared-load testbench later). Base 371+45; EDA measure file 6+1. Diff-pair + optimizer-to-UI remain.
  - [x] Quick-wins debt batch: CORS origins tightened to the two loopback dev URLs (wildcard+credentials rejected by browsers); Misc.tsx signoff/metrics/margins fiction replaced with run-state truth + live Measured block; test_digital_gates.py deck assembly via assemble_transient (new additive extra_lines param; sample times remapped to helper Va edges). Base 371+42; tsc 0; vite build green; EDA gates + inverter files 8 passed.
  - [x] 3e canvas live: cell picker + `activeCellId`/`activeSchematic` in store (mount picks first non-anchor); deterministic auto-layout with W/L engineering notation; connectivity strip + neutral port markers instead of routed-wire fiction; toolbar counts + overlay + Check all live (POST /validate); empty state, no mock fallback. Playwright 4/4 incl. new canvas test (named cell → m1/m2 + counts + sky130 label).
  - [-] **Step 3 — Lovable-shell binding** (host toolchain found: node 25.6.0 / bun 1.3.8; `bun install` 408 pkgs; baseline `tsc --noEmit` clean, `vite build` green)
  - [x] 3a `src/ic/api.ts` typed transport client (13 endpoints, SI floats, no math) + `store.tsx` live run loop (POST /testbenches/run → poll ledger → waveforms into `liveWave`; phase-driven progress, run-token cancellation, backend reachability flag; fake setTimeout choreography deleted). `tsc --noEmit` + `vite build` green.
  - [x] 3b SimulationExplorer de-faked: `scaled()` + all fabricated numbers deleted (gain 67.41, post-layout table, fake MC yield, RUN_HISTORY/CompareTable); Live-Run table (phase/job/analysis/points/trace cursor readouts), metric rows honestly NOT RUN, history from the live ledger, MC Run inert with reason, Stop cancels the poll, sky130 labels. `tsc` + `vite build` green.
  - [x] 3c WaveformAnalyzer live: plots/markers/legend/browser derive from `liveWave` (data-driven extents, cursor reset per run, AC calculator gated on live AC); `waveforms.ts` fabrication file deleted (`Pt` inlined). `tsc --noEmit` exit 0 + `vite build` green.
  - [x] Push `a9f8e07..43599eb` (9 commits incl. human's own `43599eb` e2e+gates commit) to origin/main after base 361+40 gate + EDA gates proof (3 passed). Pre-push review of `43599eb`: honest gates/tests, EDA-proven NAND truth table; follow-ups recorded, not blockers.
  - [x] 3d NewCellDialog wired: project/cell/template → createProject → createCell → instantiate (backend defaults, `{}` params); live `cells` + `refreshCells` in store; busy/error states, backend 422 surfaced verbatim. `tsc` exit 0 + `vite build` green.
  - [x] 3d-fix dead toolbar button: GlobalToolbar "New Cell View" icon shipped with NO onClick (clicks into the void; found in 2 min by tracing openers). Wired to the same `setNewCell` as the File menu; dropped the false `Ctrl+N` hints (browser-reserved, unstoppable). Playwright proves all 3 e2e green in real Chromium (sim 326 pts/13 traces, cell create, toolbar-dialog regression).
  - [ ] Follow-ups (non-blocking): CORS `allow_origins *` + credentials combo in server.py is misconfigured (browsers reject) — tighten to localhost origins; `test_digital_gates.py` hand-rolled micron string-replaces should use `assemble_transient`; netlist asserts are substring, not golden byte-identical.
  - [ ] Next: workspace-by-workspace Lovable-shell wiring behind the boundary (per ADR-031); Playwright equivalence with first UI action.
- [-] **R0 Trust Core — AnalogBench** (R0-1 `ca588c7`; R0-2a `1695af6`, R0-2b `0e74696`; R0-3a `28be619`; base 346+37)
  - [x] R0-1 registry + runner + B0: eight benches B0–B7 with per-bench defer owners; B0 executes (build→validate→netlist→sim→swing via engine surfaces); BenchResult data on all paths (pass/fail/error, error carries taxonomy with zero sims); B1–B7 raise NotImplementedError. Full EDA 370 passed + 1 legit conditional skip (b0-nolib case) in 16.5 min.
  - [x] R0-2a B1 mirror (`sim/mirror.py` fixture + runner): pushed-into-diode bias (pulling to ground parks both devices OFF, observed live ~1e-12 A); sweep-source branch vector fail-closed on ambiguity; 0.8–1.2 saturation ratio at Vout=0.9 plus triode-ordering. MEASURED 1.025 with Early slope 0.82/1.18 and KCL-closed return. EDA bench file green.
  - [x] R0-2b B2 diff pair (runner): single-ended AC drive, both output gains via Stage 3 extractor over complex phasors; differential-action fingerprint MEASURED 8.075/0.536 — 3–30 mirror side plus under-2 diode side, bands structural not fitted. EDA bench file 8 passed + 3 skips.
  - [x] R0-3a B3 common-source amp (runner over new `sim/cs_amp.py` fixture + `BiasSearch`): missionary M1-off trap hit live (Vg=0.99 parks device OFF, gain -0.3), fixed by Vg sweep-load-line search; entry-bar trap avoided by fitting dc-then-ac at measured trip. MEASURED DC 9.102 == AC 9.087 within 10%, op trip 0.85V vs 1.31 pass band, rails 0.023–1.797. EDA bench file 10 passed + 4 skips.
  - [x] R0-3b B4 cascode (runner over new `sim/cascode.py` fixture): Vbcas search reversed live (1.1 rail-hugging beats intended 0.9 by +4 gain, physically correct — higher Vbcas maximizes swing); dual DC+AC assertions required (AC-only lies: 1.6 DC vs 13.5 AC through drain resistor). MEASURED DC 12.999 == AC 12.989 at trip 0.85V, clears same-size plain-CS 9.1 action threshold 10, headroom span 0.205V, rails 0.091–1.800. Base 346+37 green; EDA `-k b4` 2 passed + 1 legit skip in 75s. Pushed `28be619` + `a9f8e07` to origin/main — R0-3 CLOSED, B5–B7 stay deferred.
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
