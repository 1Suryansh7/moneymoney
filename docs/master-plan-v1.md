# master-plan-v1.md — OpenVirtuoso Master Build Plan (v7.1 as amended)

## 1. Product and goal
Standalone, AI-native analog IC design product ("OpenVirtuoso" working title): spec-to-verified-design on open PDKs, zero Cadence dependency, zero licenses, zero coexistence modes. Audience: students (learn faster) and working engineers (less repetitive work). Moat: autonomy + cited explanation, not a cloned editor. Win condition: everything a student/engineer uses in a real analog flow exists in-app and is faster to learn and use — plus the AI dimension Virtuoso lacks.

## 2. Locked decisions (do not relitigate without the human)
Standalone-only · no Spectre/Cadence/Virtuoso lines anywhere · Sky130A-first · TinyTapeout = post-v1.0 stretch goal · second PDK via GF180-vs-FreePDK45 spike scorecard, never blind · trust core before physical flow · digital/RISC-V = parked Stage 11 · AGENTS.md discipline on every commit · honest product wording (§10.8).

## 3. Foundation state (Stages 0–6F, HEAD `af4a1ac`, gates green)
Base `305 passed / 29 env-skipped`; EDA `334 passed / 0 failed`. Six topology templates, KB + adversarial retriever, proposal state machine halting at AWAITING_HUMAN, seeded-Optuna Miller sizing with committed demo asserting **gain 75.16dB / UGB 62.41MHz / PM 152.4°**. **Caveat now attached to that result:** read-only code analysis predicts VERIFY-PM-001 will classify it MEASUREMENT-BUG (missing phase unwrap; hand calc: true phase ≈ −335° → wrapped +25° → fake PM ≈155°; true PM ≈ −155°, i.e., the "winner" is likely unstable and was selected *because* of the bug). Re-baseline of 6F is a named Phase-0 task, not a surprise.

## 4. v7.1 disposition: approved with locked amendments
Cuts: Spectre line removed; PDK bridge scoped to open file-based PDKs, EXPERIMENTAL default, no redistribution. Order: UI MVP (read-only/low-mutation: project tree, design state, run center, waveforms, evidence panel, schematic renderer) immediately after the thin slice; Python SDK pulled forward; full editor stays late. PM policy: signed `PM = 180° + phase_at_unity_gain` with STABLE/MARGINAL/UNSTABLE classification; unwrap-first + wrap-regression tests mandatory. Additions: named 6F re-baseline + re-close-spec checkpoint; EngineV01 stays v0.1 (additive methods); checkpoint registry derives from AGENTS.md §8 (single vocabulary); reuse mandates (extend Stage 5/6B, no parallel metric code); kill criteria on speculative AI (AI-05, guided optimization must beat seeded-TPE baselines or ship advisory-only).

## 5. Execution order (locked)
PM validation → EngineV01 (strangler pattern: delegate, zero logic moves) → architecture CI enforcement → checkpoint registry + Design State schema (v9 migration) → thin inverter slice → **UI MVP** → R0 trust core (Xyce + disagreement protocol with quarantine/adjudication, device audit, MC validation, hierarchical compiler, benches 0–7, accuracy page v1, perf budgets) → R1 environment (hierarchy UI, Testbench Manager, PDK Manager, noise, convergence UX, PDK spike→ADR) → Stage 8 physical → Stage 9 PEX loop → R3 learning system → Stage 10 hardening → v1.0 gate (AnalogBench green, user study, baseline comparison) → launch → stretch (tapeout, digital).

## 6. Non-goals (fenced)
Foundry signoff claims · sub-130nm · RF EM solvers · enterprise SSO (reserve `user_id` only) · Virtuoso compat beyond SPICE interchange · digital/RTL before v1.0 · surrogate models except proposal-only under §9.1 gate.

## 7. Verification regime
Base + EDA gates green every commit · byte-identity netlists vs read-only goldens · tolerance-policy sim comparisons · BLOCKING checkpoints (first PDK syntax, first clean DRC/LVS with screenshot, first PEX, any yield headline, every AI proposal, re-close-spec) · evidence levels non-cumulative with reset on revision/testbench/env change · AnalogBench B0–B12 + professional metrics in CI.
