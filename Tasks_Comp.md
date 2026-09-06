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

6 → 12 → 99 → 108 → 113 → 118 → 129 → 140 → 144 passed, zero warnings
throughout (`filterwarnings = error`), mypy strict clean on 13 → 29 files.

## Final pinned toolchain (all observed)

`python:3.11-slim-bookworm` (3.11.16) + Ubuntu 22.04 root; Python 3.11.15
(eda); ngspice-47 (CLI + libngspice.so.0.0.16); KLayout 0.30.12; Magic
8.3.683; Netgen 1.5.323; sky130A primitive-only @`1689ac3f`
(fd_pr `403964dc`); pytest 9.1.1, mypy 2.3.1, ruff 0.16.6.

## Stage 2 — Simulation Kernel (Commits 2B–2H implemented in 6ddf868)

| Commit | Scope | Status & Evidence |
|---|---|---|
| 2A docs | Stage 2 brief + continuity sync | `docs/stages/stage-2.md` created; `context.md` and `To-Do.md` synchronized |
| 2B schema | Migration v5 (`job`, `testbench`, `analysis`) | Implemented in `schema.py`; tests in `test_schema.py` |
| 2C backend | `NgspiceBackend` ctypes wrapper | Implemented in `sim/ngspice.py`, `sim/backend.py`; tests in `test_sim.py` |
| 2D runner | Worker-process isolation `JobRunner` | Implemented in `sim/jobs.py` (spawn process per job); tests in `test_jobs.py` |
| 2E reproduce | 4-part SHA-256 identity system | Implemented in `sim/reproduce.py`; tests in `test_reproduce.py` |
| 2F waveform | Typed SI waveform parser | Implemented in `sim/waveform.py`; tests in `test_waveform.py` |
| 2G stress | 1-, 2-, 4-job concurrency suite | Implemented in `tests/test_stress.py`; isolates crashes and state leaks |
| 2H inverter | CMOS Inverter prototype & testbench | COMMITTED 2026-09-06: `sim/inverter.py`, `sim/testbench.py`, `examples/plot_inverter.py`; tests in `test_inverter.py`. Two root-caused fixes en route (taxonomy Netlist): (1) SI-meter W/L fail PDK binned-model lookup — geometry emits ×1e6 microns + `.option scale=1e-6` + `.param mc_mm_switch=0` (ADR-020, 2x2 scale experiment); (2) floating `vss` return coupled output above rail — explicit `VSS vss 0 DC 0`. Evidence: EDA 182 passed; `artifacts/inverter_transient.png` 326 pts vin 0–1.8 / vout −0.019–1.808; Stage 2 checkpoint CONFIRMED by human 2026-09-06 |

## NOT done (open, owned)

1. **Stage 3 — Measurement & Specification Engine** (next; one MetricContract at a time).
2. **Push + GitHub Actions run** — no remote configured; CI has only proven itself locally via `act`. Needs: `git remote add` + push + green run observation.
4. `actions/checkout@v4` floating major (accepted for now; Dependabot later).
5. Automated W/L-minima checks (needs PDK minima ingestion; human eyes cover it at checkpoints).
6. Everything Stage 3+ (measurement & specification engine first).

