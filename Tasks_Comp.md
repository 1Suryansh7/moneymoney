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

1. **Stage 6 Human Checkpoint Signoff** — RE-BASELINED winner (focused study, seed 200, trial 17): gain 81.30dB / UGB 16.58MHz / PM 63.64deg vs 60dB/40MHz/60deg spec = gain+PM PASS, UGB SHORT. Old 6F winner re-measured +27.58 MARGINAL (kind story; 180-27.58=152.42 refutes committed PASS). CONFIRMED by human 2026-09-09: accept Trial-17 as honest empirical baseline, UGB shortfall recorded; push authorized.
2. **Push to GitHub** — verdict CONFIRMED 2026-09-09; push authorized for everything since `9980521` (6E/6F, Phase-0, 7A, 7B).
3. **Stage 7 — Schematic UI** — Lovable Axiom shell ADOPTED as baseline (ADR-031); 7B API service built (`03635a8` pins, `1cc858f` threading, `5b8c80d` routes, `ca155c4` thin slice; base 331+31, EDA thin slice green). Next: workspace wiring + Playwright with first UI action.
4. **Stage 8 — Physical Design** — (KLayout/Magic/Netgen backend spike, PCell placement, DRC/LVS flow).

## 2026-09-09 — Stage 0–6 verification sweep + 6E rework (all green)
- Verified Stages 0–5 against AGENTS.md: SI discipline clean (no parser, display-only formatting), golden `nmos.cir` untouched since 1G, NEEDS_LIB skips are documented env-gating (EDA runs them: 334 passed, 0 skipped), provider urllib confined to `ai/provider.py`, spawn isolation in `sim/jobs.py`, optuna pinned `==5.0.0`, no green-washing, no PDK-from-memory writes beyond quoted bindings.
- Known debt recorded: `DesignEngine` remains an ABC skeleton (no concrete engine; first real caller is Stage 7 GUI) — DECISIONS.md entry; concrete `EngineV01` facade is a Stage 7 prerequisite, not a Stage 6 fix.
- 6D flaws found live: (a) missing `conn.commit()` in `instantiate_template` locked worker INSERTs; (b) ungrounded analytical estimator emitted 63.2dB/44.8MHz/62.1deg; (c) differential-drive vip reference inflated UGB 2x; (d) real-part-only phasors fabricated PM = 0.0000; (e) fabricated `power_w` default; (f) taxonomy-less error strings. All fixed in 6E `ababde1`; TRUE measured numbers above.

## 2026-09-09 — Phase 0 Steps 1–2 + Stage 7A lockdown (base green)
- VERIFY-PM-001: `extract_phase_margin` interpolated principal values with `180-abs` and no unwrap — old 6F PM 152.4 re-measured live at +27.58 MARGINAL (kind story; arithmetic closes exactly). Fix (`d494d7c`, ADR-027): unwrap-first, anchor-invariant signed PM, classification, lag-form contract text, wrap suite permanent in CI. Two old unit expectations flipped transparently (0.0→180.0, 60.0→120.0). EDA phase-margin file 11 passed, live cs_amp unchanged.
- Re-baseline (`9980521`, ADR-028): 16-trial wide re-run closed nothing (best 214.71); 20-trial focused study (seed 200) winner trial 17 at gain 81.30dB / UGB 16.58MHz / PM 63.64deg adopted as empirical winner; demo now asserts honesty properties only. Full EDA 340 passed.
- 7A lockdown: `EngineV01` strangler facade (`8f51c90`, EDA engine file 8 passed incl live RC deck) — ABC 11 frozen, v0.1 intact; Law-4 AST boundary guard (`2d25985`); migration v9 checkpoint_registry + design_state (`06669bb`, pin 8→9 acknowledged). Base 325+30. Push gate lifted by 2026-09-09 CONFIRMED verdict.

## 2026-09-09 — Stage 7B HTTP service + thin slice (base green, EDA spot green)
- Pins (`03635a8`): fastapi 0.141.1 + uvicorn 0.52.4 runtime, httpx2 2.12.0 dev — plain httpx rejected live (starlette TestClient raises deprecation-as-error under filterwarnings gate); image rebuild evidence green both images.
- Threading found by the suite, fixed at root (`1cc858f`): uvicorn worker threads vs same-thread sqlite conns surfaced as ProgrammingError in teardown; RLock serialization over check_same_thread=False in engine + job ledger (store.connect additive kwarg, default untouched). Documented limit: one in-flight sim per engine binding until R0.
- Routes (`5b8c80d`): lifespan-managed factory, engine-implemented methods only, taxonomy-preserving error map (422/500), SI floats on wire with string rejection asserted, SimError/version re-exported through engine surface, AST guard extended to `api/` + own-package allowance.
- Thin slice (`ca155c4`, ADR-032): HTTP validate/netlist (base) + live transient sim parsed to rail-to-rail inversion assertions (EDA 2 passed in 21s). Base 331+31. Push gate lifted by 2026-09-09 CONFIRMED verdict.


