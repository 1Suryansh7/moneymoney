# Stage 4.5 — Robustness (Stage Brief, Layer 2)

Source of truth: `final_build.md` Stage 4.5 + `final_prompt.md` Stage 4.5.
Global rules: `AGENTS.md`.

## 1. Scope (Atomic Commits, ~100–250 lines each)

| Commit | Content | Done-When |
|---|---|---|
| 4.5A | Corner axis + testbench plumbing + 5-corner live matrix | `Corner` (SI) + standard sets; `.temp`/`.lib`/VDD deck plumbing; cs_amp runs across the envelope with per-corner ledger rows |
| 4.5B | Monte Carlo spike, then sampler | Determinism proven or parametric fallback documented; zero fabricated statistics |
| 4.5C | StatisticalProtocol + Wilson CI + robustness report | Versioned protocol, pure-math CI, end-to-end report; blocking checkpoint on any yield headline |

## 2. Non-Goals (Out of Scope)

- No two-stage Miller op-amp fixture (Stage 6 scope; declared deviation —
  4.5 evaluates the validated `cs_amp_nmos`, see §4).
- No 45-corner live matrix (defined + unit-tested only; live runs stay on
  the 5-corner envelope to bound CI time).
- No surrogate models or AI narration (Stages 5–6/10).
- No second PDK (Stage 10).

## 3. Design Rules (binding)

- Temperature stored Kelvin, emitted Celsius (`T - 273.15`) at the deck
  boundary only — same boundary law as ADR-020.
- `corner.vdd` overrides the assembler `vdd_volts`; `corner.process`
  replaces the `.lib` section of `libs[0]` (corner without `libs`
  fails closed — there is no default PDK path).
- Valid processes are exactly the five canonical MOS corners
  (`tt`/`ss`/`ff`/`sf`/`fs`) quoted from `sky130.lib.spice`; extended
  R/C-combo sections are out of scope.
- MC uses ONLY PDK-supported mechanisms; if ngspice seeding proves
  non-repeatable across workers, fall back to seeded Python-side Pelgrom
  perturbation and say so explicitly.
- A yield percentage is never emitted without N, seeds, corners, thresholds,
  and CI attached — and never without the blocking checkpoint.

## 4. Declared Deviation

`final_build.md` §4 names a two-stage Miller op-amp for the robustness
report. That topology is Stage 6 scope; smuggling it here breaks scope
control. Stage 4.5 reports on `cs_amp_nmos`.

## 5. Blocking Checkpoint (AGENTS.md §8)

Before any sentence of the form "X% of samples pass", emit the Stage 4.5
block (N, seeds, corners, supplies, temps, mechanisms, method, threshold,
CI) and wait. Test code asserts counts, never headlines.
