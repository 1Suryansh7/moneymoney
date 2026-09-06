# Stage 2 — Simulation Kernel (Stage Brief, Layer 2)

Source of truth: `final_build.md` Stage 2 + `final_prompt.md` Stage 2.
Global rules: `AGENTS.md`.

## 1. Scope (Atomic Commits, ~100–250 lines each)

| Commit | Content | Done-When |
|---|---|---|
| 2A | Documentation & continuity sync | `context.md`, `To-Do.md`, `stage-2.md` in sync |
| 2B | Packaging extras + SQLite Migration v5 | `matplotlib>=3.8.0` in dev; `job`, `testbench`, `analysis` tables live & tested |
| 2C | `NgspiceBackend` via `libngspice` C API | Loads `libngspice.so.0.0.16` via ctypes, implements Simulator interface |
| 2D | Local `Job` runner with worker-process isolation | Dispatches simulation jobs to child OS processes with zero cross-run state |
| 2E | Canonical reproducibility identity | 4 SHA-256 hashes implemented: design, execution env, reproducibility ID, policy |
| 2F | Typed SI waveform parser | Raw vectors parsed into typed `WaveformTrace` with `Quantity` base units |
| 2G | Concurrency & isolation validation suite | Repeated 1-, 2-, 4-worker stress tests proving zero state leakage or corruption |
| 2H | CMOS Inverter fixture, transient sim, PNG | First transient waveform returned & plotted $\to$ 🔴 BLOCKING HUMAN CHECKPOINT |

## 2. Non-Goals (Out of Scope)

- No spec evaluation or metric calculation formulas (Stage 3).
- No optimizer loops or parameter sweeps (Stage 4).
- No GUI integration (Stage 7).
- No physical layout or DRC/LVS decks (Stage 8).
- No in-process multi-threading with `libngspice` (prohibited by §10.3 and ADR-010).

## 3. Mandatory Stop Condition & Blocking Checkpoint

The moment the first transient waveform is generated for the CMOS inverter in Commit 2H:
1. Plot the waveform and save to `artifacts/inverter_transient.png`.
2. HALT execution immediately and emit:

```text
[ HUMAN CHECKPOINT — Stage 2 / First simulation ]
Trigger: First transient waveform returned from libngspice for the inverter.
Check: Waveform shape, rail-to-rail swing (0 to 1.8V), correct logic inversion, plausible rise/fall times for Sky130, no convergence artifacts.
Status: BLOCKING — not proceeding until you confirm.
```
