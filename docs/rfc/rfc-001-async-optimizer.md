# RFC-001: Async Optimizer Execution (Study Jobs, Trial Telemetry, UI Contract)

- **Status**: Approved (4 binding verdicts below — build authorized per §9 order)
- **Date**: 2026-09-12 (draft), approved same day
- **Scope**: Long-running Optuna studies behind the Job ledger, trial
  streaming into `experiment`, cancellation/timeout, and the frontend
  polling contract. ETAs and trial counts are illustrative, never guarantees.
- **Non-goals**: Surrogate/predictive models, multi-objective search,
  parallel trials, hosted-model guidance, interactive study editing.

## Binding verdicts (review authority)

1. **Trial timeout**: 300 s default (shared Windows/Docker hardware
   spikes false-kill tighter budgets).
2. **Max trials**: default 15, hard ceiling 30 for browser studies
   (empirical TPE sweet spot for 2–4 parameters in ~10 minutes).
3. **Cancel scope**: generic `POST /jobs/{id}/cancel` kills BOTH plain
   sims and studies. A Stop that only halts frontend polling while a
   worker burns CPU is a lie — wire the backend kill everywhere.
4. **Objective scalarizer**: MANDATORY. Raw pass/fail collapses TPE
   into blind search (a 19 dB near-miss must outscore a 2 dB
   disaster). Violating trials score
   `-1000 * (1 + sum of relative constraint violations)` (continuous
   gradient toward feasibility); passing trials score a positive
   figure of merit. No boolean ever reaches `tell()`.

---

## 1. Problem

`EngineV01.simulate()` blocks the calling thread until the worker
verdict lands (`runner.wait`, 300 s cap). That contract is correct for
single sims and fatal for optimization: a 15–30 trial Optuna study at
~45–90 s per evaluation (two sims per `measure()` call) runs 10–60
minutes of heavy CPU. Executing that inline in a FastAPI handler means
browser timeouts, wedged worker threads, and orphaned ngspice
processes. A second, quieter trap: optimizing DC gain alone on a
2-transistor stage produces degenerate, unphysical circuits (all
width, no bandwidth). Gain-bandwidth trade-off must constrain the
objective, which is exactly why R0-4e precedes this RFC.

## 2. Ground truth this design stands on (read, not assumed)

| Fact | Source |
|---|---|
| `job.kind` is free-text; no migration needed for an `optimize` kind | `store/schema.py:171` |
| `job.status` already admits `pending/running/succeeded/failed/cancelled` | `store/schema.py:172-174` |
| `JobRunner.cancel()` terminates → kills → marks `cancelled`; `shutdown()` reaps all | `sim/jobs.py:152-180` |
| `wait()` contains worker crashes (parent marks `failed`, never trusts the corpse) | `sim/jobs.py:128-150` |
| Optimizer is ask/tell over Optuna TPE, deterministic by seed | `optimize/optimizer.py`, `optimize/optuna_optimizer.py` |
| Every trial already has a ledger writer/reader (`record_experiment` / `list_experiments`) | `optimize/ledger.py` |
| Spec rules + evaluator exist for objective scoring | `metrics/evaluator.py`, `store` `specification` / `constraint_rule` |
| Engine serializes one binding behind an RLock; one in-flight sim (documented limit) | `engine/engine_v01.py:42-50` |
| SQLite is rollback-journal, FK-enforced, **no busy timeout set** (driver default 5 s applies) | `store/schema.py:289-300` |

## 3. Async execution model

### 3.1 Shape of a study

```
POST /optimize {template_id, spec_id, space, seed, max_trials, trial_timeout_s, study_timeout_s}
  -> 202 {job_id, study_id}                        # returns in ms; nothing simulated yet
       |
       v
study-worker PROCESS (spawn, daemon)               # NOT a thread: libngspice
  |  1. marks job running                          # is non-reentrant (§10.3)
  |  2. loop until max_trials / deadline / cancelled:
  |       ask() -> params                          # Optuna TPE, in-worker
  |       instantiate template with params         # own EngineV01 on same DB file
  |       measure() each spec metric               # existing testbenches only
  |       score vs spec via evaluate_specification
  |       tell() + record_experiment()             # telemetry lands per trial
  |  3. marks job succeeded (best summary in result) or failed (taxonomy)
```

`study_id` is the Optuna study name and the `experiment.study` key —
one identifier joins the job row, the trial rows, and the UI poll.

### 3.2 Why a process, not a thread or task queue

- Threads are out: libngspice global state forbids it (§10.3, ADR-006).
- An external broker (Redis/Celery) is out: unapproved dependency,
  second source of truth beside the ledger, zero local need.
- The existing primitive — spawn worker + ledger row, exactly as
  `_simulate_worker` does — generalizes: the study worker is a
  *supervisor* process that itself spawns per-trial sim workers
  through its own `JobRunner`. Proven pattern, no new machinery class.

### 3.3 Engine surface (concrete-only, ABC untouched)

```python
EngineV01.submit_study(*, template_id, spec_id, space, seed,
                       max_trials, trial_timeout_s, study_timeout_s) -> dict[str, str]
    # validates template/spec/space fail-fast (ValueError, -> 422),
    # inserts job(kind='optimize', status='pending', payload=study JSON),
    # spawns the study worker, records it in an in-memory
    # {job_id: Popen} map beside JobRunner._live, returns ids.

EngineV01.cancel_study(*, job_id) -> dict[str, str]
    # terminate -> kill the study process (mirrors JobRunner.cancel),
    # mark job 'cancelled'. In-flight trial sims die with it; completed
    # trials stay in the ledger. Unknown ids: KeyError (-> 404).

EngineV01.list_trials(*, study_id) -> list[dict]
    # list_experiments() shaped for the wire (SI floats, no physics).
```

`submit_study` MUST NOT wait, simulate, or touch Optuna itself: the
HTTP handler returns in milliseconds. Any blocking call in this path
is a design violation, pinned by a test asserting return-before-first-trial.

### 3.4 Routes

- `POST /optimize` → 202 `{job_id, study_id}`; ValueError → 422.
- `GET /studies/{study_id}/trials` → telemetry list; unknown study → 404
  (empty list is a lie — 404 says "no such study").
- `POST /jobs/{job_id}/cancel` → `{job_id, status}`; KeyError → 404.
  (Generic job cancel, not study-specific: sim jobs gain it too.)

### 3.5 SQLite concurrency (the load-bearing decision)

Study worker and API server are two processes on one file in
rollback-journal mode with the driver-default 5 s busy wait:

1. **Keep rollback-journal.** No WAL migration in this RFC.
2. **Writers use short transactions + bounded retry**: every ledger
   write (`record_experiment`, job status flips) commits immediately;
   on `OperationalError: database is locked`, retry with backoff to a
   30 s cap, then mark the study `failed` with taxonomy
   (`SPICE convergence` is wrong here — new wording:
   `Schema: ledger contention exceeded 30 s, study aborted`).
3. **Readers never block writers**: all telemetry reads are single
   SELECTs; the API never holds a write transaction open (it never
   does today — keep it that way).
4. **WAL only on measured pain**: if contention aborts a real study,
   that incident — with the ledger timestamps to prove it — justifies
   a WAL evaluation RFC. Not before (compiled-extension-gate spirit).

### 3.6 Boot reconciliation (orphans)

In-memory `{job_id: Popen}` maps die with the server. The worker
heartbeats its job row every trial; on engine boot, optimize jobs
silent longer than 30 minutes are marked `failed` with `Schema:
engine restarted with study running, verdict unknown; resubmit` —
never silently resumed, never left `running` forever. (Timestamps
compare in Python: ledger ISO text and SQLite `datetime()` text
share no lexicographic order — found during build, not review.)
Sim-job orphans stay a known limitation.

## 4. Trial telemetry

Per completed trial, the worker writes exactly one `experiment` row
via the existing `record_experiment` (no schema change):

- `study`, `trial` (0-based), `kind='trial'`, `status` (succeeded/failed)
- `parameters` (SI JSON: the Wn/Wp vector actually simulated)
- `metrics` (SI JSON: every measured metric, gain AND bandwidth —
  single-metric studies are rejected at submit: `ValueError`, degenerate
  objectives are a design error, not a user freedom)
- `verdict` (best-so-far marker or failure taxonomy class)
- `reproducibility_id`: empty in Commit 1 — trial linkage to individual
  sim jobs is deferred; seed + params + metrics replay any trial
  exactly (R0-5b design task, not an oversight to work around)
- `seed`, `job_id`: null in Commit 1 (same linkage note as above)

Failed trials are data and persist as `failed` — the convergence curve
draws them as gaps, never interpolates across them.

`GET /studies/{study_id}/trials` returns these rows oldest-first with
a recomputed `score` per trial (scalarizer re-run server-side: no
stored column, no drift). The frontend takes max over scores for the
best banner — display assembly, not physics.

## 5. Cancellation & timeout (three distinct mechanisms)

| Mechanism | Trigger | Behavior |
|---|---|---|
| Trial timeout | one evaluation exceeds `trial_timeout_s` | `runner.wait` raises; trial recorded `failed` (verdict names timeout); study continues |
| Study deadline | wall clock exceeds `study_timeout_s` | worker stops asking, marks job `failed` with taxonomy + trials-so-far intact |
| User cancel | `POST /jobs/{id}/cancel` ("Stop") | engine terminates study proc (→ kill fallback), marks `cancelled`; in-flight trial sims die; ledger keeps completed trials |

Cancel-while-simulating races resolve to exactly one terminal state:
whichever lands first (verdict write vs cancel write) wins under the
engine lock; the loser is a no-op, never a resurrection. Pinned by test.

## 6. UI contract (dumb frontend holds)

New store slice, transport only:

- `startStudy(spec)` → `POST /optimize` → `{job_id, study_id}`;
  phase vocabulary gains `OPTIMIZING` (progress = trials-done / max).
- Poll (existing 400 ms loop pattern): `GET /jobs/{id}` for status +
  `GET /studies/{study_id}/trials` for telemetry.
- SimulationExplorer renders: trial table (trial, Wn, Wp, gain, UGBW,
  verdict), best-params banner, convergence polyline in the existing
  `PlotPane` (x=trial, y=best-objective — pure display).
- Stop button → `POST /jobs/{id}/cancel` → phase back to `READY`
  with `cancelled` logged; partial trials remain visible (honest).
- dB/MHz conversions stay display-layer, as today.

No Optuna, search-space, or objective math in TypeScript — the
frontend never sees anything but ledger rows.

## 7. Objective & spec binding (what "better" means)

A study requires a `spec_id` whose rules reference **measured**
metrics only (gain + bandwidth today). At submit time the engine
rejects:

- rules on unmeasured metric_ids (`ValueError`: no testbench),
- single-metric studies (degenerate-objective guard above),
- non-positive or empty space bounds (`ValueError`; PDK-minima
  enforcement stays per-trial — the validator fails out-of-limit
  suggestions closed with taxonomy verdicts visible in telemetry).

Per-trial score is a scalarizer over measured metrics (binding
verdict 4 — booleans never reach the optimizer):

- every hard-constraint violation contributes its relative
  violation `(threshold - value) / threshold` (sign-adjusted per
  operator direction);
- violating trials score `-1000 * (1 + sum of relative violations)`;
- passing trials score a positive figure of merit (initial FOM:
  `gain_vv * bandwidth_hz`, documented where implemented — the
  first scalarizer that earns EDA proof may refine it, never by
  fitting to one study).

The objective column is therefore spec-compliance with a smooth
gradient outside feasibility — the "rocket booster on a bicycle"
failure is a submit-time error, not a runtime surprise.

## 8. Residency & provenance

- AI guidance of studies (suggested spaces, narrated convergence)
  routes through `LLMProvider` + `AIAction` exactly like Stage 5:
  mock/local only until human opt-in (§9.4). The optimizer itself is
  deterministic math (Optuna TPE, seeded), not AI, and needs no
  provenance beyond the ledger.
- Every trial's seed + reproducibility id persist": any trial
  replays byte-identically through `simulate()`.

## 9. Build order (commits, each independently green)

1. Study worker + `submit_study`/`cancel_study`/`list_trials` +
   `POST /optimize`, `GET /studies/{id}/trials`,
   `POST /jobs/{id}/cancel` + pytest (mock-objective EDA-free path
   first, live 3-trial CS study on EDA).
2. Boot reconciliation for orphaned optimize jobs (sim orphans: known limitation).
3. Frontend slice: store + explorer trial table + convergence plot +
   Stop wiring + Playwright (short study, cancel mid-run asserted).
4. Docs sync (ADR-035) + push.

## 10. Open questions for review (resolved at approval)

1. ~~Trial timeout default~~ → **300 s** (verdict 1).
2. ~~`max_trials` ceiling~~ → **default 15, hard ceiling 30** (verdict 2).
3. ~~Cancel scope~~ → **both sims and studies** (verdict 3).
4. ~~Scalarizer~~ → **mandatory, §7 formula** (verdict 4).
