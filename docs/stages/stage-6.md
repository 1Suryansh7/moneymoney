# Stage 6 — Topology Intelligence & Design Knowledge Base

> **Layer 2 Stage Brief**  
> Source of truth: `docs/master-build-plan-v3.1.md` / `final_build.md` (v3.2) §4 (Stage 6) & §13.3 (AI-03).  
> Prompt playbook: `final_prompt.md` (v1.2) §4 (Stage 6) & §10.5.

---

## 1. Scope

Build the foundation for AI-guided analog topology selection and sizing:
1. **Canonical Topology Template Library**:
   - `current_mirror` (NMOS simple/cascode current mirror)
   - `diff_pair` (NMOS input pair with PMOS active mirror load and tail source)
   - `common_source` (NMOS common-source with PMOS active load)
   - `cascode` (NMOS telescopic cascode gain stage with PMOS load)
   - `folded_cascode` (Folded cascode operational amplifier)
   - `two_stage_miller` (Two-stage operational amplifier with Miller compensation)
2. **Design Knowledge Base Linkage**:
   - Link each template to historical trials from the `experiment` and `measurement` tables.
   - Empirical capability boundary extraction (observed gain, bandwidth, power, yield).
3. **Multi-Criteria Retrieval Engine (AI-03)**:
   - Rank candidates using specification similarity + topology capability + historical PVT yield - failure penalty.
   - Retrieve both successes (for sizing starting points) and relevant failures (anti-patterns).
   - Pass adversarial test: never copy a failed sizing due to high text similarity alone.
4. **CandidateCircuitIR & Proposal State Machine**:
   - Immutable structured object: `topology_id`, `parameters`, `reasoning`, `evidence_ids`, `requested_spec_id`, `confidence`.
   - Workflow: `PROPOSED -> VALIDATED -> SIMULATED -> EVALUATED -> AWAITING_HUMAN -> COMMITTED / REJECTED`.
   - Provenance: write `ai_action` row immediately upon proposal generation.
5. **Sizing Optimization Benchmark**:
   - Spec: "Design a 2-stage Miller op-amp, 60dB gain, 40MHz UGB".
   - Optuna sizing loop against hard constraints ($A_v \ge 1000\text{ V/V}, f_u \ge 40\text{ MHz}$).
   - Emit mandatory blocking human checkpoint alert (§8 & §12) awaiting accept/reject.

---

## 2. Non-Goals & Defers

- No free-form netlist prose or arbitrary graph hallucination (deferred to Stage 10 V3.0).
- No GUI schematic editor (deferred to Stage 7).
- No auto-commit flag or bypass of human approval gate.
- No non-SI units in parameters, storage, or APIs.

---

## 3. Done-When Benchmarks

1. All 6 canonical templates instantiate into valid SQLite schemas and pass `validate()`.
2. Adversarial retrieval test proves the retriever ranks robust successes above failed trials.
3. Proposal workflow enforces fail-closed validation and immediate `ai_action` logging.
4. "Design a 2-stage Miller op-amp, 60dB gain, 40MHz UGB" produces a sized proposal verified by real SPICE simulation and halts at the blocking human checkpoint.
