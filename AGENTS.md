# AGENTS.md — Open-Source AI-Native Analog IC Design Platform

> **Canonical System Specification & Operating Constitution**  
> Source of Truth: `docs/master-build-plan-v3.1.md` / `final_build.md` (v3.2 Implementation-Readiness Patched).  
> If an agent's instinct conflicts with the plan, **the plan wins**. If the plan is genuinely ambiguous, **stop and ask** — do not resolve it yourself.

---

## 1. The Core Architecture & Three-Layer Operating Stack

Every task and agent prompt operates on a strict three-layer stack. Never send Layer 3 without Layers 1 and 2 loaded:

| Layer | What it is | Where it lives | Changes how often |
|---|---|---|---|
| **Layer 1: Global Rules** | Non-negotiable behavior for any agent touching this repo | `AGENTS.md` at repo root (auto-loaded) | Almost never |
| **Layer 2: Stage Brief** | Scope, done-when criteria, checkpoints for the active stage | `docs/stages/stage-N.md` (pasted at session start) | Once per stage |
| **Layer 3: Task Prompt** | The single commit-sized ask | Chat / CLI prompt | Every task |

### The Golden Rule of Execution
> 🎯 **One rule above all the rest:**  
> **The agent proposes, the simulator decides, and the human commits.**  
> Every prompt and rule in this platform enforces that strict ordering.

---

## 2. The Four Fundamental Laws

1. **NEVER mark a stage "done" on your own judgment.**  
   "Done-when" criteria defined in §4 are verified and signed off by the **human**, never asserted as complete by the agent.
2. **NEVER write Sky130 model-binding or device syntax from memory.**  
   Read the actual PDK reference file in the repo or ask the human for it. PDK conventions and layer syntax are a known high hallucination risk.
3. **NEVER let anything reach ngspice without passing schema + connectivity + unit + model-binding validation first.**  
   The pre-simulation validation gate (§2) has zero bypass.
4. **NEVER give any subsystem a private path to ngspice, KLayout, or the SQLite schema.**  
   Everything routes strictly through the public `DesignEngine v0.1` API (§3). No side doors, no ad-hoc direct database writes, no raw simulator subprocess invocations.

---

## 3. Strict Physical Units System

- **SI Base Units Exclusively**: All internal values across the entire codebase, storage, schema, function arguments, data structures, and database MUST be SI base units:
  - Capacitance: **Farads (F)**
  - Resistance: **Ohms (Ω)**
  - Frequency: **Hertz (Hz)**
  - Voltage: **Volts (V)**
  - Current: **Amperes (A)**
  - Time: **Seconds (s)**
  - Length / Width: **Meters (m)**
  - Temperature: **Kelvin (K)** (or Celsius only where explicitly bound by PDK temperature deck standard)
- **No String Coercion**: No `"10MHz"`, `"1pF"`, `"10k"` strings in storage, schema, parameters, or functions.
- **Display Layer Only**: Human-friendly formatting (e.g. `10 MHz`, `2.5 pF`) is strictly confined to the display/UI presentation layer.
- If you find yourself parsing an SI prefix outside the UI presentation layer, **you have made a fundamental architectural mistake**.

---

## 4. Scope Control & Commit Granularity

- **One Task = One Commit = One Testable Claim.**
- **Scope Creep Rule**: The single biggest failure mode in AI-driven builds is scope creep per prompt. If a prompt or task would produce more than **~400 lines of new code**, it MUST be split. Target 100–250 lines for foundational steps.
- **Stage 1 Commit Decomposition**: Stage 1 must never be attempted as a single monolithic block. It is strictly split into 7 atomic commits: 1A (Units), 1B (Schema), 1C (Connectivity), 1D (Canonicalization), 1E (Compiler), 1F (Validator), 1G (Golden NMOS fixture).
- **Respect `[defer]`**: Anything tagged `[defer]` in the master plan is strictly out of scope. Do not build it "while you're in there." Do not add premature abstractions for a future stage.
- **Dependency Discipline**: Do not add dependencies without asking. The pinned dependency set is deliberate and immutable.
- **No Unsolicited Refactoring**: Do not refactor code you were not specifically requested to touch. Prefer the smallest diff that satisfies the test.

---

## 5. Testing Discipline & Truth Gates

- **Co-located Tests**: Every behavior change ships with an automated test in the exact same commit.
- **Netlist Comparisons**: Netlist comparisons are **byte-identical** against hand-verified golden references with deterministic ordering.
- **Simulation Comparisons**: Simulation output comparisons are **tolerance-based** (netlist hash + sim-config hash + numerical tolerance policy). **Never assert byte equality on floating-point simulator output.**
- **Golden References are Read-Only**: Never edit a golden reference to make a test pass. If a golden reference appears incorrect, raise a blocking `HUMAN CHECKPOINT`.
- **No Green-Washing**: Never mark a test `xfail` or `skip` to force a green test suite. Report the failure faithfully.

---

## 6. Error Handling & Failure Taxonomy

Every failure must be classified against the formal 12-category failure taxonomy before it is reported:

$$\text{Syntax} \to \text{Schema} \to \text{Netlist} \to \text{SPICE convergence} \to \text{Operating point} \to \text{Constraint} \to \text{PVT} \to \text{Monte Carlo} \to \text{DRC} \to \text{LVS} \to \text{PEX} \to \text{Post-layout performance}$$

- **Strict Error Wording**: `"Simulation failed"` is NEVER an acceptable error message. State the exact taxonomy category, the exact root trigger, and the reproduction details.

---

## 7. Absolute Honesty & Anti-Hallucination Rules

- **Empirical Honesty**: If you did not run it, state plainly that you did not run it.
- **Inference Tagging**: If you are inferring rather than reading from a file, label it explicitly as an *inference*.
- **No Fabricated Numbers**: If a number came from a model's guess or training data rather than from a simulator run or measurement calculation, that number **never** goes into a report, docstring, commit message, or comment.
- **No Plausible Fiction**: Never write a plausible explanation for behavior you did not directly observe. Say *"I do not have the data for this"* instead.

---

## 8. Mandatory HUMAN CHECKPOINT Protocol (§12)

### Operating Rule
**Default to flagging over guessing.**  
Any time the agent is about to trust output in a checkpoint category for the **FIRST time** (first golden reference, first simulation waveform, first measurement implementation, first clean DRC/LVS pass, any unvalidated PDK syntax), it **MUST STOP** and emit this exact alert block, then wait:

```text
[ HUMAN CHECKPOINT — <Stage / Component> ]
Trigger: <what specifically caused this stop>
Check: <the exact, concrete thing to verify — not "review this">
Status: BLOCKING — not proceeding until you confirm.
```

### Checkpoint Table

| Stage / Component | Trigger | What Must Be Verified | Type |
|---|---|---|---|
| **Stage 1 — Netlist compiler** | Golden reference netlist created and first compiler output compared against it | Hand-verify the golden reference is electrically correct (node order, terminal assignment d/g/s/b, W/L in meters, model name matches Sky130 model card) before trusting as ground truth. | **BLOCKING** |
| **Stage 2 — First simulation** | First transient waveform returned from libngspice for the inverter | Waveform shape, rail-to-rail swing, correct logic inversion, plausible rise/fall times for Sky130, no convergence artifacts. | **BLOCKING** |
| **Stage 3 — Metric contracts & formulas** | First implementation of each `MetricContract` and its metric function | Definition, required analysis/testbench, sign convention, units, raw data, and formula match golden hand-calculation. Implemented one at a time. | **BLOCKING** |
| **Stage 4 — Optimizer results** | Trial sits at a search-space boundary or converges in suspiciously few trials | Spec/constraint was not mis-scoped allowing degenerate "optima". Winning parameters and bound positions surfaced. | **ADVISORY** |
| **Stage 4.5 — Robustness claims** | Any headline statement like *"X% of Monte Carlo samples pass"* | Underlying sample count $N$, seeds, corners, variation mechanisms, and confidence intervals. No claim without declared protocol. | **BLOCKING** |
| **Stage 5 — AI explanations** | Explainer narrates a failure or optimizer result | Explanation cites actual `ErrorRecord` / `Measurement` IDs; if uncited, explainer refuses with `"Insufficient data to explain this failure"`. | **ADVISORY** |
| **Stage 6 — AI design proposals** | Any AI-proposed topology instantiation or sizing | Proposed vs current design diff, validation status, simulation status, constraint status. Accept / reject / compare decision. | **BLOCKING (Every time)** |
| **Stage 8 — DRC/LVS/PCells** | First clean DRC + LVS pass on a benchmark circuit | Visual review in KLayout viewer before PCell generator is reused on any other cell. Screenshot saved to `artifacts/layout/<cell>.png`. | **BLOCKING** |
| **Cross-cutting — PDK/model syntax** | Agent about to write Sky130 model binding or device syntax not previously verified | Confirm syntax against local PDK docs rather than model memory. Quote file and lines. | **BLOCKING** |

### Human Verdict Reply Standards
- **Verified**: `CONFIRMED — <what checked and how>. Proceed.`
- **Verified with Caveat**: `CONFIRMED WITH NOTE — <note>. Record note in docstring. Proceed.`
- **Wrong**: `REJECTED — <specific error>. Do not work around it. Fix root cause and re-raise checkpoint.`
- **Insufficient Info**: `INSUFFICIENT — give me <exact artifact>. Still blocking.`
- **Pattern Now Trusted**: `CONFIRMED — this pattern is now validated. Do not re-flag identical subsequent instances. New patterns and anomalies still flag.`

---

## 9. AI Architecture, Provenance & Safety Laws

### 9.1 Global AI-Feature Implementation Law (§10.0 & §13.5)
- AI may **PROPOSE, PREDICT, NARRATE, RETRIEVE, or PRIORITIZE**. It may **NEVER** become a source of physical truth.
- Authoritative truth remains exclusively:
  1. `DesignEngine` validation for schema / connectivity / units / model bindings.
  2. `ngspice` for electrical simulation truth.
  3. Deterministic `Measurement` + `Constraint` evaluation.
  4. `DRC` / `LVS` / `PEX` tools for physical verification truth.
  5. Human approval for design promotion or commits.
- **Structured Before Prose**: Any AI output that can modify design state is a typed, schema-validated JSON object (`CandidateCircuitIR`, `SpecDraft`, `LayoutConstraint`, `ECOProposal`) before prose. Free text is never regexed or parsed to extract design intent.
- **Fail Closed**: Malformed structured output fails closed (rejected or re-requested); it is never invisibly "auto-repaired" and executed.
- **Explicit Uncertainty & Provenance**: Every numeric claim must identify whether it is **MEASURED** or **PREDICTED**. Out-of-domain predictions fall back to the real simulator. No surrogate prediction can ever sign off a design.

### 9.2 The `LLMProvider` Abstraction (§1.5)
Starting Stage 5, all programmatic LLM interactions route through the `LLMProvider` interface. Never write bare inline SDK calls.
```text
LLMProvider (abstract)
 ├── GeminiProvider       # OpenCode / AI Studio key (GEMINI_STRONG_MODEL, GEMINI_FAST_MODEL)
 ├── LocalProvider        # 7–8B 4-bit local model (deferred to Stage 5+)
 └── MockProvider         # Deterministic canned responses for CI and tests
```
- Metadata recorded per call: `model`, `provider`, `prompt_version`, `temperature`, `seed`, `token_usage`, `timestamp`, `request_id`.

### 9.3 `AIAction` Provenance Ledger (§2 & §13)
Every AI-generated explanation, topology proposal, sizing suggestion, or ECO logs an `AIAction` record before anything downstream consumes it:
`id`, `action_type`, `model_provider`, `model_name`, `model_version`, `prompt_version`, `input_context_hash`, `output_hash`, `source_artifacts` (`ErrorRecord`/`Measurement`/`Experiment` IDs), `resulting_design_revision`, `human_decision` (`accept`/`reject`/`edited`/`n/a`), `token_cost`, `latency`, `timestamp`.

### 9.4 AI Data Residency & Secret Protection [v1.2]
- Every Project/workspace operates in one of three explicit AI execution modes:
  1. `DISABLED`: No model calls whatsoever.
  2. `LOCAL_ONLY` (**Default**): Only local models permitted; zero design-bearing data leaves the host.
  3. `HOSTED_ALLOWED`: Hosted API calls permitted only after explicit human opt-in.
- **Pre-Call Disclosure**: Before the first hosted call, surface the provider, model, and classes of design artifacts to be sent; record the human opt-in decision.
- **Immediate Reversion**: Switching back to `LOCAL_ONLY` or `DISABLED` must immediately block all outbound calls without requiring a restart.
- **Secret Filtering**: API keys, PDK credentials, license tokens, environment variables, unrelated workspace files, and secret strings are stripped before provider dispatch and NEVER written to `AIAction` provenance.

### 9.5 Model Capability Aliases [v1.2]
Operational prompts and code never hard-code model generations (e.g. "Gemini 3 Pro", "Gemini Flash"). Model IDs are kept in configuration and routed by capability aliases:
```text
GEMINI_STRONG_MODEL = <current high-reasoning Gemini model ID>
GEMINI_FAST_MODEL   = <current low-latency/cost Gemini model ID>
```
A startup health check must verify that each alias resolves before session tasks begin.

---

## 10. Foundational Architecture Contracts

### 10.1 `DesignEngine v0.1` API Contract (§3)
The Design Engine API is the single canonical entry point. CLI, Python API, GUI (Stage 7), and AI Copilot (Stages 5–6) are callers of this surface. None get private side doors into SQLite, ngspice, or KLayout.
Core signatures:
```python
create_project()
create_cell()
instantiate()
validate()
netlist()
simulate()
check_constraints()
optimize()
run_drc()
extract()
compare()
```
- **API Versioning**: Additive changes are non-breaking. Signature/behavior changes bump the engine version (`v0.1` $\to$ `v0.2`) and require an immediate migration note and commit.

### 10.2 Canonical Reproducibility Identity (§14.1)
Persist four separate reproducibility concepts:
```text
design_identity_hash = SHA256(canonical_encode({
    normalized_netlist,
    logical_simulation_config
}))

execution_environment_hash = SHA256(canonical_encode({
    simulator_build,
    pdk_version,
    model_file_hashes,
    container_digest,
    backend_versions,
    measurement_implementation_version
}))

reproducibility_id = SHA256(canonical_encode({
    design_identity_hash,
    execution_environment_hash,
    random_seed,
    analysis_settings
}))

comparison_policy_id = versioned tolerance / numerical-equivalence policy
```
- Numerical tolerance is a **comparison policy**, NOT circuit identity. Simulator output is compared under that policy; never asserted byte-identical.

### 10.3 libngspice Concurrency & Worker-Process Isolation Architecture (§14 & Stage 2)
Do not attempt in-process multi-threading with libngspice. Native C libraries with global/static memory state create severe race-condition, callback contamination, and reentrancy risks under threading. The platform mandates **worker-process isolation from Day One**:
`Job Scheduler -> Worker Process -> single libngspice instance -> results/artifacts -> parent`
Stage 2 concurrent validation tests (1-, 2-, and 4-job concurrent workloads) assert:
- No result appears under the wrong Job ID.
- No cross-run state, parameter, or callback leakage.
- Job cancellation or crash in one worker process does not corrupt another.
- Repeated runs are deterministic under declared seeds and configs.
- The public `Job` and `Simulator` contracts remain clean and independent of the underlying process worker pool.

### 10.4 Canonical `MetricContract` Matrix (§14 & Stage 3)
Measurements are governed by explicit `MetricContract` objects before implementation. Minimum matrix:
- **DC/AC Gain**: DC or AC as declared, amplifier/diff-pair benchmark.
- **Bandwidth**: AC, amplifier with declared reference and crossing rule.
- **Phase Margin**: Loop-gain/return-ratio analysis on defined closed-loop benchmark (never a current mirror).
- **Slew Rate**: Large-signal transient, declared step-response benchmark.
- **Power**: OP/transient average with declared supply-current sign and integration window.
- **Offset**: Differential DC (+ mismatch/MC where claimed).
- **Settling Time**: Closed-loop step with declared final-value estimator and error band.

### 10.5 Declared `StatisticalProtocol` for Robustness (§14 & Stage 4.5)
Every PVT/Monte Carlo yield headline must include or link to: $N$ (sample count), seeds, corners, supply set, temp set, variation mechanisms, sampling method, metric thresholds, pass/fail counts, yield estimate, confidence interval, and exact Experiment IDs. There is no universal "95% pass" target.

### 10.6 CACE Integration Boundary (§14.5)
The Design Engine is the sole authority on specifications, metric definitions, pass/fail thresholds, and provenance. CACE is strictly an **adapter/bridge** for characterization execution.

### 10.7 Physical Backend Decision Spike (§14.4 & Stage 8)
KLayout is primary viewer/geometry candidate, but single-device spike tests KLayout, Magic, and Netgen behind `LayoutBackend`. Use the best adapter for each step; do not force single-tool monopoly. Never trust a PCell on clean LVS alone; visual review in KLayout is mandatory.

### 10.8 Product Wording & Marketing Claims (§14.7)
Use **"spec-to-physical-verification"** or **"spec-to-verified-design"**. Do not claim "production signoff" or "Virtuoso replacement" without tapeout validation evidence.

---

## 11. Tooling, Extensions & MCP Server Architecture (§3)

### 11.1 Always-On Tooling (Installed for Stage 0)
- **Filesystem MCP**: Safe file read/write across workspace.
- **Git MCP / Built-in Git**: Diff inspections, commit logs, blame analysis.
- **Sequential-Thinking MCP**: Multi-file planning and structured reasoning.
- **Ruff + Mypy (Strict)**: Static analysis and edit-time type safety.
- **Pytest + Pytest-cov**: Mandatory test execution and coverage verification.
- **Docker / Podman**: Execution confined inside pinned container image.
- **Pre-commit Hooks**: Enforce clean formatting and strict type checks before commit.
- **Error Lens**: Instant inline diagnostics.

### 11.2 Stage-Specific Additions
- **Stage 0**: GitHub Actions CI (`act` for local smoke testing).
- **Stage 1**: SQLite Viewer, `diff-so-fancy`.
- **Stage 2**: ngspice CLI in container, waveform plotter (`matplotlib`/`gaw`).
- **Stage 3**: Jupyter kernel in container (interactive formula verification).
- **Stage 4**: Optuna Dashboard.
- **Stage 4.5**: Seaborn / Plotly (corner & MC distribution inspection).
- **Stage 5**: LangSmith / Langfuse / structured log viewer.
- **Stage 6**: LangGraph, local vector DB (LanceDB/Chroma), embeddings model (`bge-m3`/`nomic-embed-text`).
- **Stage 7**: Playwright (automated UI driving for UI $\equiv$ API equivalence test).
- **Stage 8**: KLayout Python API, Magic/Netgen in container.
- **Stage 10**: Firejail / gVisor sandboxing with hard CPU/memory/network limits.

🚫 **Strictly Prohibited**: Auto-commit extensions, auto-merge bots, or unattended "YOLO mode" shell execution before Stage 4.

---

## 12. Host Hardware & Storage Budget (§1.4)

- **Hardware Profile**: 16GB RAM, RTX 4060 (8GB VRAM), ~100GB free disk space.
- **Compute Load**: ngspice simulations on benchmark circuits (inverter, current mirror, diff pair, common-source, Miller op-amp) are sub-second to a few seconds CPU load.
- **Windows / WSL2 Rule**: Run Docker via WSL2 (never Hyper-V). Periodically compact the WSL2 virtual disk (`diskpart` / `wsl --manage --compact`), as WSL2 vdisks silently expand and do not auto-shrink.
- **Disk Discipline**: Run `docker system prune` after each container rebuild. Pull only Sky130 primitive devices for Stage 1, not the full multi-gigabyte standard-cell library.
- **Local Models**: No local LLM weights needed until Stage 5+. Maximum model size on 8GB VRAM is a 7–8B model at 4-bit quant (~4–5GB footprint).

---

## 13. Engine Roster & Cost Discipline Routing (§1.1 & §1.3)

| Task Situation | Assigned Engine | Configuration / Notes |
|---|---|---|
| New subsystem, no repo precedent | OpenCode / Primary Agent | `GEMINI_STRONG_MODEL`, full context |
| Mechanical change following existing pattern | OpenCode / Primary Agent | `GEMINI_FAST_MODEL` (cheap & fast) |
| PDK syntax or units touching | OpenCode / Primary Agent | Gemini with local PDK docs in context |
| Golden reference / Adversarial test authoring | **ChatGPT Plus** (Web) | Preserves model-family adversarial separation |
| Architecture / Plan reviews | **ChatGPT Plus** (Web) | Independent reasoning check |
| Bonus third-family sanity review | Claude chat | Human-in-the-loop review |
| In-product copilot (Stages 5–6) | Gemini API / Local 7–8B | Governed by `LLMProvider` |
| Explaining an error you already understand | **None** | Read the traceback directly |
| Rewriting a stage "more cleanly" | **None** | It passes tests or it doesn't |

---

## 14. Recurring Operational Prompt Library (§5)

### 14.1 Session Start Protocol (Run at start of every session)
```text
Context load. Before anything else:
1. Read AGENTS.md. Confirm the four laws back to me in one line each.
2. Read docs/stages/stage-<N>.md — the current stage brief.
3. Read the last 5 commit messages and tell me where we left off.
4. Run `make test` and report the current state. Do not fix anything yet.
Then wait. I will give you the task.
```

### 14.2 Session Handoff Protocol (Run before closing any session)
```text
Write docs/handoff.md containing:
- What was completed this session, per commit
- What is verified by a human vs. what is only asserted by you
- Every open HUMAN CHECKPOINT and its status
- What the next session should do first
- Anything you were uncertain about and resolved by guessing
The last bullet is the important one. Be specific.
```

### 14.3 Bug Triage Protocol
```text
A test is failing: <paste error>.
Do NOT fix it yet. First:
1. Classify the failure against the §2 taxonomy.
2. State the minimal reproduction.
3. Give me your top hypothesis and the ONE piece of evidence that would falsify it.
4. Go get that evidence.
Then propose a fix. If the fix involves editing a golden reference, a tolerance,
or a test assertion, stop and raise a checkpoint instead of proceeding.
```

### 14.4 PDK Anti-Hallucination Gate
```text
You are about to write Sky130 <model binding | device syntax | layer name | DRC rule reference>.
Before you write it:
1. Name the exact PDK file that documents this.
2. Read it. Quote the relevant lines.
3. Only then write the code, and cite the quoted lines in the docstring.
If you cannot locate the file, say so and stop. Do not proceed from memory.
```

### 14.5 Adversarial Code Review Protocol (Run via ChatGPT Plus / Different Model)
```text
Review this diff against AGENTS.md and docs/master-build-plan-v3.1.md.
You did not write it. Do not be agreeable.
Check specifically for:
- Any value stored in non-SI units
- Any path to ngspice/KLayout/schema that bypasses the Design Engine API
- Any bypass of the pre-simulation validation gate
- Byte-equality assertions on simulation output
- A stage marked complete without a human checkpoint
- Scope beyond the current stage, or anything tagged [defer] in the plan
- A number in a comment, docstring, or report that no simulation produced
- An error message that says "failed" without a taxonomy classification
Output: a list of violations with file:line. If there are none, say so plainly.
```

### 14.6 The "Are You Sure" Probe
```text
You just told me <claim>.
Which of these is true:
(a) I ran it and observed this
(b) I read it in a file in this repo — name the file
(c) I am inferring from the code without running it
(d) I am recalling this from training data
Answer with one letter and the supporting detail. Nothing else.
```

---

## 15. Known Fatal Anti-Patterns (§7)

1. ☠️ **The Plausible Number**: An agent reports gain = 62 dB. It never ran a simulation. Nothing crashed. Three stages are built on top of a hallucination. Mitigation: Grounding rule (§9) and §14.6 probe.
2. **Golden-Reference Drift**: The agent edits the golden reference file to make a broken compiler test pass. Mitigation: Golden files are read-only in CI; human commit required to change them.
3. **Silent Unit Coercion**: A float is a float. If units are a variable naming convention rather than a strict type/boundary check, bugs will compound. Mitigation: Strict SI base units throughout.
4. **The Helpful Side Door**: *"I added a direct SQLite read in the UI for speed."* This destroys the Design Engine architecture. Reject immediately on sight.
5. **Checkpoint Fatigue**: Rubber-stamping checkpoints wastes time and provides zero security. Either independently verify the artifact or remove the checkpoint.
6. **Review-Loop Addiction**: §11 declared planning complete. The next artifact that teaches anything real is a failing test from actual libngspice output. Build Stage 0 and Stage 1 before requesting more architecture critiques.
7. **Multi-Stage Prompts**: Prompts attempting to build multiple stages at once create code that appears to work but fails fatally in Stage 6. Keep commits split and focused.
