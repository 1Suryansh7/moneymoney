# AGENT2.md — OpenVirtuoso Implementation Constitution (v1.0-frozen)

> Canonical operating rules for every agent touching this repo, from this
> point forward. Supersedes AGENTS.md where they conflict; AGENTS.md remains
> the historical record. Source of truth for intent:
> docs/master-plan-v1.md (v7.1 as amended in planning session 2026-09-09).
> If an agent's instinct conflicts with the plan, **the plan wins**.
> If the plan is genuinely ambiguous, **stop and ask**.

## 0. Product identity (immutable)
Standalone, AI-native analog IC design product. Zero dependency on
proprietary EDA (no Cadence/Virtuoso/Spectre code paths, adapters, file
formats, or license env vars anywhere). Open PDKs only. Students learn
faster; engineers repeat less. Moat = autonomy + cited explanation.

## 1. Layer stack (unchanged)
Layer 1 = this file · Layer 2 = docs/stages/stage-N.md + docs/master-plan-v1.md
phase brief · Layer 3 = single-commit task prompt. Never send Layer 3
without Layers 1–2 loaded.
> Golden rule: **the agent proposes, the simulator decides, the human commits.**

## 2. Four Fundamental Laws (unchanged)
1. NEVER mark a stage/phase "done" on agent judgment — human signs off.
2. NEVER write PDK/model/layer syntax from memory — quote the PDK file and lines.
3. NOTHING reaches any simulator without schema + connectivity + unit +
   model-binding validation. Zero bypass.
4. NO subsystem touches simulators, layout tools, PDK files, artifact
   storage, or SQLite internals except through its engine/backend boundary.
   UI → EngineV01 · AI → EngineV01 · CLI → EngineV01 · SDK → EngineV01.
   CI enforces this (architecture test fails on forbidden imports).

## 3. SI units (unchanged)
SI base units exclusively in storage/schema/params/APIs. No SI-prefix
strings outside the display layer. Parsing a prefix outside display = bug.

## 4. Scope and commits (unchanged + extended)
One Task = One Commit = One Testable Claim. ~400-line cap; target 100–250.
Respect [defer]. No new dependencies without asking. No unsolicited
refactoring. EngineV01: strangler pattern — delegate to existing modules,
zero logic moves in the facade commit. Additive engine methods keep v0.1;
signature/behavior change bumps v0.2 with a migration note same-commit.

## 5. Testing and truth gates (unchanged + extended)
Co-located tests every commit. Netlists byte-identical vs read-only goldens
(edit golden ⇒ BLOCKING checkpoint). Sim output tolerance-based, never byte
equality. No xfail/skip green-washing. NEW: metric extractors must handle
wrapped/adversarial math — every extractor ships a wrap/degeneracy
regression test. Phantom guardrails forbidden: a docstring claiming a check
that code does not perform is a defect.

## 6. Failure taxonomy (unchanged)
Classify every failure in this formal chain before reporting:

$$\text{Syntax} \to \text{Schema} \to \text{Netlist} \to \text{SPICE convergence} \to \text{Operating point} \to \text{Constraint} \to \text{PVT} \to \text{Monte Carlo} \to \text{DRC} \to \text{LVS} \to \text{PEX} \to \text{Post-layout performance}$$

No bare "failed" messages — category + trigger + reproduction always.
`"Simulation failed"` alone is NEVER acceptable.

## 7. Honesty (unchanged + extended)
Ran-it vs read-it vs inferring — label it. No fabricated numbers in code,
comments, commits, or reports. No plausible fiction. NEW: every numeric
claim is tagged MEASURED or PREDICTED; predictions never sign off designs;
surrogate models are proposal-only under §9.1 and need their own gate.

## 8. Signed-measurement policy (NEW)
Extractors report mathematically correct signed values — never clamp,
never wrap silently. Phase margin = 180° + phase_at_unity_gain, with
STABLE/MARGINAL/UNSTABLE classification alongside. Negative PM is data
(instability reported, optimizer learns away). Unwrap-first is mandatory
for all phasor math, with regression tests.

## 9. Checkpoints (registry derives from AGENTS.md §8 — single vocabulary)
Machine-readable registry: trigger, required evidence, verification action,
blocking/advisory, reviewer, decision, timestamp. Blocking set: first PDK
syntax, first waveform, every new metric formula, first MC yield headline,
every AI proposal, first clean DRC/LVS (+KLayout screenshot), first PEX,
re-close-spec after any invalidation. ADVISORY: bound-sitting optimizers,
uncited explainer narrations (refuse instead). BLOCKING cross-cutting:
any rewrite/shift out of Python or any compiled extension (needs profiler
proof of >80% Python-bytecode bottleneck + engine-interface containment).
Verdicts: CONFIRMED / CONFIRMED WITH NOTE (record note) / REJECTED (fix
root cause) / INSUFFICIENT (name artifact).

Emit this exact block, then wait:

```text
[ HUMAN CHECKPOINT — <Stage / Component> ]
Trigger: <what specifically caused this stop>
Check: <the exact, concrete thing to verify — not "review this">
Status: BLOCKING — not proceeding until you confirm.
```

## 10. Re-baseline and re-close rule (NEW)
When a fix invalidates a prior result: re-run the measurement/optimization,
rewrite affected tests/comments/trackers, record an ADR, and raise the
re-close checkpoint before accepting a weaker spec or bigger budget.
Never silently keep the old numbers anywhere.

## 11. Evidence and design state (NEW)
Evidence levels: THEORETICAL < SIMULATED < CROSS-SOLVER < PVT < MC <
PEX < SILICON-CORRELATED. Non-cumulative; any revision/testbench/env
change resets dependent levels. Design states: DRAFT → SIMULATION_READY →
NOMINAL → PVT → MC → LAYOUT_READY → PHYSICAL_VERIFIED →
POST_LAYOUT_VALIDATED → REVIEW_READY → RELEASED, with dependency
invalidation on change (affected states only).

## 12. AI laws (unchanged)
PROPOSE/PREDICT/NARRATE/RETRIEVE/PRIORITIZE only — never physical truth
(DesignEngine validation, simulators, deterministic measurement/constraints,
DRC/LVS/PEX, human approval). Structured-IR-before-prose, fail closed,
explicit uncertainty/provenance. LLMProvider routing, residency modes
(LOCAL_ONLY default), secret filtering, capability aliases — all unchanged.
NEW: speculative AI (experiment planner, guided optimization) ships only
with task-benchmarks beating seeded-TPE baselines, else advisory-only
(kill criterion, not aspiration).

## 13. Solver and PDK policy (NEW)
ngspice primary, Xyce independent cross-check; capability-matched comparison
only; disagreements quarantined as SIMULATOR_DISAGREEMENT for human
adjudication — never silent winner-picking; delta report published.
PDK bridge: open file-based PDKs only, manifested, EXPERIMENTAL until
capability-certified, never redistributed. Second PDK only via scored spike
→ ADR. No universal mismatch criterion — per-device validation.

## 14. Physical policy (unchanged + extended)
Best adapter per step behind LayoutBackend (KLayout primary candidate).
Deterministic PCell generators only — AI proposes constraints, never
geometry directly. Coverage certificates per PDK declare automated/manual/
unsupported; never claim "fully verified" with undisclosed manual rules.
Visual KLayout review before PCell reuse.

## 14b. Foundational contracts carried forward (condensed from AGENTS.md §10)
- **Reproducibility**: persist design_identity_hash, execution_environment_hash,
  reproducibility_id, comparison_policy_id (SHA-256, canonical encoding).
  Tolerance is comparison policy, never circuit identity.
- **Concurrency**: worker-process isolation for all native simulation, forever.
  libngspice is non-reentrant; no threading in any language changes that.
- **MetricContracts**: the 7-metric matrix (gain, bandwidth, phase margin,
  slew rate, power, offset, settling) with declared analysis/testbench/sign/
  units/crossing rules; same metric, one meaning everywhere.
- **StatisticalProtocol**: every yield headline carries N, seeds, corners,
  supplies, temps, mechanisms, method, thresholds, counts, CI, experiment IDs.
- **CACE boundary**: CACE executes/imports/exports characterization only. The
  engine owns specifications, metric definitions, pass/fail, provenance.
- **Language stability**: Python 3.11+ is the permanent orchestration layer.
  NEVER propose/plan/execute a rewrite in C++/Rust/another language.
  Compiled extensions only behind the engine interface with profiler proof
  (BLOCKING checkpoint, §9).
- **Wording**: "spec-to-physical-verification" only. Never "production
  signoff" or parity/superiority claims without tapeout-grade evidence.

## 14c. Tooling, hardware, roster (condensed from AGENTS.md §§11–13)
- Always on: filesystem+git MCP, ruff + mypy-strict, pytest, Docker, pre-commit.
  Stage adds: Playwright (7, UI≡API equivalence), KLayout API + Magic/Netgen
  (8), Firejail/gVisor limits (10). No auto-commit/merge bots, no YOLO shells.
- Host: WSL2 Docker only (never Hyper-V); compact the vdisk periodically;
  `docker system prune` after rebuilds; primitive-only PDK scope until a
  scored-spike ADR changes it; 7–8B 4-bit local models max on 8GB VRAM.
- Cost discipline: novel subsystem → strong model full context; mechanical
  change → fast model; PDK/units → docs in context; golden/adversarial
  authoring + architecture reviews → different model family (ChatGPT Plus);
  copilot traffic → governed LLMProvider. Never explain a traceback you
  already understand; never rewrite passing code "more cleanly."

## 15. Product and wording (unchanged + extended)
Learn Mode + Engineer Mode share one engine; AI optional and reversible.
Claim "spec-to-verified-design" only. Never "signoff"/parity/superiority
without tapeout-grade evidence. Productivity measured empirically (time,
sim count, interventions) — never "do you like it".

## 16. Reuse mandates (NEW)
Extend, don't rebuild: AI §§ build on Stage 5, knowledge on 6B,
measure() dispatches to MetricContracts, impact analysis builds on the 1C
graph + revision system. Parallel metric/extractor code is a defect.

## 17. Operational prompts (kept in full — agents execute these literally)

### 17.1 Session start (every session, before anything else)
1. Read AGENT2.md. Confirm the four laws back in one line each:
   human signs off done · never invent PDK syntax · zero validation bypass ·
   everything through EngineV01.
2. Read docs/stages/stage-<N>.md — the current stage brief.
3. Read the last 5 commit messages; state where work stopped.
4. Run `make test`; report state. Fix nothing yet. Then wait for the task.

### 17.2 Session handoff (before closing any session)
Write docs/handoff.md: completed work per commit · human-verified vs
agent-asserted · every open checkpoint + status · next session's first
action · anything resolved by guessing (be specific — this bullet matters most).

### 17.3 Bug triage (failing test: do NOT fix yet)
1. Classify against the §6 taxonomy. 2. State minimal reproduction.
3. Top hypothesis + the ONE evidence that would falsify it. 4. Go get it.
Then propose a fix. Touching a golden, tolerance, or test assertion ⇒
checkpoint instead of proceeding.

### 17.4 PDK anti-hallucination gate (before writing any PDK syntax)
1. Name the exact PDK file. 2. Read it; quote relevant lines. 3. Only then
write code, citing quoted lines in the docstring. File not found ⇒ stop,
never proceed from memory.

### 17.5 Adversarial review (via a different model family; be hostile)
Check the diff for: non-SI storage · engine bypasses · validation-gate
bypass · byte equality on sim output · done-without-checkpoint · out-of-stage
scope or [defer] violations · numbers no simulation produced · taxonomy-less
"failed" wording. Output violations with file:line, or plainly state none.

### 17.6 Are-you-sure probe (for any claim challenged)
Answer one letter + detail: (a) ran it, observed · (b) read it in a named
repo file · (c) inferring without running · (d) recalling training data.

## 18. Anti-patterns (7 kept + 1 new)
Plausible Number · Golden Drift · Silent Unit Coercion · Helpful Side Door ·
Checkpoint Fatigue · Review-Loop Addiction · Multi-Stage Prompts — all kept.
8. ☠️ **The Wrapped Phase**: trusting principal-value math on multi-pole
data. Mitigation: unwrap-first + signed reporting + wrap regression tests.
