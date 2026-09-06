# Stage 3 — Measurement & Specification Engine (Stage Brief, Layer 2)

Source of truth: `final_build.md` Stage 3 (§14.1–§14.2) + `final_prompt.md` Stage 3.
Global rules: `AGENTS.md`.

## 1. Scope (Atomic Increments, One Metric at a Time)

Stage 3 bridges raw simulation vectors (Stage 2) into typed electrical engineering quantities, contracts, and specification evaluations.

### Architectural Sequence:
1. **Contract Matrix & Schema (Commit 3A)**:
   - Define canonical `MetricContract` dataclass.
   - Define the 7-metric contract matrix (semantics, required analysis, testbench capability, formula, sign, units, crossing rules, invalid data behavior, comparison policy, golden fixture ID).
   - SQLite Migration v6: `measurement` table (`id`, `job_id`, `metric_id`, `value`, `units`, `created_at`).
2. **AC & Complex Simulation Support (Commit 3B)**:
   - Extend `NgspiceBackend` and `waveform.py` to handle frequency-domain AC analysis (complex vectors: magnitude, phase, real, imag) without perturbing the transient path.
3. **Metric 1: DC / AC Gain (Commit 3C) $\to$ 🔴 BLOCKING CHECKPOINT**:
   - Contract, formula, Common-Source / Inverter amplifier benchmark fixture. Hand-calculation verification.
4. **Metric 2: Bandwidth (Commit 3D) $\to$ 🔴 BLOCKING CHECKPOINT**:
   - Contract, AC frequency crossing rule (-3dB from DC reference). Hand-calculation verification.
5. **Metric 3: Phase Margin (Commit 3E) $\to$ 🔴 BLOCKING CHECKPOINT**:
   - Contract, loop-gain / return-ratio analysis on defined closed-loop benchmark. Hand-calculation verification.
6. **Metric 4: Slew Rate (Commit 3F) $\to$ 🔴 BLOCKING CHECKPOINT**:
   - Contract, large-signal step transient (10% to 90% or 20% to 80% declared slope). Hand-calculation verification.
7. **Metric 5: Power (Commit 3G) $\to$ 🔴 BLOCKING CHECKPOINT**:
   - Contract, supply current sign convention + integration window. Hand-calculation verification.
8. **Metric 6: Offset (Commit 3H) $\to$ 🔴 BLOCKING CHECKPOINT**:
   - Contract, differential DC input balance methodology. Hand-calculation verification.
9. **Metric 7: Settling Time (Commit 3I) $\to$ 🔴 BLOCKING CHECKPOINT**:
   - Contract, closed-loop step response, declared error band (e.g. 1%), staying condition. Hand-calculation verification.
10. **Specification Evaluator (Commit 3J)**:
    - Hard constraints: pass/fail evaluation against `constraint_rule`.
    - Soft objectives: better-is-better normalized score.
    - Weighted objectives: combined Figure-of-Merit (FOM).

## 2. Hard Non-Negotiable Rules

- **Strict SI Base Units**: All extracted metrics are raw SI floats or `Quantity` objects (e.g., $V/V$ or numeric ratio for Gain, $Hz$ for Bandwidth, degrees or radians for Phase Margin, $V/s$ for Slew Rate, $W$ for Power, $V$ for Offset, $s$ for Settling Time).
- **No Generic Benchmark Reuse**: A current mirror is NOT an accepted benchmark for phase margin or settling time. Each metric runs on an appropriate canonical benchmark.
- **Hand-Calculation Truth Gate**: Every metric function MUST be hand-calculated against golden analytical circuit equations before its checkpoint is signed off.
- **No Log Swallowing**: Simulator errors during metric characterization must carry full ngspice stderr/stdout logs.

## 3. Human Checkpoint Protocol (Once Per Metric)

For each metric $M$, execution halts immediately after implementation:

```text
[ HUMAN CHECKPOINT — Stage 3 / MetricContract + measurement: <metric> ]
Trigger: First implementation of <metric>.
Check: Here is the MetricContract, testbench, raw data, exact algorithm, computed value, sign, and units: <values>. Hand-calculate or independently verify the declared metric and confirm the implementation matches the CONTRACT.
Status: BLOCKING — not proceeding until you confirm.
```
