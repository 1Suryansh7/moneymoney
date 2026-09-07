# Stage 4 — Optimization Layer (Stage Brief, Layer 2)

Source of truth: `final_build.md` Stage 4 + `final_prompt.md` Stage 4.
Global rules: `AGENTS.md`.

## 1. Scope (Atomic Commits, ~100–250 lines each)

| Commit | Content | Done-When |
|---|---|---|
| 4A | Documentation & continuity sync + SQLite Migration v7 | `docs/stages/stage-4.md` in sync; `experiment` ledger table live & tested |
| 4B | Optimizer interface + search space + ledger writer | Abstract `Optimizer` (ask/tell), SI `SearchSpace`, `record_experiment`; no Optuna yet |
| 4C | `OptunaOptimizer` (+ dependency) | Seeded TPE ask/tell over the space; determinism proven without sims |
| 4D | Live sizing demo on `cs_amp_nmos` | Real spec + real sims + ledger rows; reproducibility proven by re-simulation; winner bounds surfaced |

## 2. Non-Goals (Out of Scope)

- No PVT corners or Monte Carlo sampling (Stage 4.5 owns values; the
  `corner` axis exists from 4A but stays `'nominal'` throughout Stage 4).
- No GUI integration (Stage 7).
- No surrogate models or AI proposals (Stages 5–6/10).
- No multi-objective Pareto front (single scalar objective; AI-05 narrates later).

## 3. Design Rules (binding for 4B–4D)

- Every trial is a `job` row (kind `'trial'`) plus exactly one `experiment`
  row: study, trial index, params (SI JSON), metrics (JSON), verdict,
  reproducibility id, seed, corner (`'nominal'`), timestamps.
- Failed trials are data: status `'failed'` with verdict naming the failure
  class — never dropped, never retried silently.
- Search spaces are SI floats with `low < high`; W/L bounds respect the PDK
  minima (`pdk_limits`) — the validator, not the optimizer, enforces them.
- Single scalar objective for Stage 4 (Optuna `maximize`); hard-constraint
  verdicts come from the Stage 3 evaluator and are recorded, not bypassed.
- Determinism: same seed + same observations → same suggestions (proven in
  4C without sims); same params → same metrics within tolerance (proven in
  4D by re-simulating the winner).

## 4. Advisory Checkpoint (AGENTS.md §8 — non-blocking)

If the winning trial sits at a search-space bound, converges in
suspiciously few trials, or improves by an order of magnitude, emit the
Stage 4 advisory block with winning parameters and bound positions, then
proceed flagged. Never report a result without trial count + seed.
