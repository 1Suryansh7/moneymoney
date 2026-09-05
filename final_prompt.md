# Analog IC Design Platform — AI Prompt Playbook (v1.2 — implementation-readiness patched)

> v1.2 preserves every v1.1 + AI-expansion capability and patches the final load-bearing implementation issues: metric contracts, libngspice isolation testing, formal reproducibility identities, declared Monte Carlo statistics, CACE-as-adapter, explicit AI data-residency modes, product UX acceptance, physical-backend spike, and model aliases instead of stale provider model IDs.

> Adapted from v1.0 for what you actually have: **Gemini Pro** (subscription) + **OpenCode** (Go-based CLI agent) + **ChatGPT Plus**, on a 16GB RAM / RTX 4060 (8GB VRAM) / ~100GB-free laptop.
> Everything below that isn't flagged **[changed]** is unchanged from v1.0 — the original prompts and rules never actually named a specific model, so they transfer as-is. Still the companion to **Master Build Plan v3.1**: that document says *what* to build, this says *what to type, into what, at which stage*.
>
> **[ADDENDUM]** Master Build Plan v3.1 has a compatible addendum (LLM provider abstraction, structured AI-proposal schemas, AI-action provenance, a fuller reproducibility/environment-hash definition, and Design Engine API versioning, plus two sequencing clarifications). Nothing here or there was rewritten — the additions are marked **[ADDENDUM]** inline, at the stage where each actually gets built. See §9 at the end for an index.

---

## 0. How to use this (unchanged)

Every prompt here assumes a three-layer stack. Never send layer 3 without layers 1 and 2 loaded.

| Layer | What it is | Where it lives | Changes how often |
|---|---|---|---|
| 1. Global rules | Non-negotiable behavior for any agent touching this repo | `AGENTS.md` at repo root, auto-loaded | Almost never |
| 2. Stage brief | Scope, done-when, checkpoints for the current stage | `docs/stages/stage-N.md`, pasted at session start | Once per stage |
| 3. Task prompt | The single commit-sized ask | Chat / CLI | Every task |

⚠️ The single biggest failure mode in AI-driven builds is **scope creep per prompt**. One prompt = one commit = one testable claim. If a prompt would produce more than ~400 lines of new code, split it.

**[changed]** OpenCode reads `AGENTS.md` natively (falls back to `CLAUDE.md` if absent). Layer 1 needs zero edits to work with your setup — paste §2 below into your repo root as-is.

---

## 1. Your actual engine roster

### 1.1 Primary assignments **[changed — replaces v1.0 §1.1]**

| Job | v1.0's pick | What you use | Why it still works |
|---|---|---|---|
| Long-horizon build agent (Stages 0–4) | Claude Code | **OpenCode** + Gemini API key (free via AI Studio; your Google AI Pro sub gives elevated daily quota there) | OpenCode reads `AGENTS.md` faithfully, multi-file edit discipline is solid with the configured `GEMINI_STRONG_MODEL` |
| Architecture / plan review | GPT-5-class reasoning | **ChatGPT Plus** (web) | Exact match, zero setup change |
| PDK & doc grounding (Sky130 syntax, DRC rules) | Gemini-class 1M-context | **Gemini Pro** (web/AI Studio) | Exact match — this is literally the recommended tool |
| Analog domain sanity checking | GPT-5-class + you | **ChatGPT Plus** + you | Match — advisory only, never a substitute for §12 checkpoints |
| Golden reference / adversarial test authoring | "a different model than the one that wrote the code" | Whichever of OpenCode+Gemini / ChatGPT Plus **didn't** write the code under review | Preserves adversarial separation with only two engines |
| In-product copilot (Stage 5–6, ships to users) | Ollama/vLLM local | Defer — see §1.4 | Not needed for months |
| Fast inner-loop completion | Cursor Tab / Copilot | Skip | Not essential to this workflow |
| Knowledge Base embeddings (Stage 6+) | `bge-m3` / `nomic-embed-text` locally | Same, when Stage 6 arrives | Tiny (a few hundred MB–1.2GB), no hardware concern |

Bonus: this Claude chat is a third distinct model family, available for free whenever you want one more pair of eyes on an adversarial review or a stuck checkpoint.

Note: ChatGPT Plus ($20/mo) doesn't include API billing, so OpenCode can't call it directly — use it via the web chat for review/checkpoint roles, which is how the playbook's copy-paste sessions already work for most of this anyway.

### 1.1.1 Provider model aliases **[v1.2 — mandatory maintenance rule]**

Operational prompts **never hard-code a Gemini generation such as "Gemini 3 Pro" or "Gemini Flash"**. Keep exact provider model IDs in configuration and route by capability alias:

```text
GEMINI_STRONG_MODEL = <current high-reasoning Gemini model id>
GEMINI_FAST_MODEL   = <current low-latency/cost Gemini model id>
```

A config/health check must verify that each alias resolves to an available model before an agent session starts. Updating a provider model is a config change plus benchmark run, not a playbook rewrite. The adversarial-separation rule still applies regardless of the concrete model behind an alias.

### 1.2 Reality check on the open-weights shortlist **[changed — replaces v1.0 §1.2]**

The original shortlist (Qwen3-Coder-480B, DeepSeek-V3.x, Hermes 4 70B, Codestral, GLM-4.6, Kimi K2) assumes either paid API access to huge models or a workstation GPU well beyond an 8GB-VRAM laptop. None of it is required right now:

- **Stages 0–4:** OpenCode + Gemini covers the "long-horizon build agent" role — no local model needed.
- **Stage 5–6 (later):** if/when you want the in-product copilot running fully locally, the realistic option on your hardware is a **~7–8B model at 4-bit quant** (Qwen2.5-7B-Instruct or Llama-3.1-8B-Instruct class, ~4–5GB file — fits comfortably in 8GB VRAM). That's smaller than the playbook's Hermes 4 70B suggestion, but Stage 5's explainer role is deliberately narrow and grounded (§5's citation-or-refuse rule), so a 7–8B model is plenty. Cross this bridge when you get there — don't download anything now.

### 1.3 Routing policy (cost discipline) **[changed — replaces v1.0 §1.3]**

| Situation | Route to |
|---|---|
| New subsystem, no precedent in repo | OpenCode + `GEMINI_STRONG_MODEL`, full context |
| Mechanical change following an existing pattern | OpenCode + `GEMINI_FAST_MODEL` (cheap/fast) |
| Anything touching PDK syntax or units | OpenCode + Gemini, PDK docs in context, **always** |
| Explaining an error you already understand | Don't. Read the traceback |
| Rewriting a stage "more cleanly" | Don't. It passes tests or it doesn't |
| Second opinion / adversarial review | **ChatGPT Plus** — different model family than whoever wrote the code |

### 1.4 Hardware & storage budget **[new]**

**Fine as-is, no changes needed for Stages 0–4:**
- ngspice sims on the benchmark circuits (inverter, current mirror, diff pair, common-source, Miller op-amp) are trivial CPU/RAM load — sub-second to a few seconds each.
- KLayout viewing/DRC on small benchmark cells is light.
- SQLite + the local Job runner (master plan §1) is designed for exactly one machine, one process, a small worker pool.
- The RTX 4060 is irrelevant until Stage 8 layout rendering, and not compute-limiting even then.

**Storage budget (100GB free):**
- Pinned Docker image (ngspice + KLayout + Magic + Netgen + Python deps + Sky130 primitives): roughly **3–10GB**. Pull only the Sky130 primitive devices you need for Stage 1, not the full standard-cell library.
- Repo + deps: under 2GB.
- No local LLM weights needed until Stage 5+.
- **If you're on Windows:** run Docker via WSL2, not Hyper-V, and periodically compact the WSL2 virtual disk — it silently grows even after you delete images. This is the single most common way to quietly blow a 100GB budget without downloading anything huge.
- Discipline: `docker system prune` after each stage's image rebuild; don't hoard old tags.

**Where hardware will eventually matter (not yet):** Stage 5–6's local copilot, if you self-host it, caps you at roughly a 7–8B model at 4-bit quant on 8GB VRAM — fine for its narrow, grounded role. Not a blocker today.

### 1.5 LLMProvider abstraction, mapped to your actual setup **[ADDENDUM]**

Master plan §1 addendum defines an `LLMProvider` interface so the LLM stays a swappable client. Mapped onto your actual roster (§1.1):

| LLMProvider implementation | Maps to |
|---|---|
| `GeminiProvider` | OpenCode's Gemini API key (AI Studio) — the only one called programmatically pre-Stage 5 |
| `LocalProvider` | The future 7–8B local model, §1.2/§1.4 — implement the interface now, point it at nothing until Stage 5 |
| `MockProvider` | Deterministic canned responses for tests — every Stage 5/6 test uses this, never a live API call |
| _(no provider)_ | ChatGPT Plus and this Claude chat stay human-in-the-loop review tools, called manually via web/copy-paste — they're not wired into `LLMProvider` because nothing in the pipeline calls them programmatically |

Build the interface at Stage 5 (first real caller), not Stage 0 — an abstraction with one real implementation and a mock is enough; don't add `OpenAIProvider` until you actually have a reason to call OpenAI's API.

---

## 2. Global rules — paste this as `AGENTS.md` at repo root (unchanged)

This is layer 1. OpenCode loads it automatically (as do Claude Code, Cursor, Cline, Codex CLI, and OpenHands, if you ever add them).

```
# AGENTS.md — Open-Source AI-Native Analog IC Design Platform

## Identity
You are a build agent for an analog IC design platform (Sky130 + ngspice + KLayout).
The canonical spec is docs/master-build-plan-v3.1.md. It is the source of truth.
If your instinct conflicts with the plan, the plan wins. If the plan is genuinely
ambiguous, stop and ask — do not resolve it yourself.

## The four laws
1. NEVER mark a stage "done" on your own judgment. Done-when criteria in §4 are
   verified by the human, not asserted by you.
2. NEVER write Sky130 model-binding or device syntax from memory. Read the PDK
   reference in the repo or ask for it. PDK conventions are a known hallucination risk.
3. NEVER let anything reach ngspice without passing schema + connectivity + unit +
   model-binding validation first. The validation gate in §2 has no bypass.
4. NEVER give a subsystem a private path to ngspice, KLayout, or the schema.
   Everything routes through the Design Engine API (§3). No side doors, ever.

## Units
All internal values are SI base units: farads, ohms, hertz, volts, amps, seconds.
No "10MHz" strings in storage, in the schema, in function arguments, or in the
database. Human formatting happens at the display layer only. If you find yourself
parsing an SI prefix outside the UI layer, you have made a mistake.

## Scope control
- One task = one commit = one testable claim.
- Anything tagged [defer] in the plan is out of scope. Do not build it "while you're
  in there." Do not add abstraction for a future stage.
- Do not add dependencies without asking. The pinned dependency set is deliberate.
- Do not refactor code you were not asked to touch.

## Testing
- Every behavior change ships with a test in the same commit.
- Netlist comparisons are byte-identical against golden references.
- Simulation output comparisons are tolerance-based (netlist hash +
  sim-config hash + numerical tolerance). Never assert byte equality on
  floating-point simulator output.
- Never edit a golden reference to make a test pass. If a golden reference looks
  wrong, raise a HUMAN CHECKPOINT.
- Never mark a test xfail/skip to get green. Report the failure.

## Error handling
Every failure is classified against the taxonomy before it is reported:
Syntax -> Schema -> Netlist -> SPICE convergence -> Operating point -> Constraint
-> PVT -> Monte Carlo -> DRC -> LVS -> PEX -> Post-layout performance.
"Simulation failed" is never an acceptable error message. Say which category and why.

## Honesty rules
- If you did not run it, say you did not run it.
- If you are inferring rather than reading, label it as inference.
- If a number came from a model's guess rather than from a simulator, that number
  does not go in a report, a docstring, or a commit message.
- Never write a plausible explanation for behavior you did not observe. Say
  "I don't have the data for this" instead.

## HUMAN CHECKPOINT protocol (§12) — mandatory
When you are about to trust output in a checkpoint category for the FIRST time,
stop and emit this exact block, then wait:

[ HUMAN CHECKPOINT — <Stage / Component> ]
Trigger: <what specifically caused this stop>
Check: <the exact, concrete thing to verify — not "review this">
Status: BLOCKING — not proceeding until you confirm.

Blocking categories: first golden reference; first simulation waveform; first
implementation of each measurement metric; any Monte Carlo percentage claim;
any AI-proposed topology or sizing (every time, no exceptions); first clean
DRC+LVS pass; any unvalidated PDK/model syntax.
Advisory categories: optimizer results at a search-space boundary or suspiciously
fast convergence; any AI-generated explanation of a failure.
Once a specific pattern is human-verified once, do not re-flag identical
subsequent runs — only new patterns or anomalous results from old ones.

## Working style
- Read before you write. State which files you read.
- Plan in bullets before multi-file changes; wait for approval on plans over 3 files.
- Prefer the smallest diff that satisfies the test.
- End every task with: what changed, what was tested, what is still unverified.

## AI provenance & structured output [ADDENDUM]
Starting Stage 5, these three rules apply to every LLM call and every AI-generated
proposal:
1. Every call to a model goes through the LLMProvider interface (master plan §1
   addendum) — never a bare SDK call inline in application code. Record model,
   provider, prompt_version, temperature, seed, token usage, timestamp, request id.
2. Every AI-generated explanation or proposal writes an AIAction row (master plan
   §2 addendum) before anything downstream trusts it — this is provenance, not
   optional logging.
3. An AI proposal crosses into the Design Engine as the structured object defined
   in master plan §4 Stage 6 addendum (topology_id, parameters, reasoning,
   evidence_ids, requested_spec_id) — never as prose the system parses to extract
   intent. If you find yourself regex-ing or prompt-parsing an LLM's free text to
   decide what it proposed, stop — that is a side door into the Design Engine and
   Law 4 above already forbids it.

## AI data residency & secrets [v1.2]
- Every Project/workspace has AI mode: DISABLED, LOCAL_ONLY, or HOSTED_ALLOWED.
- Default design-bearing work to LOCAL_ONLY unless the user explicitly enables a
  hosted provider for that Project/workspace.
- Before the first hosted call, surface the provider/model and the classes of design
  artifacts that will be sent; record the opt-in decision.
- Never send API keys, PDK credentials, license tokens, environment variables,
  unrelated files, or secret values to a model. Never persist them in AIAction.
- Switching to LOCAL_ONLY or DISABLED must block hosted calls immediately.
```

---

## 3. Extensions, MCP servers, and tooling per stage (unchanged, two notes)

### 3.1 Always-on (install at Stage 0)

| Tool | Type | Why |
|---|---|---|
| Filesystem MCP | MCP | Agent reads/writes repo without shell guessing |
| Git MCP or built-in git tool | MCP | Diff review before commit, blame during debugging |
| Sequential-thinking MCP | MCP | Forces plan-then-act on multi-file work |
| Ruff + mypy (strict) | Extension | Kills a whole class of silent agent errors at edit time |
| pytest + pytest-cov | Test | Non-negotiable from Stage 0 per §9 of the master plan |
| Docker/Podman extension | Extension | Agent must run inside the pinned image, never on host Python |
| Pre-commit hooks | Git | Blocks the agent from committing unformatted or untyped code |
| Error Lens / inline diagnostics | Extension | You see agent-introduced type errors instantly |

### 3.2 Stage-specific additions

| Stage | Add | Purpose |
|---|---|---|
| 0 | GitHub Actions, `act` for local CI | Smoke test must run before any agent commits |
| 1 | SQLite Viewer extension, `diff-so-fancy` | Eyeball the schema and golden-netlist diffs by hand |
| 2 | ngspice CLI in-container, waveform plotter (matplotlib/`gaw`) | You cannot verify a waveform you cannot see |
| 3 | Jupyter kernel in-container | Hand-verify each measurement formula interactively — this is a §12 blocking check |
| 4 | Optuna Dashboard, `optuna-dashboard` MCP if available | Spot degenerate optima at a search-space boundary |
| 4.5 | seaborn/plotly for corner + MC distributions | Sample-count sanity, per §12 |
| 5 | Structured-logging viewer, LangSmith or Langfuse | Trace whether the explainer cited a real ErrorRecord |
| 6 | LangGraph, a local vector DB (Chroma/LanceDB), embeddings model | Knowledge Base retrieval per §5 of the master plan |
| 7 | Playwright MCP, Storybook or equivalent | UI-vs-API equivalence test needs automated UI driving |
| 8 | KLayout Python API, Magic/Netgen in-container, image-capable model | Visual DRC/LVS review is blocking |
| 10 | Firejail/gVisor or container sandboxing, resource limits | Hard requirement before multi-user, per master plan §4 Stage 10 |

🚫 **Do not install:** auto-commit extensions, auto-merge bots, or any "YOLO mode" that lets an agent run shell commands unattended before Stage 4. The §12 protocol assumes a human is in the loop at defined moments; a harness that auto-approves defeats the entire mechanism.

**[changed] Notes for your setup:**
- None of §3.1/3.2 is tied to which LLM drives OpenCode — nothing here changes.
- OpenCode supports MCP servers directly, so Filesystem MCP / Git MCP / Sequential-thinking MCP all work exactly as described.
- Stage 5's LangSmith/Langfuse and Stage 6's vector DB + embeddings model are all lightweight — install them when those stages actually arrive, not before.

---

## 4. Stage-by-stage prompts

Each task prompt below is **unchanged from v1.0** — none of it ever named a specific model. Only the **Engine:** line per stage is adapted for your setup.

### Stage 0 — Architecture & Packaging
**Engine [changed]:** OpenCode, backed by a Gemini API key from AI Studio. Flash-tier is fine here — this stage is stubs and packaging, low stakes.

```
STAGE 0 — Architecture & Packaging.

Read docs/master-build-plan-v3.1.md sections 0, 1, 3, 4 (Stage 0), 9, 10 before
writing anything. Confirm what you read.

Build, in this order, as separate commits:

1. Dockerfile + docker-compose with PINNED versions of: Python, ngspice
   (with libngspice shared lib), Sky130 PDK, KLayout, Magic, Netgen. Pin by
   digest or exact tag, never "latest". List every pinned version in the commit body.

2. Makefile with exactly three targets: setup, test, run-example.
   Done-when: fresh clone + `make setup && make test` passes with ZERO manual steps.
   Verify this by describing the exact command sequence a stranger would run.

3. Interface stubs only — no implementations:
   - Simulator (abstract)
   - LayoutBackend (abstract)
   - PDKAdapter (abstract)
   Each method typed, docstringed with units in SI, and raising NotImplementedError.

4. Design Engine API skeleton (§3), empty implementations, correct signatures:
   create_project, create_cell, instantiate, validate, netlist, simulate,
   check_constraints, optimize, run_drc, extract, compare.
   These signatures are a contract. Design them as if you cannot change them later.

5. CI smoke test (GitHub Actions) that builds the image and runs `make test`.

Constraints:
- No business logic in this stage. Stubs and packaging only.
- The unit system module can be created but must be empty of domain logic here.
- Do not create the database schema yet. That is Stage 1.

Deliver a summary listing: pinned versions, the exact stranger-runs-this command
sequence, and every API signature you committed to.

[ADDENDUM] Commit granularity: this stage is Commits 1–2 of the master plan §10
addendum's commit-level breakdown (bootstrap, then interfaces + Design Engine API
skeleton) — land them as two separate commits, not one, even though both are
low-risk stubs. Stage 1 picks up at Commit 3.
```

### Stage 1 — Circuit Kernel 🔴 blocking checkpoint
**Engine [changed]:** OpenCode + Gemini for the compiler. **ChatGPT Plus** authors the adversarial golden-reference test — a different model family than whatever wrote the compiler.

```
STAGE 1 — Circuit Kernel.

Read §2 (Core data model) and §4 Stage 1. The unit system is live from the FIRST
line of code in this stage — no exceptions, no "we'll convert later."

Build as separate commits:

1. Unit system: SI-base internal representation, explicit converters at the
   boundary, a type or newtype per physical quantity if the language allows.
   Write the test that proves "10MHz" never appears in storage.

2. SQLite schema for: Project, Library, Cell/Schematic, Symbol, Instance, Port,
   Net, Parameter, Technology, ModelBinding, Specification, Testbench, Analysis,
   Job, Constraint, DesignRevision, ErrorRecord, Artifact.
   Specification must model hard constraints, soft objectives, AND weighted
   objectives — each with tolerance and priority. Not one generic "target" field.
   ErrorRecord uses the §2 failure-taxonomy enum. Exclude Measurement and
   Experiment — those are Stage 3 and 4.

3. Netlist compiler: schema -> SPICE netlist. Deterministic ordering.

4. Pre-simulation validator: schema + connectivity + unit + model-binding checks.
   This is the gate from §2. Nothing bypasses it.

STOP CONDITION: Before you compare any compiler output against a golden reference
netlist, you must first create the golden reference and raise:

[ HUMAN CHECKPOINT — Stage 1 / Netlist compiler ]
Trigger: Golden reference netlist created for the NMOS instance.
Check: Verify by hand that this netlist is ELECTRICALLY CORRECT — node order,
  terminal assignment (d/g/s/b), W/L in meters, model name matches the actual
  Sky130 model card. Print the netlist and the schema it came from side by side.
Status: BLOCKING — not proceeding until you confirm.

Do not write the Sky130 model card syntax from memory. Read the PDK reference.
```

**Second-model prompt (adversarial test author) — paste into ChatGPT Plus:**

```
You did not write this code and you are not here to be agreeable.

Here is the netlist compiler and the golden reference it is tested against.
Write tests that try to BREAK it, not tests that confirm it works. Specifically:
- A device whose terminals are connected in a swapped-but-still-simulable order
- A parameter given in the wrong unit that still produces a plausible netlist
- A model binding that does not exist in Sky130
- A floating net that connectivity validation should catch
- A W/L pair below the PDK minimum

For each: state what SHOULD happen per §2's validation gate, then whether it does.
Do not fix anything. Report only.
```

### Stage 2 — Simulation Kernel 🔴 blocking checkpoint
**Engine [changed]:** OpenCode + Gemini.

```
STAGE 2 — Simulation Kernel.

Read §1 (Execution model), §2 (SimulationRun), §4 Stage 2, and master plan §14.1.

Build:

1. NgspiceBackend implementing the Simulator interface, via libngspice
   (shared library, not subprocess shelling to the ngspice binary).

2. The Job runner from §1: a Job record (id, type, status, inputs, artifacts)
   plus a LOCAL single-machine executor and a status table in SQLite. Do NOT make
   thread safety an architectural assumption. The public Job API must be independent
   of whether workers are threads or isolated processes.

3. Implement the v3.2 reproducibility contract as separate concepts:

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

   HARD RULE: numerical tolerance is a comparison policy, not circuit identity.
   Simulator OUTPUT is compared under the selected policy; never byte-for-byte.

4. Waveform parsing into a typed structure, SI units throughout.

5. LIBNGSPICE CONCURRENCY / ISOLATION PROOF — mandatory before Stage 3:
   Run the same deterministic fixture under repeated 1-job, 2-job, and 4-job
   simultaneous workloads. Include fixtures with intentionally different circuits,
   seeds, callbacks, and output sizes. Assert:
   - no waveform/result appears under the wrong Job id
   - no cross-run parameter or callback state leakage
   - cancellation/cleanup of one Job does not corrupt another
   - repeated runs are deterministic under the declared seed/config
   - no crashes, use-after-free symptoms, deadlocks, or orphaned simulator state

   If the pinned libngspice wrapper fails ANY of these tests, do not weaken the test.
   Keep the Job/Simulator interfaces and move concurrent execution to isolated worker
   processes. Re-run the same 1/2/4-job suite until it passes.

Done-when: the hand-built inverter runs through libngspice via a Job, returns a
transient waveform entirely from schema data, and the selected execution strategy
passes the isolation suite.

STOP CONDITION: the moment the first transient waveform comes back, raise:

[ HUMAN CHECKPOINT — Stage 2 / First simulation ]
Trigger: First transient waveform returned from libngspice for the inverter.
Check: Plot it and save the PNG to artifacts/. Verify rail-to-rail swing, correct
  logic inversion, plausible rise/fall times for Sky130 at this sizing, and no
  convergence artifacts. This run becomes the template every other testbench copies.
Status: BLOCKING — not proceeding until you confirm.

Do not proceed to Stage 3 with an unverified waveform OR an unproven concurrency/
isolation strategy.
```

### Stage 3 — Measurement & Specification Engine 🔴 blocking, once per metric
**Engine [changed]:** OpenCode + Gemini.

```
STAGE 3 — Measurement & Specification Engine.

Read §2 (Specification, Measurement, MetricContract), §4 Stage 3, and master plan
§14.1-14.2 before writing a metric implementation.

FIRST DELIVERABLE — Metric Contract + Analysis/Testbench Matrix.
Do not write generic measurement functions until this exists.

Create MetricContract with at least:
- metric_id / version
- semantic definition
- required Analysis type
- required testbench capability
- stimulus and operating condition
- observed nodes/ports
- exact formula / extraction algorithm
- sign convention
- SI units
- measurement window / reference value
- interpolation/crossing rule when relevant
- invalid/ambiguous-data behavior
- comparison policy
- golden fixture id

Minimum matrix:

Metric          Required analysis        Canonical benchmark intent
DC/AC gain      DC or AC as declared     amplifier / differential amplifier
Bandwidth       AC                       amplifier; declared reference + crossing
Phase margin    loop gain / return ratio defined closed-loop feedback benchmark
Slew rate       large-signal transient   declared step-response benchmark
Power           OP/transient average     supply-current sign + measurement window
Offset          DC (+ mismatch if claim) differential-input methodology
Settling time   transient                closed-loop step + declared error band

HARD RULES:
- A current mirror is not a generic phase-margin/slew/settling benchmark.
- "Gain" is not implemented until its contract says DC gain vs AC gain vs differential
  gain (etc.).
- Phase margin cannot be extracted from an arbitrary output waveform; the loop-gain
  method and injection/reference topology must be explicit.
- Power must define supply-current sign and averaging/integration interval.
- Offset must define the methodology and whether mismatch/MC is included.
- Settling time must define final-value estimation, error band, and staying condition.

Then implement MetricContracts ONE AT A TIME. For EACH metric, in its own commit:
  a. Write/freeze the contract and testbench requirement.
  b. State formula/algorithm and sign convention in code/docstring with SI units.
  c. Run it only on an appropriate canonical benchmark.
  d. STOP and raise:

  [ HUMAN CHECKPOINT — Stage 3 / MetricContract + measurement: <metric> ]
  Trigger: First implementation of <metric>.
  Check: Here is the MetricContract, testbench, raw data, exact algorithm, computed
    value, sign, and units: <values>. Hand-calculate or independently verify the
    declared metric and confirm the implementation matches the CONTRACT.
  Status: BLOCKING — not proceeding until you confirm.

  e. Only after confirmation, move to the next metric.

Then implement Specification evaluation:
- hard constraints -> pass/fail
- soft objectives -> better-is-better score
- weighted objectives -> figure-of-merit combination
- each with tolerance and priority
- every spec criterion references the MetricContract that can prove it

Evaluation runs against nominal now; the API must already accept a corner/sample
axis so Stage 4.5 does not require a rewrite.

A wrong metric definition silently poisons optimization, AI explanations, Pareto
analysis, surrogate labels, and the Knowledge Base. Treat each MetricContract as a
first-class engineering contract, not a convenience function.
```

### Stage 4 — Optimization Layer 🟡 advisory checkpoint
**Engine [changed]:** OpenCode + Gemini.

```
STAGE 4 — Optimization Layer. This is the first demoable product. No GUI.

Read §4 Stage 4 and §5 (Experiment Ledger).

Build:
1. Optimizer interface (abstract), OptunaOptimizer as the first implementation.
2. Every trial is a Job (§1) and writes ONE ROW to the Experiment Ledger:
   parameters, measurements, verdict, reproducibility hash, timestamp,
   success AND failure alike. Failed trials are data, not noise — §5 depends on this.
3. Search space definition tied to the Specification, in SI units.
4. Nominal evaluation first. Wire the PVT-corner axis but leave Monte Carlo to 4.5.

Done-when: the common-source amplifier gets sized against a real spec via real
simulations, reproducibly — same seed, same result, verified by re-running.

ADVISORY CHECKPOINT — raise this whenever it triggers:

[ HUMAN CHECKPOINT — Stage 4 / Optimizer results ]
Trigger: <a trial sits at a search-space boundary | convergence in suspiciously
  few trials | the objective improved by more than an order of magnitude>
Check: The spec may be mis-scoped in a way that lets the optimizer find a
  degenerate solution. Here are the winning parameters and where they sit
  relative to the bounds: <detail>. Confirm the spec is real before I record
  this as a success.
Status: ADVISORY — proceeding, but flagged.

Never report an optimization result without the trial count and the seed.
```

### Stage 4.5 — Robustness 🔴 blocking on any percentage claim
**Engine [changed]:** OpenCode + Gemini.

```
STAGE 4.5 — Robustness. PVT corners and Monte Carlo, per §2, §4, and §14.2.

Extend Stage 3 and 4 so Specification evaluation runs across:
  nominal -> declared PVT corners -> Monte Carlo samples.
Each corner and MC sample is its own Job. The Experiment Ledger records all of them
individually — never store only the aggregate.

Build:
1. Corner definition bound to PDKAdapter (process, voltage, temperature).
2. Monte Carlo sampling using ONLY variation mechanisms supported by the pinned PDK
   and specific device/model cards. Do not invent a distribution. Distinguish process
   variation from local mismatch when the PDK/model distinguishes them.
3. A versioned StatisticalProtocol containing at minimum:
   - sample count N
   - random seed(s)
   - corner set
   - supply set
   - temperature set
   - variation mechanism(s) and source model/card ids
   - sampling method
   - metric threshold(s)
   - confidence interval / uncertainty method
4. Aggregate reporting: pass count, fail count, yield estimate, confidence interval
   or justified uncertainty statement, worst-case corner, distribution summary,
   protocol id, and exact Experiment ids.

Done-when: the two-stage Miller op-amp benchmark produces a reproducible robustness
report under one declared StatisticalProtocol and rerunning with the same frozen
inputs reproduces the expected statistical dataset/provenance. There is NO universal
"95% pass" completion target. A 95% result is merely one possible observed result.

HARD RULE: you may never emit a sentence of the form "X% of samples pass" without
first raising:

[ HUMAN CHECKPOINT — Stage 4.5 / Robustness claim ]
Trigger: About to report "<the claim>".
Check: N=<n>; seeds=<seeds>; corners=<corners>; supply/temp=<sets>;
  variation=<PDK mechanisms>; sampling=<method>; threshold=<threshold>;
  CI/uncertainty=<method/result>. Confirm this declared protocol supports the claim.
Status: BLOCKING — not proceeding until you confirm.
```

### Stage 5 — AI Diagnostics & Copilot 🟡 advisory
**Engine [changed]:** OpenCode + Gemini builds it. The shipped explainer model (the one end users talk to) is a separate question — see §1.4. When you get here, a small local 7–8B model or just the hosted API path (the plan says "LLM always optional") both work with the system prompt below unchanged.

```
STAGE 5 — AI Diagnostics & Copilot. Build only after Stage 4 is verified.

Read §2 (failure taxonomy) and §4 Stage 5.

Build:
1. Structured error explainer. CLASSIFY FIRST, EXPLAIN SECOND. The classifier is
   deterministic code against the taxonomy enum — it is NOT an LLM call. The LLM
   only writes prose about an already-classified, already-retrieved ErrorRecord.
2. Optimizer-result narration, grounded strictly in Stage 3/4 Measurement rows.

HARD CONSTRAINT — the grounding rule:
Every sentence the explainer produces must be traceable to a specific
ErrorRecord ID or Measurement ID. Implement this as an actual check, not a prompt
instruction: the explainer returns (prose, cited_ids). If cited_ids is empty, the
system returns "Insufficient data to explain this failure" — it does NOT return
prose. A plausible story with no citation is the exact failure mode this stage
must be architected against.

Orchestration: plain functions. Do NOT introduce LangGraph here — §9 says one
framework, and it arrives at Stage 6.

Done-when: a failed convergence run and a completed optimization run each get a
correct, data-grounded plain-English explanation, and a deliberately
unexplainable case correctly returns the refusal string.

[ADDENDUM] Dependency note: "build only after Stage 4 is verified" above is
sufficient to start. But production-grade robustness-aware explanations (citing
a PVT-corner or Monte Carlo ErrorRecord) need Stage 4.5's data to exist first.
Until then, the grounding rule will correctly cause the explainer to refuse on
any PVT/MC failure it's asked to explain — that refusal is expected behavior,
not a bug to work around.

[ADDENDUM] Grounding-rule granularity: implement citation-checking per FACTUAL
CLAIM, not per grammatical sentence. "The amplifier failed the gain requirement.
Measured gain was 48.2 dB against a 60 dB spec." is two sentences grounded by the
same Measurement/Specification pair — that's one shared citation, not a
requirement to cite each sentence separately. A per-sentence check is more
rigid than the intent and will reject correctly-grounded explanations for
formatting reasons.
```

**System prompt for the shipped explainer model (served locally or hosted):**

```
You explain analog simulation failures. You are given a classified ErrorRecord
and its associated Measurements. You may ONLY state things present in that data.
You may not speculate about causes not evidenced in the record. If the record is
insufficient, say exactly: "Insufficient data to explain this failure."
Never invent a numeric value. Never suggest a fix you cannot ground in the record.
End every explanation with the ErrorRecord ID you used.
```

### Stage 6 — Topology Intelligence 🔴 blocking, every single time
**Engine [changed]:** OpenCode + Gemini.

```
STAGE 6 — Topology Intelligence / Design Knowledge Base. V0.2+.

Read §5 and §4 Stage 6.

Build:
1. Topology templates for: current mirror, differential pair, common-source,
   cascode, folded cascode, two-stage Miller. Each with a schematic template,
   parameters, constraints, and documented trade-offs.
2. Link each template to its historical experiments from the Experiment Ledger —
   which sizings worked, which failed, for which spec. This linkage IS the moat (§5).
3. Retrieval: the AI SEARCHES this store and FILLS a template. It NEVER invents
   connectivity from scratch. Enforce this in code: the proposal API accepts a
   template_id plus parameters. There is no free-form netlist entry point for the AI.
4. LangGraph enters here, and only here, per §9.

The proposal workflow, implemented as a real state machine:
  AI proposes -> schema validation -> simulate -> check_constraints
  -> human approval (accept / reject / compare) -> commit

HARD RULE: there is no code path from "all checks passed" to "committed" that
does not pass through a human decision. Not a config flag, not an --auto-approve
setting, not a "trusted mode." If you find yourself writing one, stop and ask.

Every proposal raises:

[ HUMAN CHECKPOINT — Stage 6 / AI design proposal ]
Trigger: AI proposed <topology> with sizing <params>.
Check: Validation <status>, simulation <status>, constraints <status>.
  Proposed vs current design diff: <diff>. Accept / reject / compare?
Status: BLOCKING — never auto-committed, even when all checks pass.

Done-when: "design a 2-stage Miller op-amp, 60dB gain, 40MHz UGB" produces a
template instantiation that validates, simulates, gets sized by Stage 4, and
sits as a proposal awaiting accept/reject.

[ADDENDUM] The AI's output at step 1 of the proposal workflow is the structured
object from master plan §4 Stage 6 addendum (topology_id, parameters, reasoning,
evidence_ids, requested_spec_id) — schema validation in step 2 validates THIS
object, not prose. Log it as an AIAction row (master plan §2 addendum) the moment
it's generated, before validation runs — a rejected or failed-validation proposal
is still provenance data, same principle as failed trials in the Experiment Ledger.
```

### Stage 7 — Schematic UI
**Engine [changed]:** OpenCode + Gemini.

```
STAGE 7 — Schematic UI. One more client of the Design Engine API (§3).

Read §3 and §4 Stage 7.

HARD ARCHITECTURAL CONSTRAINT: the UI calls the Design Engine API and nothing
else. If you need a capability the API does not expose, you ADD IT TO THE API —
you do not reach around it. Any direct UI access to SQLite, ngspice, or KLayout
is an automatic reject, regardless of convenience.

Build incrementally: canvas -> symbol placement -> wiring -> property editing
-> netlist preview -> simulate button -> results view.

Also build DesignRevision branching and diffing here (deferred from §2) — it only
becomes useful now that there is something to visually diff.

PRODUCT UX CONTRACT — Stage 7 is not accepted as "a canvas with buttons".
Implement the first-time designer flow using product-language, not architecture-language:
  New Project -> choose PDK + AI privacy mode -> define/confirm specs -> surface missing
  assumptions -> show MetricContract coverage -> propose/select known topology -> schematic
  -> size/optimize -> compare Pareto candidates -> inspect failures/sensitivity -> accept or
  branch DesignRevision -> physical verification handoff.

The user must NOT need to understand SQLite tables, Job internals, LLMProvider, or the
Design Engine API to complete this flow. Those remain inspectable for power users.

Required views by V0.4/V1.0: Project Home, Spec Builder, Design Workspace, Run Center,
Explore/Optimize, Evidence Inspector, Revision Decision Gate, and a Physical Verification
view/handoff when Stage 8/9 exists.

ACCEPTANCE TEST (the corrected one — read it carefully):
A design built in the UI and the same design built via the Python API must produce
MATCHING NETLIST HASHES and simulation results WITHIN DEFINED NUMERICAL TOLERANCE.
Not byte-identical simulation output. Netlists byte-identical; sim results within
tolerance. Write this as an automated test using Playwright to drive the UI.
```

### Stage 8 — Physical Design 🔴 blocking on first clean DRC/LVS
**Engine [changed]:** OpenCode + Gemini for the build. For the visual review itself, both Gemini and ChatGPT are multimodal — paste the KLayout screenshot into either for a second pair of eyes, but the actual sign-off is yours, per §12.

```
STAGE 8 — Physical Design.

FIRST: run a backend technology spike before treating KLayout as the universal physical
implementation backend:
  one transistor/device -> programmatic geometry -> DRC -> extract -> LVS -> PEX
  -> pre/post-layout simulation comparison.

Record which backend/tool performed each operation, exact versions/decks, and artifacts.
The spike must run through LayoutBackend/related adapters. If KLayout is the best viewer/
geometry surface but Magic or Netgen is materially more reliable for a verification or
extraction operation, USE THE BETTER ADAPTER. Do not force a single-tool architecture.

After the spike, proceed incrementally:
viewer -> geometry model -> import -> basic PCells -> placement -> DRC
-> LVS -> extraction/PEX.

Do not skip ahead. Each arrow is a separate commit with its own test.

All physical-tool access goes through LayoutBackend or its defined verification/extraction
adapters. No UI/AI/client gets a private KLayout/Magic/Netgen path.

PCELL WARNING: a PCell can be geometrically non-physical and still pass LVS. LVS
checks connectivity, not manufacturability-in-spirit. Never trust a PCell
generator on a clean LVS alone.

STOP CONDITION:

[ HUMAN CHECKPOINT — Stage 8 / DRC-LVS-PCells ]
Trigger: First clean DRC + LVS pass on <benchmark circuit>.
Check: Open this in the KLayout viewer and VISUALLY review the geometry before
  the PCell generator is reused on any other cell. Screenshot saved to
  artifacts/layout/<cell>.png. Confirm the layout is physically sensible, not
  merely rule-clean.
Status: BLOCKING — not proceeding until you confirm.

Also: any Sky130 layer, PCell parameter, or DRC deck construct you have not
already validated once against the actual PDK documentation triggers the
cross-cutting PDK checkpoint. Read the deck. Do not recall it.
```

### Stage 9 — Post-Layout Physical Verification Loop
**Engine [changed]:** OpenCode + Gemini.

```
STAGE 9 — Post-Layout Physical Verification Loop.

Feed post-layout extracted parasitics back into the Stage 3 measurement engine.
Reuse the existing measurement functions unchanged — if a metric needs different
code for post-layout, that is a bug in the Stage 3 abstraction, not a new feature.

Deliverable: a pre- vs post-layout delta report, side by side, per metric, with
the percentage degradation and which metrics now violate their Specification.

If a post-layout number is BETTER than pre-layout, flag it as suspicious rather
than reporting it as a win. Parasitics do not improve performance.
```

### Stage 10 — Expansion (V2.0+)

```
STAGE 10 — Expansion. Do not start any of this before V1.0 ships.

Scope: multi-PDK via PDKAdapter (GF180/IHP), AI-assisted layout/placement,
surrogate models, RF/EM, cloud collaboration.

GATING REQUIREMENT — read this before writing a line:
Sandboxing becomes a HARD requirement the moment AI-generated netlists or third
parties can trigger jobs without a human in the loop. Before any multi-user or
cloud feature ships: container isolation, CPU/memory resource limits, wall-clock
timeouts on every Job, and no unnecessary network access from the execution
sandbox. This is not a Stage 0 concern for a single-user local tool. It is
non-negotiable here.

Also: adding a second PDK is the real test of whether PDKAdapter was a genuine
abstraction or a Sky130-shaped hole. Expect to find leaks. Fix the interface,
do not special-case the new PDK.
```


### Cross-cutting — CACE adapter boundary [v1.2]

```text
CACE INTEGRATION RULE.

The Design Engine is canonical for Specification, MetricContract, Measurement,
pass/fail, Experiment, and provenance.

If CACE is integrated, implement it as an adapter/import-export/execution bridge:
  Design Engine canonical spec/metric definitions
    -> CACE adapter representation/run
    -> import raw/results
    -> normalize back into canonical Measurement/Experiment rows

Never let a CACE datasheet/config become a second independent definition of gain,
limits, units, or acceptance criteria. Add a round-trip test that detects semantic loss
or mismatch between the canonical MetricContract and the adapter representation.
```

### Cross-cutting — AI data residency / hosted-provider opt-in [v1.2]

```text
Implement Project/workspace AI execution modes:
  DISABLED
  LOCAL_ONLY       # default for design-bearing work
  HOSTED_ALLOWED   # explicit user opt-in

Before the first hosted call for a Project/workspace, show provider/model and the
classes of design artifacts that would be sent. Persist only the opt-in decision and
normal AI provenance — never credentials/secrets.

Build a provider-call guard that rejects hosted calls unless mode=HOSTED_ALLOWED.
Build a redaction/filter layer that excludes API keys, environment variables, PDK
credentials, license tokens, unrelated files, and configured secret fields.

Tests:
- LOCAL_ONLY blocks all hosted-provider network/model calls
- DISABLED blocks local and hosted model calls
- HOSTED_ALLOWED permits only the configured provider through LLMProvider
- switching from HOSTED_ALLOWED to LOCAL_ONLY immediately blocks the next call
- secret fixtures never appear in serialized prompt payloads or AIAction rows
```

### Cross-cutting — product claim / wording rule [v1.2]

```text
For Sky130 V1 docs/UI/marketing, use "spec-to-physical-verification" or
"spec-to-verified-design" for the end-to-end flow.

Do not claim foundry-certified production signoff or a general professional
Virtuoso/Spectre replacement unless a later release has evidence for that claim.
Internal stage names may discuss signoff concepts, but user-facing claims must state
what was actually verified: DRC/LVS/PEX/post-layout measurements under the declared
open PDK/toolchain.
```

---

## 5. Recurring prompt library (unchanged)

### 5.1 Session start (every new agent session)

```
Context load. Before anything else:
1. Read AGENTS.md. Confirm the four laws back to me in one line each.
2. Read docs/stages/stage-<N>.md — the current stage brief.
3. Read the last 5 commit messages and tell me where we left off.
4. Run `make test` and report the current state. Do not fix anything yet.
Then wait. I will give you the task.
```

### 5.2 Session handoff (before you close a session)

```
Write docs/handoff.md containing:
- What was completed this session, per commit
- What is verified by a human vs. what is only asserted by you
- Every open HUMAN CHECKPOINT and its status
- What the next session should do first
- Anything you were uncertain about and resolved by guessing
The last bullet is the important one. Be specific.
```

### 5.3 Bug triage

```
A test is failing: <paste>.
Do NOT fix it yet. First:
1. Classify the failure against the §2 taxonomy.
2. State the minimal reproduction.
3. Give me your top hypothesis and the ONE piece of evidence that would falsify it.
4. Go get that evidence.
Then propose a fix. If the fix involves editing a golden reference, a tolerance,
or a test assertion, stop and raise a checkpoint instead of proceeding.
```

### 5.4 PDK anti-hallucination gate

```
You are about to write Sky130 <model binding | device syntax | layer name |
DRC rule reference>.
Before you write it:
1. Name the exact PDK file that documents this.
2. Read it. Quote the relevant lines.
3. Only then write the code, and cite the quoted lines in the docstring.
If you cannot locate the file, say so and stop. Do not proceed from memory.
```

### 5.5 Adversarial review (run with a different model than the author)

```
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

Output: a list of violations with file:line. If there are none, say so plainly —
do not manufacture findings to seem useful.
```

### 5.6 The "are you sure" probe

```
You just told me <claim>.
Which of these is true:
(a) I ran it and observed this
(b) I read it in a file in this repo — name the file
(c) I am inferring from the code without running it
(d) I am recalling this from training data
Answer with one letter and the supporting detail. Nothing else.
```

---

## 6. Checkpoint response templates (your side, unchanged)

Consistency matters — the agent learns your gate is real.

| Your verdict | Reply |
|---|---|
| Verified | `CONFIRMED — <what you checked and how>. Proceed.` |
| Verified with a caveat | `CONFIRMED WITH NOTE — <note>. Record the note in the docstring. Proceed.` |
| Wrong | `REJECTED — <the specific error>. Do not work around it. Fix the root cause and re-raise the checkpoint.` |
| Not enough info to judge | `INSUFFICIENT — give me <exact artifact>. Still blocking.` |
| Pattern now trusted | `CONFIRMED — this pattern is now validated. Do not re-flag identical subsequent instances. New patterns and anomalies still flag.` |

---

## 7. Anti-patterns — things that will quietly kill this project (unchanged)

☠️ **The plausible number.** An agent reports gain = 62 dB. It never ran a simulation. Nothing crashed. You built three stages on top of it. → Mitigation: §5.6 probe, and the grounding rule in Stage 5.

- **Golden-reference drift** — the agent edits the golden file to make a test pass. Make golden files read-only in CI and require a separate, human-authored commit to change one.
- **Silent unit coercion** — a float is a float. If your unit system is a naming convention rather than a type, it will fail. Use typed quantities.
- **The helpful side door** — "I added a direct DB read in the UI for performance." This is how §3 dies. Reject on sight.
- **Checkpoint fatigue** — if you rubber-stamp checkpoints, they cost you time and buy you nothing. Either actually check, or remove the checkpoint from the list.
- **Review-loop addiction** — §11 of the master plan already declared planning finished. The next artifact that teaches you something is a failing test from real libngspice output. Do not run a fifth architecture review.
- **Multi-stage prompts** — asking one prompt to build Stages 1 and 2 produces code that runs and is wrong in ways you will find in Stage 6.

---

## 8. Quick reference card **[changed — Engine column adapted]**

| Stage | Engine | Checkpoint | Key artifact |
|---|---|---|---|
| 0 | OpenCode + Gemini | — | `make setup && make test` green from fresh clone |
| 1 | OpenCode + Gemini + ChatGPT Plus (adversarial) | 🔴 Golden netlist | Hand-verified NMOS golden reference |
| 2 | OpenCode + Gemini | 🔴 First waveform | Inverter transient PNG |
| 3 | OpenCode + Gemini + Jupyter | 🔴 Per metric | Hand-calc match, all 7 metrics |
| 4 | OpenCode + Gemini + Optuna Dashboard | 🟡 Degenerate optima | Sized common-source amp, reproducible |
| 4.5 | OpenCode + Gemini + stats tooling | 🔴 Any % claim | MC yield with N and corner set |
| 5 | Hosted API (deferred) or small local 7–8B later | 🟡 Ungrounded prose | Explainer that refuses when uncited |
| 6 | OpenCode + Gemini + LangGraph + vector DB | 🔴 Every proposal | Miller op-amp proposal awaiting accept |
| 7 | OpenCode + Gemini + Playwright | — | UI ≡ API netlist hash match |
| 8 | OpenCode + Gemini (+ ChatGPT for a second visual pass) | 🔴 First clean DRC/LVS | Visually reviewed layout |
| 9 | OpenCode + Gemini | — | Pre/post-layout delta report |
| 10 | — | Sandbox gate | Isolated execution before multi-user |

---

## 9. Addendum index [NEW]

Everything below was added by a later review pass, on top of v1.1, without changing anything above. Nothing here is new scope — it's five implementation details plus two sequencing clarifications, each already placed inline at the stage it applies to. Listed here as one lookup table:

| Addition | What it is | Where it's built | Inline location |
|---|---|---|---|
| LLMProvider abstraction | Swappable interface for any LLM call | Stage 5 (first real caller) | §1.5, master plan §1 |
| AIAction provenance | A row logged for every AI action | Stage 5–6 | AGENTS.md addendum, master plan §2 |
| Structured proposal schema | JSON object (not prose) for AI proposals | Stage 6 | Stage 6 prompt, master plan §4 |
| Reproducibility/environment hash | Full env captured, not just netlist+config hash | Stage 2 (SimulationRun) | master plan §2 |
| Design Engine API versioning | `DesignEngine v0.1`, additive-vs-breaking rule | Stage 0 onward | master plan §3 |
| Stage 5 / 4.5 dependency note | Robustness-aware explanations need 4.5 first | Stage 5 | Stage 5 prompt, master plan §4 |
| Commit-level breakdown | 7-commit split of the "first concrete commit" | Stage 0–3 | Stage 0 prompt, master plan §10 |

---

🎯 One rule above all the rest: **the agent proposes, the simulator decides, and you commit.** Every prompt in this document is a way of enforcing that ordering.


---

## 10. AI Feature Expansion Prompt Pack — September 2026 [ADDITIVE]

This section is an additive companion to Master Build Plan §13. It does not replace any Stage 0–10 prompt above. Use these prompts only when the owning stage is already complete enough to supply the required structured data.

### 10.0 Global AI-feature implementation law

Paste this before any AI feature task in this section:

```text
AI FEATURE IMPLEMENTATION LAW — READ BEFORE WRITING CODE

Read AGENTS.md, the current stage prompt, and Master Build Plan §13.

Do not weaken any existing gate.

The feature may PROPOSE, PREDICT, NARRATE, RETRIEVE, or PRIORITIZE.
It may not become a new source of physical truth.

Authoritative truth remains:
- Design Engine validation for schema/connectivity/units/model binding
- ngspice for electrical simulation
- deterministic Measurement + Constraint evaluation
- DRC/LVS/PEX tools for physical verification
- human approval for promotion/commit where the plan requires it

Every AI call goes through LLMProvider or a dedicated model interface.
Every AI action is provenance-logged.
Every design-changing output is typed structured data before prose.
Every numeric claim must identify whether it is MEASURED or PREDICTED.
Malformed structured output fails closed.
Low-confidence or out-of-domain predictions fall back to the real tool.

Do not create a side door into ngspice, KLayout, SQLite, or committed design state.
```

### 10.1 Grounded Error Explainer 2.0 + diagnostic test proposals (AI-01)

```text
Implement AI-01 from Master Build Plan §13.3 on top of the existing Stage 5 explainer.

DO NOT replace the existing deterministic failure classifier or citation/refusal rule.

Add a typed output containing:
- failure_class
- supported_findings[]
- evidence_ids[]
- unknowns[]
- next_diagnostic_tests[]
- confidence
- summary

Rules:
1. supported_findings must each reference concrete ErrorRecord/Measurement/Artifact IDs.
2. unknowns must explicitly identify missing evidence.
3. next_diagnostic_tests are proposals only. Each must map to an existing or additive
   Design Engine analysis/measurement call and state what uncertainty it would resolve.
4. If evidence cannot support a root cause, do not guess one. Keep the cause in unknowns.
5. Add tests for: fully grounded explanation, partially grounded explanation,
   insufficient data/refusal, hallucinated ID rejection, and malformed model output.

Done-when: the explainer can distinguish "what is known" from "what should be measured
next" without turning the latter into a factual diagnosis.
```

### 10.2 Conversational Spec-to-Constraint Generator (AI-04)

```text
Implement AI-04 from Master Build Plan §13.3.

Input: user natural-language requirements.
Output: SpecDraft, NOT Specification.

SpecDraft must contain:
requested_function, constraints[], soft_objectives[], weighted_objectives[],
assumptions[], ambiguities[], missing_inputs[], source_text_hash,
needs_human_confirmation=true.

HARD RULES:
- Never silently default supply voltage, load, input CM range, output swing,
  temperature, PVT scope, stability/load condition, or measurement definition.
- Normalize proposed numeric values into SI but preserve the original phrase for audit.
- Detect contradictions and impossible unit combinations.
- Confirm every proposed metric has a registered Measurement implementation.
- No code path promotes SpecDraft -> active Specification without explicit human action.

Tests:
- vague request produces ambiguities/missing_inputs instead of invented defaults
- contradictory request is flagged
- unit conversion is correct
- unsupported metric is flagged
- human-confirmation gate cannot be bypassed
```

### 10.3 Deterministic Pareto service + AI Pareto narration (AI-05)

```text
Implement AI-05.

First build deterministic compute_pareto() over Experiment/OptimizationRun rows.
The LLM must not decide dominance.

Persist a ParetoSnapshot with:
objective definitions, directions, tolerances, filtered trial IDs,
non-dominated trial IDs, dominance relations, PVT/MC filter,
environment/reproducibility identifiers.

Then add narration that can answer trade-off questions using ONLY the snapshot and
linked Measurement rows.

Tests must prove:
- dominated/non-dominated classification on hand-built examples
- narration cannot cite a trial outside the snapshot
- a boundary/degenerate optimum is still flagged under the existing Stage 4 rule
- missing data causes refusal, not interpolation presented as fact
```

### 10.4 Sensitivity + bottleneck explainer (AI-13)

```text
Implement AI-13 only after the relevant Simulation/Measurement path is stable.

Build deterministic perturbation/sensitivity experiments first. Record each perturbation
as normal Jobs/Experiment rows.

The AI receives measured sensitivity results and explains:
- which parameters most affect each metric
- direction and approximate local magnitude from the measured perturbations
- which hard constraint is currently the bottleneck
- where the result is local and should not be extrapolated

Never ask the LLM to invent derivatives from the schematic.
Done-when: the explanation exactly matches a hand-checkable perturbation benchmark.
```

### 10.5 Template topology retrieval upgrade (AI-03)

```text
Upgrade Stage 6 retrieval per AI-03.

Retrieval ranking must use more than text embeddings. Combine:
- requested Specification similarity
- topology compatibility
- validated outcome
- PVT/MC robustness
- post-layout outcome when available
- semantic similarity as one feature, not the whole ranking

Retrieve BOTH successes and relevant failures.
Proposal evidence_ids must point to actual Experiment rows.

Add an adversarial test where the semantically closest experiment failed badly and a
slightly less similar experiment succeeded robustly. The retriever must not blindly
copy the failed sizing because embedding similarity was highest.
```

### 10.6 Active-learning experiment planner (AI-12)

```text
Implement AI-12 as a planner, not an executor.

Input: current spec, experiment history, uncertainty/sensitivity state, simulation budget.
Output: AIExperimentPlan containing candidate Jobs, rationale, expected information gain
(or another explicit selection score), budget, stop conditions, and evidence IDs.

The normal Job scheduler owns execution and enforces resource limits.
The planner cannot exceed the supplied budget.

If expected-information-gain math is implemented, it is deterministic code; the LLM may
narrate why a proposed experiment is useful but does not supply the authoritative score.
```

### 10.7 Surrogate modeling gate (AI-06)

```text
Implement AI-06 only after enough real Experiment data exists. Do not create a neural
network because the roadmap says "AI"; choose the simplest model that wins on held-out data.

Create a dedicated SurrogateModel interface and provenance record.
Required evaluation:
- train/validation split with leakage checks by design/spec group
- held-out MAE/RMSE or metric-appropriate error
- calibration / uncertainty quality
- applicability-domain or OOD detection
- simulated-vs-predicted residual logging

Prediction output must include predicted value, uncertainty, in_domain, model_id,
training_data_hash, and requires_spice_validation=true.

HARD RULE: no surrogate prediction may satisfy a Specification or sign off a design.
Any promoted candidate is simulated for real.
```

### 10.8 PDK Porting Assistant (AI-07)

```text
Implement AI-07 after the second PDK works through PDKAdapter without AI.

Do NOT implement "multiply W/L by process-node ratio" as the porting algorithm.

Build a source design intent extractor from validated source-PDK operating points:
gm/Id or equivalent inversion indicator, Vov/headroom, current density, intrinsic gain,
capacitances, voltage stress, matching area, current, and topology role where available.

Map device classes legally into the target PDK, propose a STARTING parameter set,
then route through target-PDK validation -> SPICE -> optimization -> PVT/MC.

The output is a proposal with source/target evidence and explicit unmapped assumptions.
Done-when: at least one benchmark ports between two real PDK adapters and is re-verified
entirely in the target PDK.
```

### 10.9 Multimodal DRC/LVS debugger + ECO proposals (AI-08)

```text
Implement AI-08 only after Stage 8 produces structured DRC/LVS artifacts.

Evidence precedence is mandatory:
1. DRC rule IDs + marker geometry + layers
2. LVS mismatch graph / device-net mapping
3. LayoutConstraint / design intent
4. extracted geometry/net metadata
5. screenshot/image context

Do not let the model infer a rule name or layer relationship from pixels when the
structured report does not contain it.

Return typed ECOProposal objects with target geometry/net, rationale, evidence IDs,
and expected effect. Applying an ECO creates a DesignRevision candidate and MUST rerun
DRC/LVS before human approval.

Adversarial test: give the model a visually suggestive screenshot but a conflicting
structured rule marker. The structured evidence must win.
```

### 10.10 AI-assisted placement clustering (AI-09)

```text
Implement AI-09 as LayoutConstraint proposal generation.

Allowed proposal types:
symmetry_pair, common_centroid_group, matched_group, proximity_group,
keep_apart_group, orientation_constraint, sensitive_net, high_swing_net,
noise_isolation_group, plus PDK-backed guard/well constraints only when verified.

The AI does not output final XY polygons as trusted geometry.
The deterministic placement/layout backend consumes validated LayoutConstraint objects.
Every generated layout still goes through DRC/LVS and the Stage 8 human checkpoint rules.
```

### 10.11 PEX/parasitic root-cause + ECO assistant (AI-17)

```text
Implement AI-17 after Stage 9 can produce pre/post-layout deltas and extracted parasitics.

Join:
- pre-layout Measurement
- post-layout Measurement
- PEX parasitic elements by net/device
- layout geometry metadata
- DesignRevision diff

Rank likely contributors using deterministic attribution/sensitivity where possible.
The LLM narrates that evidence and proposes ECOs.
No claim that a parasitic "caused" a regression unless the evidence supports it;
otherwise say "candidate contributor" and propose the confirming re-run.
```

### 10.12 Autonomous topology exploration sandbox (AI-10)

```text
Implement AI-10 only in V3 after the sandbox gate and the normal topology workflow are mature.

The model outputs CandidateCircuitIR, never raw trusted SPICE.
CandidateCircuitIR must pass:
- schema
- graph/connectivity
- units
- model binding
- basic static analog sanity checks
before compilation.

Execution sandbox requirements:
- no unnecessary network
- CPU and memory limits
- wall-clock timeout
- bounded output size
- bounded simulation count
- cancellation
- provenance for every attempt

After simulation, deduplicate against the Knowledge Base and log as EXPERIMENTAL.
There is no automatic promotion to a trusted topology template.
Promotion requires the same human approval philosophy as Stage 6 plus a defined
benchmark suite.

Never hard-code an assumed "99% fail / 1% pass" rate. Measure and report reality.
```

### 10.13 Knowledge-base curator + read-only natural-language query (AI-18 / AI-19)

```text
Build two distinct surfaces:

A) KB CURATOR
Mine validated Experiment/Measurement history for repeated patterns.
Output candidate LearnedHeuristic objects with evidence_ids, support_count,
counterexample_ids, scope, and promotion_state="candidate".
Never silently convert a correlation into a design rule.

B) READ-ONLY LEDGER QUERY
The LLM produces a constrained query plan against an allowlisted schema/view.
A deterministic query compiler executes it with read-only DB permissions.
Return exact trial/measurement IDs.
No SQL generated by the model is executed directly.
```

### 10.14 AI trust benchmark harness (AI-20) — required before shipping any AI feature

```text
Implement AIEvaluationRun and a sealed fixture set per AI capability.

Track, as applicable:
- structured output validity
- unsupported factual claim rate
- citation precision and recall
- refusal precision/recall on insufficient evidence
- proposal schema acceptance
- simulation/verification success of proposals
- human accept/edit/reject outcome
- latency and model cost
- end-to-end engineer time saved

Model/prompt changes cannot be promoted solely because one demo looks better.
Require a comparable benchmark report against the current champion configuration.
Store model, provider, prompt version, dataset/fixture hash, and code commit.
```

### 10.15 Adversarial AI-feature review prompt

```text
Review this AI feature diff against AGENTS.md and Master Build Plan §13.
You did not write it. Assume the most dangerous bugs are plausible, silent ones.

Check specifically for:
- AI numeric claims that are not marked MEASURED vs PREDICTED
- free-form prose being parsed into design-changing commands
- missing evidence IDs or fake/nonexistent citations
- a surrogate used as signoff or constraint truth
- PDK porting based only on geometry/process-node scaling
- image-only DRC/LVS conclusions that ignore structured reports
- AI-generated final layout geometry bypassing LayoutBackend validation
- experimental topologies entering trusted templates without human promotion
- malformed structured model output being silently "fixed" and executed
- missing OOD/uncertainty fallback to the real simulator/tool
- direct model SDK calls bypassing LLMProvider
- hidden state mutation by a read-only assistant
- no sealed benchmark/regression test for the feature

Output violations with file:line and severity. If none exist, say so plainly.
```

### 10.16 Product-value checkpoint prompt

Use after an AI feature is technically working:

```text
PRODUCT VALUE CHECK — AI FEATURE <name>

Compare the AI-assisted workflow against the same task without AI on a fixed benchmark.
Report:
- engineer time to result
- number of simulator/DRC/LVS jobs
- number of invalid proposals
- factual/citation errors
- human edits required
- inference cost and latency
- final verified design quality

Do not call the feature a win unless it measurably improves at least one important
workflow metric without degrading correctness/trust metrics.
```

---

**Expansion rule:** the point of these prompts is to add intelligence around the validated engine, not to turn model output into a second simulator. Build the data substrate first; then make the AI earn its place with measured workflow improvements.


---

## 11. v1.2 final implementation-readiness patch — apply before Stage 0

The architecture remains frozen. Before implementation starts, verify the repository/playbook contains all of these contracts:

1. MetricContract + Analysis/Testbench matrix before Stage 3 metrics.
2. libngspice 1/2/4-job isolation stress test in Stage 2, with process fallback.
3. design identity, execution environment, reproducibility id, and comparison policy separated.
4. declared StatisticalProtocol for every PVT/MC yield statement; no universal 95% target.
5. CACE only as an adapter; Design Engine remains measurement/spec authority.
6. AI modes DISABLED / LOCAL_ONLY / HOSTED_ALLOWED and secret filtering.
7. GEMINI_STRONG_MODEL / GEMINI_FAST_MODEL capability aliases in config, not frozen provider IDs.
8. Stage 7 first-time user journey as an acceptance test, not merely a schematic canvas.
9. Stage 8 one-device backend technology spike before locking tool responsibilities.
10. User-facing wording says spec-to-physical-verification / spec-to-verified-design until stronger claims are proven.

After that, stop planning and run Stage 0 -> Stage 1 -> Stage 2 on the real pinned environment.
