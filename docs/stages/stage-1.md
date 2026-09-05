# Stage 1 — Circuit Kernel (Stage Brief, Layer 2)

Source of truth: `final_build.md` Stage 1 + `final_prompt.md` Stage 1 (+
adversarial second-model prompt). Global rules: `AGENTS.md`.

## 1. Scope (atomic commits, one testable claim each)

| Commit | Content | Done-when |
|---|---|---|
| 1A | Typed SI units + display formatter (no parser, ADR-018) | `Hertz("10MHz")` raises; formatting exact |
| 1B | Migration framework + 9 structural/existence tables | versioned, FK-enforced, idempotent |
| 1C | Connectivity graph over 1B rows (facts only) | degrees/loose/sparse proven |
| 1D | Canonical form + SHA-256 identity | same circuit/different ids → one hash |
| 1E | Netlist compiler + v2 tables (Parameter/Technology/ModelBinding) | byte-identical expectation on generic fixture |
| 1F | Validation gate + v3 tables (Specification 3 kinds, Constraint, ErrorRecord) | rejection suite per pillar |
| 1G | NMOS golden fixture + hand-written reference | 🔴 HUMAN CHECKPOINT (see §3) |

Table ownership (past 1B): 1E Parameter/Technology/ModelBinding (+v4 `kind`
in 1G: `M` mosfet vs `X` subckt, read from the PDK); 1F
Specification/Constraint/ErrorRecord; Stage 2 Job/Testbench/Analysis;
Stages 3/4 Measurement/Experiment.

## 2. Non-goals

No simulator calls (Stage 2), no spec evaluation (Stage 3), no optimizer
(Stage 4), no automated W/L-minima checks (needs PDK minima ingestion —
open follow-up, human eyes cover it at the checkpoint).

## 3. Blocking checkpoint (AGENTS.md §8)

Before ANY Stage 2 work: hand-verify `tests/golden/nmos.cir` against
`sky130_fd_pr__nfet_01v8__tt.pm3.spice` in the pinned image — model name,
d/g/s/b order, `X` prefix (subckt, not `M`), W/L meters + plausibility,
net-name sanity. Verdict vocabulary: `CONFIRMED` / `REJECTED — <error>` /
`INSUFFICIENT — <artifact>`.
