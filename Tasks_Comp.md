# Tasks_Comp.md — Completed Tasks & Evidence Record

> Status ledger for everything built and verified to date. One row per
> commit: the single testable claim, what was proven, and the observed
> evidence. Every number below was observed in a tool run — nothing is
> projected or recalled. Open items live at the bottom, not mixed in.

Conventions: `make setup` = build base image + pytest + smoke (in-container).
`make test` = ruff + mypy(strict) + pytest (in-container). `make run-example`
= packaging smoke. Sanctioned shell: WSL2 Ubuntu (GNU Make 4.3,
Docker 29.6.2). Base Python 3.11.16; EDA Python 3.11.15.

## Phase 0 — Governance baseline (`0d9fbcc`)

Eight files, zero code: `AGENTS.md` (4 laws, units, taxonomy, checkpoints),
`DECISIONS.md` (ADR-001..014), `PREREQUISITES.md`, `To-Do.md`, `context.md`,
`final_build.md` (v3.2), `final_prompt.md` (v1.2), `final_prod.pdf`.

## Stage 0, Commit 1 — Packaging + CI (`ecda6f8`)

- Layered `Dockerfile` (`base` built; `eda` pins declared), `docker-compose.yml`
  (`app` + `app-eda` profile), `Makefile` with exactly `[setup, test, run-example]`
  (asserted by test), strict `pyproject.toml`, `config/models.json` capability
  aliases + no-network `scripts/check_models.py`, `examples/smoke.py`,
  `tests/test_smoke.py` (6 tests), CI workflow, `.gitattributes` LF guards.
- Evidence: `make setup` 6 passed + SMOKE OK; `make test` ruff clean +
  mypy strict clean + 6 passed. Upstream base resolved to
  `python:3.11-slim-bookworm@sha256:528257d4…`.

## Stage 0, Commit 2 — Interfaces + DesignEngine v0.1 (`598b2ba`)

- Abstract `Simulator` / `LayoutBackend` / `PDKAdapter` (typed, SI-docstringed,
  `NotImplementedError`), `DesignEngine` with exactly the 11 plan method names
  (keyword-only, version constant `ENGINE_API_VERSION = "0.1"`), empty `units`
  stub. Tests prove the STUB bodies raise (base-class invocation) and freeze
  the surface (any change fails with a bump-version message).
- Evidence: 12 passed, ruff + mypy-strict clean (13 files).

## Stage 0, audit fixes (`c102e58`)

- Self-audit per §14.5 after an unspecific REJECTED: F-1 Commit 2 added 443
  Python lines (over the 400 cap — recorded, process fix applied since);
  F-2 `make setup` never installed pre-commit hooks (documented why);
  F-3 smoke failures lacked taxonomy (now `SMOKE FAIL [taxonomy: Schema]`).
  Full record: `docs/stages/stage-0.md` §8.

## Stage 0, EDA follow-up (`e62ca18`) — image `app-eda` GREEN

Manifest `sha256:51ab1806…`. Recipe (Ubuntu 22.04 root): deadsnakes Python
3.11.15 (jammy archives carry an RC build — rejected), ngspice-47 source
(CLI + `--with-ngshared` lib build; ngshared yields lib-only, observed),
Magic 8.3.683 + Netgen 1.5.323 from tags, KLayout 0.30.12 Ubuntu-22 .deb
(MD5-checked), sky130A primitive-only @open_pdks `1689ac3f`
(fd_pr `403964dc`, nodeinfo.json in `/pdk-record`).
- In-build acceptance, all green: ngspice-47 banner, RC transient via
  `ngspice -b`, `libngspice.so.0.0.16` ctypes-loadable, KLayout 0.30.12,
  Magic 8.3.683 banner, netgen present, `sky130.lib.spice` present.
- Root-caused along the way (ADR-017 for ngspice 46→47: top-level `46/`
  folder does not exist; compose UNPINNED-stomp; global ARG scoping;
  `--enable-sky130-pdk` master switch missing from `--help` but honored by
  `scripts/configure`). CI gained an `eda` job (commands run verbatim
  locally — green). Upstream noise noted, not fixed: `git describe` fatal
  (shallow clone), `NODE elements not supported` spam, both non-blocking.
- Debt record `docs/stage-0-layered-debt.md` CLOSED (R-1..R-8 checked off);
  `PREREQUISITES.md` §3 refreshed to observed pins.

## Verification-only proofs (no commit)

- Fresh-clone gate: clean clone at `/tmp/stage0-fresh`, all three gates
  green (12 passed, ruff/mypy clean). Honest caveat: pip layers came from
  the shared daemon cache; cold base-pull was proven in the Commit 1 log.
- `act` 0.2.89 installed (WSL `~/.local/bin`); full `act -j smoke` green
  locally. CI YAML proven valid + step-equivalent (`make setup`, `make test`).

## Stage 1 — Circuit Kernel (all committed, gate green every step)

| Commit | Hash | Claim | Evidence |
|---|---|---|---|
| 1A units | `0e1f5c4` | `Quantity` + 8 SI types (finite-only), display formatter, NO parser (ADR-018) | 99 passed (87 new); `Hertz("10MHz")` raises `UnitError`; 274 lines |
| 1B schema | `08745af` | Migration framework (append-only, FK-enforcing) + 9 tables; behavior tables deferred with owners | 108 passed; 308 lines |
| 1C graph | `a4a61e2` | `ConnectivityGraph` facts (degrees, loose ports, sparse nets), no schema change | 113 passed; 221 lines |
| 1D canonical | `cb6f785` | Name-based canonical form + SHA-256; same circuit/different uuids → one hash | 118 passed; 229 lines |
| 1E compiler | `8b0847a` | Deterministic netlist compiler + v2 tables; declared pin_order consumed, TEST_* fixtures only | 129 passed; ~290 lines |
| 1F validator | `ccf5401` | Four-pillar gate + v3 tables (hard/soft/weighted, 12-category ErrorRecord); degree-1 allowed, degree-0/unconnected flagged | 140 passed; 355 lines |
| 1G golden | `46b3fe5` | PDK-quoted NMOS fixture + v4 `kind` (M/X); hand-written `tests/golden/nmos.cir` byte-identical; swapped-terminals adversarial test | 144 passed |

1G PDK evidence (read from the pinned image, quoted in `tests/test_golden.py`):
`.../libs.ref/sky130_fd_pr/spice/sky130_fd_pr__nfet_01v8__tt.pm3.spice` →
`.subckt sky130_fd_pr__nfet_01v8 d g s b` (model name, d/g/s/b order, subckt
kind ⇒ `X` prefix). W=1µm/L=150nm are author-chosen for the human
plausibility check, not PDK-quoted.

## Test-suite growth (observed)

Base (`make test`): 6 → 12 → 99 → 108 → 113 → 118 → 129 → 140 → 144 passed
(Stages 0–1, zero warnings throughout via `filterwarnings = error`),
then 167+14 (2G) → 168+14 (2H) → 170+16 (error-log hardening) →
196+19 (3A–3C) → 200+20 (3D) → 209+21 (3E) → 214+22 (3F) → 232+25 (3G–3J) → 243+26 (4A–4D) → 256+28 (4.5A–4.5C) → 276+28 (5A–5C). mypy strict clean throughout (13 → 29 →
52 → 57 → 66 → 72 → 80 → 89 files). EDA full suite: 182 (2H) → 186 (hardening) → 215 (3A–3C) →
220 (3D) → 230 (3E) → 236 (3F) → 257 (3G–3J) → 269 (Stage 4) → 284 (4.5A–4.5C) → 304 passed, 0 failed (5A–5C).

## Final pinned toolchain (all observed)

`python:3.11-slim-bookworm` (3.11.16) + Ubuntu 22.04 root; Python 3.11.15
(eda); ngspice-47 (CLI + libngspice.so.0.0.16); KLayout 0.30.12; Magic
8.3.683; Netgen 1.5.323; sky130A primitive-only @`1689ac3f`
(fd_pr `403964dc`); pytest 9.1.1, mypy 2.3.1, ruff 0.16.6.

## Stage 2 — Simulation Kernel (2A–2H + hardening, all committed)

| Commit | Hash | Scope | Status & Evidence |
|---|---|---|---|
| 2A docs | `67f0a73` | Stage 2 brief + continuity sync | `docs/stages/stage-2.md` created; `context.md` and `To-Do.md` synchronized |
| 2B schema | `83c53a0` | Migration v5 (`job`, `testbench`, `analysis`) | Implemented in `schema.py`; tests in `test_schema.py` |
| 2C backend | `7466709` | `NgspiceBackend` ctypes wrapper | Implemented in `sim/ngspice.py`, `sim/backend.py`; tests in `test_sim.py` |
| 2D runner | `0b5fcd4` | Worker-process isolation `JobRunner` | Implemented in `sim/jobs.py` (spawn process per job); tests in `test_jobs.py` |
| 2E reproduce | `72a6a96` | 4-part SHA-256 identity system | Implemented in `sim/reproduce.py`; tests in `test_reproduce.py` |
| 2F waveform | `8cc102b` | Typed SI waveform parser | Implemented in `sim/waveform.py`; tests in `test_waveform.py` |
| 2G stress | `a42285f` | 1-, 2-, 4-job concurrency suite | Implemented in `tests/test_stress.py`; isolates crashes and state leaks |
| 2H inverter | `f6aee05` | CMOS Inverter prototype & testbench | `sim/inverter.py`, `sim/testbench.py`, `examples/plot_inverter.py`; tests in `test_inverter.py`. Two root-caused fixes en route (taxonomy Netlist): (1) SI-meter W/L fail PDK binned-model lookup — geometry emits ×1e6 microns + `.option scale=1e-6` + `.param mc_mm_switch=0` (ADR-020, 2x2 scale experiment); (2) floating `vss` return coupled output above rail — explicit `VSS vss 0 DC 0`. Evidence: EDA 182 passed; `artifacts/inverter_transient.png` 326 pts vin 0–1.8 / vout −0.019–1.808; Stage 2 checkpoint CONFIRMED by human 2026-09-06 |
| post-2H hardening | `eecaef0` | ngspice log tail on all run-phase `SimError`s; pure-Python no-analysis guard | Failing decks execute only in workers (ADR-021: in-process error-path C calls segfault later runs — observed full-suite crash, deselect-proven). Evidence: base 170+16, EDA 186, no crash |

## Stage 3 — Measurement & Specification Engine (3A–3J committed & verified)

| Commit | Hash | Scope | Status & Evidence |
|---|---|---|---|
| 3A contracts | `d61c674` | `MetricContract` matrix (8 contracts) + Migration v6 (`measurement`) | `metrics/contract.py`, `metrics/__init__.py`; tests in `test_metrics.py` (frozen/unique/invariants, v6 FK + cascade) |
| 3B AC support | `cc8ab90` | Complex-vector capture + `ACWaveform`/`parse_ac` | `sim/ngspice.py` (`complex_vectors`), `sim/backend.py` + `sim/jobs.py` payload plumbing, `sim/waveform.py`; tests in `test_sim.py` + `test_waveform.py` |
| 3C gain | `9884494` | `extract_dc_gain` / `extract_ac_gain` + `cs_amp_nmos` fixture + DC-sweep/AC assemblers | `metrics/gain.py`, `sim/cs_amp.py`, `sim/testbench.py` (`assemble_dc_sweep`, `assemble_ac`, both honor ADR-020); tests in `test_gain.py`. Gain checkpoint CONFIRMED by human 2026-09-06 (DC 9.1061 == AC 9.1059 V/V, rel 0.0000 < 0.05; base 196+19, EDA 215/215) |
| 3D bandwidth | `43aaed6` | `extract_bandwidth` (unity-gain crossing, linear interp) | `metrics/bandwidth.py`; tests in `test_bandwidth.py` (exact crossings, first-crossing semantics, 7 rejections, live UGB). Bandwidth checkpoint CONFIRMED by human 2026-09-06 (UGB 2.07e7 Hz @ declared 1 pF load, 0dB-absolute reading; base 200+20, EDA 220/220). Load note: unloaded fixture pole sits beyond the 10 GHz sweep (gain 2.45 @10 GHz observed), so bandwidth is declared loaded — fixture untouched |
| 3E phase margin | `13bbe58` | `extract_phase_margin` via Tian loop gain + `assemble_loop_gain` | `metrics/phase_margin.py`, `sim/testbench.py` (`assemble_loop_gain`); tests in `test_phase_margin.py` (0 deg oscillator, 60 deg synthetic, 7 rejections, live Tian loop on `cs_amp_nmos`). Checkpoint CONFIRMED by human 2026-09-07; independently verified same day (PM 83.37 deg exact reproduce @1pF, UGF 26.8 MHz, trip-slope 8.7111 vs loop 8.7241 = 0.15%; base 209+21, EDA 230/230) |
| 3F slew rate | `0d4eff6` | `extract_slew_rate` (20%-80% rise/fall linear interp) + `assemble_step_response` | `metrics/slew_rate.py`, `sim/testbench.py` (`assemble_step_response`); tests in `test_slew_rate.py` (exact 1.8e9 V/s rise/fall, min(rise,fall), 5 rejections, live rail-to-rail step on `inverter`). Checkpoint CONFIRMED WITH NOTE by human 2026-09-07: unloaded 4.88e11 CONFIRMED by 0.1 ps refinement (4.96e11, within 1.8%); loaded figure corrected to 8.32e9 observed twice bitwise (checkpoint text 1.80e10 did not reproduce) |
| 3G power | `032e6a7` | `extract_power` (VDD·mean(−Ibranch), branch sign probed on 1 kΩ load) | `metrics/power.py`; tests in `test_power.py` (exact DC/sine/window, 5 rejections). Checkpoint CONFIRMED by human 2026-09-07; independently verified (live inverter 0.55 µW steady to 0.5% over 5 periods) |
| 3H offset | `cc827b4` | `extract_offset` (Vid at Vod zero) + `diff_pair_nmos` fixture (mirror load) | `metrics/offset.py`, `sim/diff_pair.py`; tests in `test_offset.py` (exact 3 mV crossing, 5 rejections). Checkpoint CONFIRMED by human 2026-09-07; independently verified (symmetric 1.9e-10 V; 2:1 mismatch −77 mV correct sign) |
| 3I settling | `6e11964` | `extract_settling_time` (last violation + staying rule) + `assemble_closed_loop_step` | `metrics/settling_time.py`, `sim/testbench.py`; tests in `test_settling_time.py` (exact 4.6052 ns exponential, staying-spike semantics, 6 rejections). Checkpoint CONFIRMED by human 2026-09-07; independently verified (live ts=26.2 ns @1pF; unloaded 20 ps is source feedthrough, benchmark declared loaded) |
| 3J evaluator | `2443152` | hard/soft/weighted evaluation over `constraint_rule` rows | `metrics/evaluator.py`; tests in `test_evaluator.py` (tolerance edges, soft fractions, FOM, fail-closed). Pure logic, base-green. No checkpoint due |


## Stage 4.5 — Robustness (4.5A–4.5C committed; yield checkpoint CONFIRMED 2026-09-07)

| Commit | Scope | Status & Evidence |
|---|---|---|
| 4.5A corners | Corner axis + deck plumbing + live 5-corner matrix | `docs/stages/stage-4.5.md`, `robust/corner.py` (SI K/V, 5-envelope + 45-matrix defined-only), `sim/testbench.py` corner params (`.temp`/`.lib`/VDD; corner without libs fails closed); `tests/test_corner.py` + `tests/test_pvt_sim.py`. Live TT 9.106/20.7M (reproduces nominal exactly), FF 63.1M > SS 12.0M monotonic, per-corner ledger rows |
| 4.5B sampler | Seeded geometric MC sampler (ngspice-native proven unseedable) | `robust/mc_sampler.py` (per-(seed,sample) streams, declared relative sigmas — protocol parameters, not foundry data); spike table in `tests/test_mc_spike.py` (mc=1 varies ~6%, setseed repeats fail). Verified green standalone at its commit via isolated worktree |
| 4.5C protocol | StatisticalProtocol + Wilson CI + report builder | `robust/protocol.py` (N/seeds/corners/supplies/temps/mechanisms/method/thresholds/CI; stdlib NormalDist, no SciPy); `tests/test_protocol.py` (validation, Wilson goldens, synthetic reports). Live N=8 DC-gain MC report: 8/8 pass, CI [0.676, 1.000] @95%. Yield checkpoint CONFIRMED by human 2026-09-07 (thin-N caveat noted) |


## Stage 4 — Optimization Layer (4A–4D committed, demo green)
| Commit | Scope | Status & Evidence |
|---|---|---|
| 4A brief+schema | Stage brief + Migration v7 (`experiment` ledger) | `docs/stages/stage-4.md`; `store/schema.py` v7; `test_schema.py` (round-trip, vocab CHECKs, job-delete SET NULL) |
| 4B interface | Ask/tell `Optimizer` ABC + SI `SearchSpace` + ledger writer | `optimize/optimizer.py`, `optimize/ledger.py`; `tests/test_optimize.py` (fake-optimizer determinism, ledger failures recorded) |
| 4C optuna | Seeded TPE `OptunaOptimizer` (+ plan-mandated `optuna==5.0.0` dep) | `optimize/optuna_optimizer.py` (strict FIFO ask/tell pairing); determinism proven without sims |
| 4D demo | Live cs_amp sizing: 8-trial study seed 7 vs hard spec (gain≥8, UGB≥10MHz) | `tests/test_optimize_demo.py` (worker sims with timeouts; every trial a `job`+`experiment` row). Winner trial 5: w_n=2.198µm, w_p=5.019µm, gain 9.139, UGB 13.44 MHz, spec passed; interior on both axes (advisory NOT triggered); winner re-simulated within 1e-6. Base 243+26, EDA 269/269 |


## Stage 5 — AI Diagnostics & Copilot (5A–5C COMMITTED & PUSHED `02b3c5b`)

| Commit | Scope | Status & Evidence |
|---|---|---|
| 5A classifier (`6aea310`) | Deterministic taxonomy classifier + migration v8 (`ai_action`) | `ai/taxonomy.py` (12-category order, prefix/category/spec mapping, fail-closed); `ai/actions.py` (provenance writer); `tests/test_ai_classify.py` |
| 5B provider (`7f57ecd`) | `LLMProvider` (Gemini stdlib-urllib + Mock) + residency guard + secret filter | `ai/provider.py` (alias resolution explicit > env > config, injectable transport, malformed replies fail closed); `ai/residency.py` (DISABLED/LOCAL_ONLY/HOSTED_ALLOWED, opt-in records, immediate reversion, redaction); `tests/test_ai_provider.py` (zero network) |
| 5C explainer (`02b3c5b`) | Grounded explainer + Mock demos | `ai/explainer.py` (classify→retrieve→generate→substring citation check→refuse; AIAction before return, refusals included; `hosted` flag routing); `tests/test_ai_explain.py` (cited narration, empty/uncited refusal, unknown-ID fail-closed, DISABLED block). Advisory noted, never triggered as failure |

## Stage 6 — Topology Intelligence & Knowledge Base (6A–6D COMMITTED & VERIFIED)

| Commit | Scope | Status & Evidence |
|---|---|---|
| 6A templates (`3bbc21b`) | Canonical Topology Template Library (6 standard blocks) | `topology/templates.py`: `current_mirror`, `diff_pair`, `common_source`, `cascode`, `folded_cascode`, `two_stage_miller`. Relational SQLite instantiation strictly in SI base units; `tests/test_topology_templates.py` (15 tests passing: pre-sim validation, connectivity, determinism) |
| 6B retriever (`68c8c14`) | Knowledge Base linkage & AI-03 Multi-Criteria Retriever | `topology/knowledge_base.py` + `topology/retriever.py`: aggregates empirical trials and yield; multi-criteria scoring $S = w_{\text{spec}}s_{\text{spec}} + w_{\text{top}}s_{\text{top}} + w_{\text{yield}}Y - w_{\text{fail}}F$; `tests/test_topology_retriever.py` (4 tests passing, including mandatory AI-03 adversarial test rejecting failed sizings) |
| 6C proposal (`9eceb1c`) | `CandidateCircuitIR` & Proposal State Machine | `topology/proposal.py`: immutable proposal IR, immediate `ai_action` logging, fail-closed pre-sim validation gate, human decision gate (`decide_proposal`). `tests/test_topology_proposal.py` (5 tests passing) |
| 6D demo | Two-Stage Miller Op-Amp Sizing & Proposal Workflow Demo | `sim/miller_opamp.py`: AC deck assembly, analytical & SPICE evaluators, Optuna sizing against 60dB/40MHz, blocking human checkpoint alert block. `tests/test_stage6_demo.py` (5 passed, 1 live skipped). Suite total: 305 passed, 29 skipped |

## CI post-mortem 2026-09-06 (first-ever GitHub run, both jobs red)

- Symptom: `smoke` failed in 44 s, `eda` in 14 m 07 s — both at pytest
  cache-write teardown with `PermissionError: Errno 13` on
  `/workspace/pytest-cache-files-*`, AFTER all tests passed (98%+ dots, zero
  failures; EDA image build + acceptance probes fully green).
- Root cause: `docker-compose.yml` runs the container as UID 1000, but
  GitHub checks out files owned by the runner UID (1001) — /workspace is
  read-only for the test user. Locally the developer UID is 1000, so the
  skew never manifests; CI had only ever run locally via `act`.
- Fix (product-level, runner-agnostic): hermetic caches — pytest
  `-p no:cacheprovider`, ruff `cache-dir` + mypy `cache_dir` → /tmp
  (`pyproject.toml`); exact dev pins (`==`) so fresh builds resolve
  identically. Proven by read-only-workspace replica (`docker run :ro`:
  reproduced pre-fix, green post-fix for pytest+ruff+mypy) and a fresh
  `--no-cache` base build (205+20, ruff+mypy clean).
- Never-again: gates must never depend on workspace writability (replica
  recipe above); fresh builds must resolve hermetically; first GitHub run
  of any workflow change gets watched, not assumed.

## NOT done (open, owned)

1. **Stage 8+ physical design** — KLayout/Magic/Netgen backend spike, PCell placement, DRC/LVS flow, then Stages 9–10 per `planchanges.md`.
2. **CI Actions observation** — Confirm smoke/eda runs are green in the GitHub Actions tab.

## 2026-09-15 — Stage 7 UI-API Equivalence Proof (Playwright E2E green)
- Automated Playwright end-to-end equivalence test (`UI design 1/e2e/cockpit.spec.ts:217`):
  - User creates `common_source` cell via the Cockpit UI `NewCellDialog`.
  - Backend compiles UI-instantiated cell via `POST /netlist`.
  - Independent direct instantiation executed purely via Engine API (`POST /cells` + `POST /instantiate`).
  - Byte-identical netlist equality (`expect(uiNetlist).toBe(apiNetlist)`) and matching Sky130 model bindings (`sky130_fd_pr__nfet_01v8`, `sky130_fd_pr__pfet_01v8`) verified live in real Chromium in 5.3s.
- Stage 7 done-when criterion formally satisfied.

## 2026-09-15 — Golden netlist byte-identical asserts (Error 2, base + EDA green)
- Replaced substring asserts with byte-identical golden comparisons against hand-verified reference netlists:
  - `tests/golden/not_gate.cir`: CMOS inverter (Xmn1 pull-down, Xmp1 pull-up, Sky130 1.8V, W/L in meters, LF-only).
  - `tests/golden/nand_gate.cir`: 2-input NAND (series NMOS stack out→mid→vss, parallel PMOS to vdd).
  - `tests/golden/miller_ac.cir`: Two-stage Miller AC deck (single-ended 1.0V AC drive Vip, Vin AC 0, Xcc + Xrz, 2.0p load).
  - `tests/test_inverter.py`: Inline byte-exact assertion for micron-scaled deck with `.option scale=1e-6`.
- Human Checkpoint CONFIRMED: electrical correctness, pin order, W/L in meters, single-ended AC drive verified.
- Evidence: `test_digital_gates.py`, `test_inverter.py`, `test_stage6_demo.py` all green (15 passed in 249.20s). Full base gate clean.

## 2026-09-16 — CI #40–#42 triage (infrastructure verdict, `actionhub.md`)
- Three consecutive full failures on green code: smoke ~1m ×3 (build-phase pull fault signature), eda exit-1 ×3 with local full rerun 479+14 green in 50m24s. Scare en route (apparent 15-min hang at B7) root-caused to observer load + buffered dots + wrong-container readings; faulthandler proved mid-simulation, and every wait is already 300 s-bounded.
- Fix: bounded ×3 retry on both compose builds; `comp.out` pinned to tmp_path; `actionhub.md` workflow log + incident record + runbook. Push re-triggers CI as the live verdict.

## 2026-09-16 — Degradation dashboard (`compare_prepost` + Explorer table, EDA-proven)
- Backend: `layout/postlayout.py` compare runner + concrete-only engine method + POST /postlayout/compare (blocking ~2.5 min, documented) + `tests/test_api_postlayout.py`.
- Frontend: transport + store loop + Pre/Post table (DC/AC/UGBW rows + UGB drop %, MEASURED) + Playwright green live in 2.2 min.
- Evidence: full base 447+62 green; tsc + vite build green.

## 2026-09-16 — Stage 9 PEX closed loop (DC control + 12.6% UGB loss, EDA-proven)
- Extracted-SI M1 in the B3 CS fixture vs schematic twin: DC agrees <5% (caps don't move DC), UGB degrades 5–30% (measured 12.6% @2fF declared load; unloaded pole past 10GHz both sides).
- Evidence: EDA closed-loop green in 2.5 min; full base 446+61 green.

## 2026-09-16 — Stage 9 PEX quantify (10 coupling caps, scaling proof, EDA-proven)
- `extract all` + zero thresholds force femtofarad caps into the netlist (defaults silently drop them on demo cells). Parser is suffix-explicit/fail-closed; budgets are conservative (full value both terminals, documented).
- Evidence: EDA scaling proof 4 passed in 6 s; full base 444+60 green.

## 2026-09-16 — Stage 8 LVS closure (extract w=200/l=30, Netgen match, EDA-proven)
- Labels renamed to schematic vocabulary (drain/gate/source/vss) so extracted nets compare directly. Diff-Y fix: overlap IS the channel (was extracting W=1.5 for 1.0 drawn) + W≥0.5µm two-row guard.
- Loop: OASIS→GDS→Magic extract→ext2spice→Netgen vs 1G golden with W/L→lambda conversion (setup compares w/l at 1%, deletes the rest — verified in deck, no wrapper games). Verdict: "Circuits match uniquely."
- Evidence: EDA `test_layout_lvs` 2 passed; full base 441+59 green.

## 2026-09-16 — Stage 8 PCell PMOS (DRC-clean first try, same cleared pattern)
- `pmos_rects`: mirrored grid + psdm + nwell ring (0.84 deck minimum enforced); 19 boxes F=1. DRC-clean with zero iteration; both polarities parametrized in `test_pcell_drc_clean`.
- Evidence: EDA layout files 14 passed; full base 440+57 green.

## 2026-09-16 — Stage 8 PCell DRC-clean (`2096215`, deck-proven)
- Iterative loop vs the FEOL-enabled Sky130 deck (4 → 1 → 0 violations): tap gap 0.30 (`difftap.3`), gate endcap 0.18 (`poly.8`), tap contact+li (`licon.16`), strap/bar 0.37/0.57 (`li.5`+`li.3`). All numbers deck-quoted.
- `test_pcell_drc_clean` pins zero violations in CI (EDA). Interim visual pipe (`layout_dump` + `layout.plot` → `artifacts/layout/pcell_nmos.png`): KLayout offscreen won't paint fills (control-proven incl. PDK GDS), so GUI review stays pending.
- Evidence: full base 439+56 green.

## 2026-09-15 — Stage 8 PCell NMOS (`2dabe8f`, EDA-proven)
- `layout/pcells.py` pure geometry (SI boundary documented, DRC-dirty grade) + JSON-pipe emitter + base/EDA tests. F=1 reproduces spike counts; scaling/symmetry/extents pinned. Base file 5+1, EDA 10/10 with spike file; full base 438+55 green.

## 2026-09-15 — Stage 8 backend spike (`b06df86` + `18f68bd`, ADR-037, EDA-proven)
- K: pya single-NMOS on 8 PDK-quoted layers, 16 boxes, 507B OASIS, round-trip True (0.30.12). argv lesson: `-b -r` eats positionals — fixed contract name + cwd. `klayout.db` pip package absent; `-b -r` is the path.
- M: Magic batch `-T sky130A.tech` v1.0.608, paint + save (120B .mag) + DRC "No errors found". (First attempt loaded default tech — `-T` required.)
- N: Netgen 1.5.323 + sky130A_setup.tcl self-matches; gate/drain swap fails; d/s swap passes by correct `permute default` semantics (first misread as tool bug, root-caused).
- Verdict: KLayout primary geometry/viewer, Magic DRC/extract adapter, Netgen LVS adapter. Visual §8 checkpoint still gates first clean pass.
- NOT/NAND compiled fragments + Miller AC deck migrated from substring asserts to byte-identical goldens (`tests/golden/*.cir`, 1G read-only protocol); inverter micron deck to inline `==`. Assembler-plumbing asserts (corner lib/temp lines) deliberately stay substring — they pin the varying part.
- Human hand-verified: CMOS inverter/NAND topology, d/g/s/b order, W/L meters, single-ended AC drive. Full base 432+51 green at seal time.
- Housekeeping in the same window: planning records + Lovable shell vendor drop committed (fresh clones build; generated weight stays gitignored); working tree clean.

## 2026-09-14 — R0-5 B7 bandgap (`6a2f265` + `1b38a3b`, EDA-proven, ZERO deferred benches)
- PDK recon (Law 2): `sky130_fd_pr__pnp_05v5_W3p40L3p40` quoted C/B/E + subckt/X; `.dc temp` + CTAT slope proven live in one ngspice-CLI run (0.851V@-40 → 0.575V@125).
- Key falsification en route: subckt `mult` scales mismatch sigma only — ΔVbe measured exactly 0.0000 with it. Fixture reworked to structural 1:8 (Q1 + 8 parallel units, exact by construction); ΔVbe then physical (42.54mV@-40 → 73.10mV@125, theory 41.75/71.3).
- B7a: `sim/bandgap.py` core + gate test + `metrics/tempco.py` (Vref sum + box ppm/°C) + hand-golden unit tests (one own-arithmetic slip caught: 48.67957, verified via 10000/205.425).
- B7b: `assemble_temp_sweep` (.dc temp; corner follows lib+VDD, never .temp) + `_run_b7` (K=9.0 declared, ideal-R/IDC deck assumption documented) + dispatch + live tests; deferral test retired into zero-deferred assertion.
- MEASURED: tempco tt 57.44 / ff 68.90 / ss 43.47 / fs,sf 57.44 ppm/°C; Vref 1.227–1.236V; band 100 clears worst ff. Readout: fs/sf==tt at same VDD (bipolar tt-only inference); tempco moves with supply.
- Evidence: EDA b7-live green at <100; full base 432+51 green. Scratch probes deleted pre-commit.

## 2026-09-14 — R0-4 B6 Miller PVT (`89d33b1` + `42180b0`, EDA-proven)
- B6a: `corner` plumbing in `assemble_miller_ac_deck` (None default keeps nominal decks byte-identical, proven by untouched deck test) + per-corner deck-text test.
- B6b: `_run_b6` instantiates Trial-17 (now single-sourced as `MILLER_TRIAL17_WINNER`, Stage 6 demo deduplicated) across the 5-envelope; per-corner gain_db/UGB/PM via the Stage 6 extraction path; pass = gain≥60dB + PM STABLE on all 5, UGB reported with 1MHz floor.
- MEASURED: tt 81.30/16.58M/63.64, ff 85.40/15.07M/65.07, ss 66.32/16.10M/63.67, fs 84.52/4.96M/63.83, sf 60.78/29.33M/66.06. TT reproduces ADR-028 to 4 sig figs through the corner-plumbed path; 60dB spec survives every corner; 40MHz UGB target stays shorted (reported, not gated).
- Evidence: EDA b6-live green (5 sims, 220 s); full base 421+50 green. Scratch probe deleted pre-commit. Deferral advanced B6→B7/R0-5; only B7 bandgap remains.

## 2026-09-14 — R0-4 Track B PVT sweep in cockpit (B1 `2e0af41` + B2, EDA-proven)
- B1 backend: concrete-only `EngineV01.run_corners` (5-envelope inverter sweep, one ledger job per corner, fail-soft rows) + `POST /corners/run` + `tests/test_api_corners.py`. First red was client ReadTimeout (5×20.5 s sweep > 60 s budget, MEASURED single-corner wall) — test-only 300 s fixture timeout per R0-4b precedent. EDA file 4+2.
- B2 UI: `api.ts` corners transport; store sweep loop (cornerRuns/cornerWaves/cornerPhase, click-to-view through shared liveWave, dumb-frontend kept); "Run All Corners" rewired from nominal `runSimulation` to checkbox-state sweep; Corner Results rows (backend temp/supply/status); Playwright corners test green live in 1.9 min.
- Verification notes: loopback-only CORS blocked the alt-port dev server (hardening working as designed) — temp 8081 origins added, verified, REVERTED (committed diff has no server.py change); user's :8000/:5173 stack left untouched (stale, predates B1).
- Evidence: tsc + vite build green; full base 419+49 green.

## 2026-09-14 — R0-4 Track A B5 folded-cascode (`07ed471` + `5db39ea`, EDA-proven)
- A1 fixture: hand-built `sim/folded_cascode.py` (9-device OTA, template-default 0.5 µm sizes, independent of the `folded_cascode` template for cross-check) + gate test + deferral advanced B5→B6. Base bench file 13+5.
- A2 runner: `_run_b5` (DC sweep on vip → trip → AC at trip with declared 1 pF `Cload`, dual DC/AC assertions + UGB band) + dispatch + base/EDA tests. Bias recipe probed live (16-combo grid; NMOS-strong parks out at vss, PMOS-strong at vdd; winner tail=1.0/bp=1.0/n1=0.5/n2=1.0/vcm=0.9).
- MEASURED: DC 28.070 == AC 28.070 @trip 0.870V, UGB 39.6kHz @1pF, rails 0.063–1.775V. PM deliberately unasserted (single-ended open-loop PM ill-defined; B5 acceptance text updated to dc/ac+UGB).
- Evidence: EDA `-k b5` 3 passed + 1 skip; full base 414+48 green. Scratch probe deleted pre-commit.

## 2026-09-14 — RFC-002 v0-backend (`26d1176`, base green, PUSHED)
- RFC-002 ACCEPTED by human (all 4 §10 verdicts = proposals); status flipped in-file.
- Claim: tutor explain-or-refuse chat over HTTP + 20-prompt refusal Eval. `ai/tutor.py` keyword classifier (9 stems, pure), concrete-only `EngineV01.chat` (newest-first failed-job scan, unclassifiable skipped, fail-soft refusal, chat never raises), `POST /copilot/chat` (ChatIn/ChatOut, trail echoes action_id or `refused-no-evidence`), `tests/test_tutor_refusal.py` (10 in-domain must-ground verbatim + AIAction row; 10 out-of-domain must-refuse with zero provenance rows; newest-fallback, no-job, unclassifiable-only edges; uncited-refusal covered at explainer level in `test_ai_explain.py`).
- Evidence: ruff clean, mypy strict clean, new file 24 passed, full base **412 passed + 47 skipped**. One ruff I001 fixed en route (tutor import sorts after taxonomy). Frontend (AssistPanel rewire + Playwright), v1, ADR-036/037 remain.

## 2026-09-14 — Session gate re-verification + tracker sync (no commit)
- Full base gate re-run at HEAD `7c4ca71`: ruff clean, mypy strict clean (125 files), pytest **388 passed + 47 skipped in 65.7 s**. Only failure en route was 3 ruff hits (I001/F541) from untracked scratch `scripts/_probe_fcn.py` (folded-cascode bias probe, EDA-path hardcoded) — deleted, gate green.
- Verified two To-Do follow-ups as DONE in code and retired them: CORS loopback-only (`api/server.py:323-324`); `test_digital_gates.py` on `assemble_transient` (`tests/test_digital_gates.py:24,124`).
- Synced `To-Do.md` status overview (was stale at Stage 3), `context.md` Active Status (was stale at R0-3/push-due), and this ledger's NOT-done section (was stale at Stage-6-signoff/push-due).

## 2026-09-09 — Stage 0–6 verification sweep + 6E rework (all green)
- Verified Stages 0–5 against AGENTS.md: SI discipline clean (no parser, display-only formatting), golden `nmos.cir` untouched since 1G, NEEDS_LIB skips are documented env-gating (EDA runs them: 334 passed, 0 skipped), provider urllib confined to `ai/provider.py`, spawn isolation in `sim/jobs.py`, optuna pinned `==5.0.0`, no green-washing, no PDK-from-memory writes beyond quoted bindings.
- Known debt recorded: `DesignEngine` remains an ABC skeleton (no concrete engine; first real caller is Stage 7 GUI) — DECISIONS.md entry; concrete `EngineV01` facade is a Stage 7 prerequisite, not a Stage 6 fix.
- 6D flaws found live: (a) missing `conn.commit()` in `instantiate_template` locked worker INSERTs; (b) ungrounded analytical estimator emitted 63.2dB/44.8MHz/62.1deg; (c) differential-drive vip reference inflated UGB 2x; (d) real-part-only phasors fabricated PM = 0.0000; (e) fabricated `power_w` default; (f) taxonomy-less error strings. All fixed in 6E `ababde1`; TRUE measured numbers above.

## 2026-09-09 — Phase 0 Steps 1–2 + Stage 7A lockdown (base green)
- VERIFY-PM-001: `extract_phase_margin` interpolated principal values with `180-abs` and no unwrap — old 6F PM 152.4 re-measured live at +27.58 MARGINAL (kind story; arithmetic closes exactly). Fix (`d494d7c`, ADR-027): unwrap-first, anchor-invariant signed PM, classification, lag-form contract text, wrap suite permanent in CI. Two old unit expectations flipped transparently (0.0→180.0, 60.0→120.0). EDA phase-margin file 11 passed, live cs_amp unchanged.
- Re-baseline (`9980521`, ADR-028): 16-trial wide re-run closed nothing (best 214.71); 20-trial focused study (seed 200) winner trial 17 at gain 81.30dB / UGB 16.58MHz / PM 63.64deg adopted as empirical winner; demo now asserts honesty properties only. Full EDA 340 passed.
- 7A lockdown: `EngineV01` strangler facade (`8f51c90`, EDA engine file 8 passed incl live RC deck) — ABC 11 frozen, v0.1 intact; Law-4 AST boundary guard (`2d25985`); migration v9 checkpoint_registry + design_state (`06669bb`, pin 8→9 acknowledged). Base 325+30. Push gate lifted by 2026-09-09 CONFIRMED verdict.

## 2026-09-10 — Quick-wins debt batch (base + EDA + tsc + build green)
- CORS loopback-only; Misc signoff/metrics fiction → run-state truth; gates deck via assemble_transient (additive extra_lines; remapped samples EDA-proven). Base 371+42; EDA 8 passed.

## 2026-09-12 — CI smoke red fix (ruff + dockerignore)
- Unused loop var broke `make test` ruff gate (Commit 2 shipped without full local gate — lapse recorded); UI generated dirs excluded from image context. Local full gate 388+47 green; CI re-run requested (59s profile = build stage).

## 2026-09-12 — R0-5 Commit 2 optimizer UI (tsc + build + base + e2e green)
- create_spec + POST /specs; study state/poll/stop; sim Stop kills backend; trial table + best + convergence; own dialog-text scoping bug fixed. Playwright 5/5 in 11.4 min.

## 2026-09-12 — R0-5 Commit 1 study supervisor (base + EDA green)
- Scalarizer + supervisor proc (mock/slow/spec, timeout wrapper, heartbeats) + submit/cancel/trials + 3 routes + reconciliation. RFC amended to as-built. Base 386+47; live 3-trial CS study green in 4.3 min.

## 2026-09-12 — RFC-001 approved + ADR-035 (docs commit)
- Spec updated with 4 binding verdicts (§7 scalarizer, §10 resolved); no code per orders. Commit 1 (§9.1) next.

## 2026-09-12 — R0-4e declared-load bandwidth (base + EDA + e2e green)
- 1 pF on AC decks (Stage 3 precedent, DC untouched); MEASURED INV 56.9 / CS 20.709046 MHz; UGBW row live; e2e result-cell assertion fixed. Base 372+46; EDA 7+2; Playwright 4/4.

## 2026-09-10 — R0-4d-2 diff-pair testbench (base + EDA green)
- Third fingerprint with R0-2b bias recipe; DC/AC cross-check + split anchor; rows persist. Probe DC 8.31 pre-commit. Base 372+46; EDA 7+2. Trinity complete (survived a host crash mid-proof; resumed clean).

## 2026-09-10 — R0-4d common-source testbench (base + EDA green)
- Second fingerprint (pair + vbias) with R0-3a bias recipe; shared helper; MEASURED 9.106/9.106, rails clean; bandwidth refuses (2.45 @10GHz). Base 371+45; EDA 6+1. Real analog now measurable; diff-pair next.

## 2026-09-10 — R0-4c bandwidth (contract unity crossing, base + EDA green)
- extract_bandwidth off the in-memory AC sweep; inverter honestly refuses (6.52 V/V @10GHz measured); UI bandwidth attempt with warn-degradation. Own unconditional-extraction bug caught pre-commit. Base 371+43; EDA 4+1; tsc + build green.

## 2026-09-10 — R0-4b measure route + live gain row (base + EDA + e2e green)
- POST /measure via `measure_with_unit` (contract-registry units); frontend measures post-waveforms, Explorer shows 15.24 V/V (23.66 dB) MEASURED. Base 371+42; EDA 4+1; Playwright 4/4. Two red runs root-caused to Playwright's 60s test timeout vs ~90s measure latency (test.slow(); CORS/slowness theories falsified with evidence).

## 2026-09-10 — R0-4a measure dc/ac gain (base + EDA green)
- `EngineV01.measure` for dc_gain/ac_gain on inverter-shape cells (allowlist + dual-analysis cross-check + V/V Measurement rows); shared `_load_raw`; deferral test transparently flipped. MEASURED inverter 15.240/15.244. Base 367+41; EDA 8+1.

## 2026-09-10 — 3e live schematic canvas (Playwright 4/4 green)
- Picker, auto-layout, connectivity strip, live Check/validate, empty state; rename wired so the tab carries the dialog name. Canvas test creates `schem_live_test` and asserts m1/m2 + counts + label. tsc 0 + vite build + e2e green.

## 2026-09-10 — 3d-fix dead toolbar button (Playwright 3/3 green)
- Root cause: toolbar icon had no onClick (only the File menu opened the dialog). Wired via `onNewCell` prop; removed unbindable Ctrl+N hints. New regression test clicks the real toolbar button and asserts the dialog. Full e2e in live Chromium vs user backend: sim COMPLETE (326 pts, 13 polylines), cell create logged, dialog opens. Evidence screenshots refreshed.

## 2026-09-10 — Push 9 commits + 3d cell creation (tsc + vite green)
- Push `a9f8e07..43599eb`: 8 agent commits + human's own `43599eb` (Playwright e2e with verified screenshot, NOT/NAND fixtures, live truth-table test). Pre-push review: SI clean, schema-legal, EDA truth table 3 passed; non-blocking follow-ups (CORS wildcard+credentials, micron string-replace debt, substring netlist asserts).
- 3d: NewCellDialog creates real cells (project → anchor → instantiate, backend defaults); store gains live `cells`/`refreshCells`; errors surfaced verbatim; no physics duplicated in TS.

## 2026-09-10 — Steps 3b + 3c shell de-faking (tsc + vite build green)
- 3b SimulationExplorer: fake physics deleted, live-run table + NOT RUN metrics + ledger history + inert MC + cancelling Stop + sky130 labels.
- 3c WaveformAnalyzer: everything derives from `liveWave` (extents, cursors, markers, legend, AC-gated calculator); `waveforms.ts` deleted. No fake water remains in either workspace; `Misc.tsx` "6 pass / 1 fail" noted for a later slice.

## 2026-09-10 — Step 3a shell run-loop wiring (tsc + vite build green)
- New `UI design 1/src/ic/api.ts` (13 typed endpoints, transport-only) + `store.tsx` live loop: demo run, 400ms ledger poll (150-try cap), waveforms into `liveWave`, phase-driven progress (no fake % ticker), token cancellation + `stopSimulation`, `backendUp` flag, mount-time health + job refresh. Host Bun toolchain verifies: `tsc --noEmit` clean, `vite build` green. Only touched shell files tracked; rest of drop stays untracked.

## 2026-09-10 — 7B-9 cell rename (base green)
- Concrete-only `EngineV01.rename_cell` + POST /cells/{id}/rename; roundtrip/unknown/empty tests. Unblocks dialog naming coherence for 3e without touching the frozen ABC. Base 364+40.

## 2026-09-10 — 7B-8 demo testbench route (Path B step 2d, base + EDA green)
- Concrete-only `EngineV01.run_demo_testbench` + POST /testbenches/run; canonical inverter_tran deck from Stage 2 fixture, job/cell/reproducibility handles out. Suite caught SimError-subclasses-ValueError except-ordering. Base 359+39; EDA file 2 passed + 1 skip, live inversion proven.

## 2026-09-10 — 7B-7 copilot route (Path B step 2c, base green)
- Concrete-only `EngineV01.explain_job` + POST /copilot/explain; failed-job error classified with job as evidence, MockProvider narration only, AIAction provenance pinned by ledger read-back. Succeeded/unclassifiable fail closed with no rows. Base 357+38.

## 2026-09-10 — 7B-6 waveforms route (Path B step 2b, base green)
- Concrete-only `EngineV01.job_waveforms` + GET /jobs/{id}/waveforms; ledger payload re-parsed through Stage 2/3 extractors (parse_transient/parse_ac), units from Quantity symbols. Base seeds exact tran + AC payloads (0dB/0deg and 0dB/90deg hand-computed); live RC charging shape asserted EDA-only. Base 353+38.

## 2026-09-10 — 7B-5 cell browser + schematic routes (Path B step 2a, base green)
- Concrete-only `EngineV01.list_cells`/`schematic` + GET /cells + GET /cells/{id}/schematic; instances with symbol names + SI parameter floats, terminal hookups resolved to net names, unknowns 422. Test builds cells through POST /instantiate (real template rows); symbol-master cells honestly listed (membership, not count). Base 349+37.

## 2026-09-09 — Stage 7B HTTP service + thin slice (base green, EDA spot green)
- Pins (`03635a8`): fastapi 0.141.1 + uvicorn 0.52.4 runtime, httpx2 2.12.0 dev — plain httpx rejected live (starlette TestClient raises deprecation-as-error under filterwarnings gate); image rebuild evidence green both images.
- Threading found by the suite, fixed at root (`1cc858f`): uvicorn worker threads vs same-thread sqlite conns surfaced as ProgrammingError in teardown; RLock serialization over check_same_thread=False in engine + job ledger (store.connect additive kwarg, default untouched). Documented limit: one in-flight sim per engine binding until R0.
- Routes (`5b8c80d`): lifespan-managed factory, engine-implemented methods only, taxonomy-preserving error map (422/500), SI floats on wire with string rejection asserted, SimError/version re-exported through engine surface, AST guard extended to `api/` + own-package allowance.
- Thin slice (`ca155c4`, ADR-032): HTTP validate/netlist (base) + live transient sim parsed to rail-to-rail inversion assertions (EDA 2 passed in 21s). Base 331+31. Push gate lifted by 2026-09-09 CONFIRMED verdict.

## 2026-09-10 — R0-3a B3 common-source bench (base green, EDA file green)
- `sim/cs_amp.py` fixture + `BiasSearch` (28 lines fixture): missionary M1-off trap hit live and fixed by Vg sweep-load-line search; dc-then-ac at measured trip. MEASURED DC 9.102 == AC 9.087, trip 0.85V. EDA bench file 10 passed + 4 skips. Commit `28be619`.

## 2026-09-10 — R0-3b B4 cascode bench (base green, EDA proof pending)
- `sim/cascode.py` fixture (31 lines): Vbcas search reversed live (1.1 beats 0.9 by +4, physically correct); dual DC+AC assertions required (AC-only lies through Rd). MEASURED DC 12.999 == AC 12.989 at trip 0.85V, clears same-size plain-CS 9.1 (threshold 10), headroom 0.205V. Base 346+37 green. EDA `-k b4` proof 2 passed + 1 legit conditional skip in 75s; `28be619` + `a9f8e07` pushed to origin/main. R0-3 CLOSED per Path-B strategic plan; B5–B7 remain deferred (clean NotImplementedError owners).

## 2026-09-09 — R0-2 mirror + diff-pair benches (base green, EDA file green)
- B1 (`1695af6`): matched-pair fixture with bias-direction lesson recorded in code (push-into-diode, not pull-to-ground); sweep-branch identification fail-closed; saturation ratio + triode ordering acceptance. MEASURED ratio 1.025 @0.9V, Early slope to 1.18, KCL-closed return.
- B2 (`0e74696`): single-ended AC drive on proven diff-pair fixture; differential-action fingerprint MEASURED 8.075/0.536; wide structural bands. Deferral representative advanced B1→B2→B3.
- EDA bench file: 8 passed + 3 conditional skips (fail-closed paths). Base 342+35.

## 2026-09-09 — R0-1 AnalogBench + full EDA proof (370 green)
- Registry B0–B7 + executable B0 (`bench/__init__.py`, `tests/test_bench.py`, commit `ca588c7`); B1–B7 raise with R0 owners. Full EDA suite: **370 passed, 1 skipped** (legit `pytest.skip` inside b0-nolib test on lib images) in 16.5 min — covers 7B API routes, thin slice, PM wrap suite, bench B0-live, and all prior stages. Tallies reconcile: 371 collected both images (base 338+33).

## 2026-09-18 — Stage 8 DRC verdict parser (base green)
- `layout/drc.py`: `parse_klayout_drc_xml` over the real `drc.txt` report database → `DrcVerdict(clean, violation_count, rules)`; deck-quoted rule names (`'li.3'`) stripped, malformed/wrong-root/missing-items fail closed via `SimError` (Schema). Fixtures are observed EDA shapes (clean empty `<items>`; 0.30 um gap → exactly two `li.3` edge-pair items, values verbatim — independently re-confirms the #6 `li.3` analysis with direct evidence). Magic stdout parsing deferred (no dirty fixture observed). Base file 5 passed; full base 452+62, ruff + mypy (149 files) clean.


