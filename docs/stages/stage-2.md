# Stage 2 — Simulation Kernel (Stage Brief, Layer 2)

Source of truth: `final_build.md` Stage 2 + `final_prompt.md` Stage 2 prompt.
Global rules: `AGENTS.md`. Architecture: ADR-006 (worker-process isolation
from Day One), ADR-007 (four-part reproducibility identity), AGENTS.md §10.3.

## 1. Scope (atomic commits, one testable claim each)

| Commit | Content | Done-when |
|---|---|---|
| 2B | Migration v5: `job`, `testbench`, `analysis` tables + FKs | ledger round-trips, statuses constrained |
| 2C | `NgspiceBackend` ctypes wrapper over libngspice.so (SendChar / SendStat / ControlledExit callbacks per `sharedspice.h`) | library loads, backend implements `Simulator`, RC deck runs |
| 2D | Local `Job` runner: one worker **process** per job (spawn; timeout/cancel/crash-safe). Zero in-process threading — libngspice global state forbids it | submit/wait/cancel semantics proven |
| 2E | Canonical reproducibility identity: `design_identity_hash`, `execution_environment_hash`, `reproducibility_id`, `comparison_policy_id` (SHA-256, §14.1) | same inputs → same hashes; env change → different env hash |
| 2F | Waveform parser into SI-typed structures (`Second`, `Volt`, `Ampere`) | typed waveform from raw vectors |
| 2G | Concurrency & isolation stress suite: simultaneous 1-, 2-, 4-job workloads | zero cross-run contamination, no callback mixups, contained cancel/crash, deterministic re-runs |
| 2H | CMOS inverter fixture (PDK-quoted PMOS binding read from on-disk PDK) + first transient via a Job + PNG to `artifacts/` | 🔴 HUMAN CHECKPOINT (see §3) |

No new dependencies — ctypes, multiprocessing, hashlib, sqlite3 are stdlib.
Plotting for the checkpoint PNG is decided at 2H (dependency rules apply).

## 2. Non-goals

No thread-based execution; no pool-reuse optimization (per-job processes
until profiling demands otherwise); no measurement semantics (Stage 3); no
optimizer (Stage 4); no spec evaluation.

## 3. Stop condition (AGENTS.md §8)

The moment the first inverter transient returns from libngspice: plot it,
save PNG to `artifacts/`, verify rail-to-rail swing, correct inversion,
plausible rise/fall for sky130, no convergence artifacts — then STOP and
raise `[ HUMAN CHECKPOINT — Stage 2 / First simulation ]`. This run becomes
the template every other testbench copies. No Stage 3 code before verdict.
