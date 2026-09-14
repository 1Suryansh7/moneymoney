# RFC-002: Grounded Tutor (Failure Explanation First, Proposal Gates Second)

- **Status**: Accepted 2026-09-14 (all 4 §10 verdicts = proposals: keyword rules; 20-prompt Eval, ChatGPT-Plus adversarial half ordered as follow-up; log-only metering; CI-green exposure, no flag). v0-backend committed; v1 + docs sync (ADR-036/037) pending.
- **Date**: 2026-09-12
- **Scope**: Wiring `AssistPanel` to real explanation and proposal
  machinery under constraints that make hallucination structurally
  impossible rather than merely discouraged.
- **Non-goals**: Open-ended circuit synthesis, student modeling,
  Socratic dialogue state, autonomous canvas edits, hosted-model
  default, any feature whose evidence base is not yet measured.

---

## 1. Problem

A chatbox wired to a raw LLM is a confident liar with a schematic
canvas — precisely the Plausible Number failure mode (AGENTS.md §7)
aimed at the audience least able to detect it. The existing
`AssistPanel` is 100% canned theater (a hardcoded corner answer and
dead suggestion buttons). The tutor earns trust only if every
sentence it emits is either grounded in ledger rows or an explicit
refusal, and every state change it proposes passes validation plus
human accept. This RFC defines that cage before any wiring.

## 2. Ground truth this design stands on (read, not assumed)

| Fact | Source |
|---|---|
| `explain_failure` resolves evidence IDs to ledger rows, checks verbatim citation, refuses uncited prose with `REFUSAL`, writes `AIAction` before returning (refusals included) | `ai/explainer.py:55-131` |
| `POST /copilot/explain` serves this over HTTP with MockProvider only | `api/server.py`, 7B-7 |
| `CandidateCircuitIR.validate_schema()` enforces known templates, positive SI numerics, mandatory evidence IDs | `topology/proposal.py:52-70` |
| `execute_proposal_workflow` runs propose → validate → instantiate → simulate → evaluate with provenance-first logging | `topology/proposal.py:94-` |
| `decide_proposal` exists for accept/reject/edit verdicts | `topology/proposal.py:211` |
| Residency: `DISABLED` / `LOCAL_ONLY` (default) / `HOSTED_ALLOWED` (explicit opt-in), pre-call disclosure, `redact_payload` secret scrubbing | `ai/residency.py`, `ai/provider.py` |
| Model IDs by capability alias only (`GEMINI_STRONG_MODEL` / `GEMINI_FAST_MODEL`), health-checked at startup | AGENTS.md §9.5 |
| `AssistPanel` input + suggestions exist but answer nothing real | `UI design 1/src/ic/chrome/Overlays.tsx:214-264` |

## 3. Sequencing law (non-negotiable)

**Tutor maturity ≤ verified-base width.** The tutor may discuss
exactly what the measurement ledger covers (today: 3 structures,
gain + bandwidth + study telemetry) and must refuse everything
else. Each new testbench widens the allowed territory; no calendar
date or demo overrides this. Capability ladder:

- **v0 — failure explanation** (this RFC's build): grounded answers
  about the user's own runs, or refusal. No synthesis whatsoever.
- **v1 — proposal gates**: sizing/topology suggestions as typed
  diffs through the existing workflow, human accept required.
- **v2+ — open teaching**: unlocked only when the verified base
  covers the syllabus being taught. Not designed here.

## 4. v0 design: failure explanation

`POST /copilot/chat {message, context_ids?}` classifies intent
deterministically (keyword rules, not a model):

- **Failure question** (mentions a job, error, sim, run, trial):
  resolve to the newest failed job in scope → `explain_job`
  pipeline → return `{prose, cited_ids, action_id}` verbatim.
- **Anything else** (concepts, how-tos, out-of-domain topologies):
  return `REFUSAL` ("Insufficient data to explain this failure."
  generalized: *"I do not have a verified testbench for this
  topic."*) with a null action trail marked `refused-no-evidence`.
  No model call is even attempted — refusal is a code path, not a
  generation gamble.

UI renders either the prose with its evidence chips (clickable →
navigates to the ledger row) or the refusal. No third state exists.

## 5. v1 design: proposal gate (human in the loop, always)

1. Model output is `CandidateCircuitIR` JSON **only**. Free text is
   never parsed for intent (structured-before-prose, §9.1).
2. Malformed JSON fails closed (rejected, logged, surfaced as
   "proposal malformed" — never auto-repaired and executed).
3. Valid objects enter `execute_proposal_workflow` up to the
   simulate/evaluate gates; results plus the candidate render in a
   **Review Proposed Change modal** showing diff vs current cell,
   validation status, and measured outcomes.
4. Nothing instantiates before the human clicks **Accept / Reject /
   Edit**; the verdict writes back to `AIAction.human_decision`
   (`decide_proposal`). Default-selected button is never Accept
   (keyboard-enter safety).
5. The Golden Rule holds end to end: model proposes (typed),
   simulator decides (measured), human commits (clicks).

## 6. Refusal Eval harness (the proof the cage holds)

`tests/test_tutor_refusal.py` (v0 commit): 20 scripted prompts —
10 in-domain failures (must ground: assert cited_ids non-empty and
present verbatim in prose), 10 out-of-domain
("Design me a 10-bit SAR ADC", "phase margin of an LC
oscillator", "size this FinFET", …) — **must refuse, 100% target**.
Harness mechanics run in CI against `MockProvider` variants (canned
citing / canned uncited / empty) to prove the harness itself
catches uncited prose deterministically. Hosted-model transcripts
are evaluated by human eyes quarterly, never in CI (nondeterminism
cannot gate a build).

## 7. Residency, cost, secrets (college-buyer relevant)

- Default mode `LOCAL_ONLY`; the chat box shows its mode chip
  at all times. Hosted calls require explicit per-workspace opt-in
  with pre-call disclosure (provider, model, artifact classes sent).
- `redact_payload` scrubs keys, tokens, env, and unrelated files
  before every dispatch; scrub failures fail closed, never degrade.
- Per-seat token caps with graceful degradation to refusal
  ("explanation budget exhausted") — an institutional buyer will
  ask who pays per student; this is the answer, designed now.
- No model generation is ever hardcoded; capability aliases only.

## 8. UI contract (AssistPanel rewire)

- Delete the canned corner answer and dead suggestion buttons
  (fabrication, same class as `waveforms.ts`). Suggestions become
  capability-reflecting prompts that route to live endpoints
  (failure explain → v0; trial narration → study telemetry; sizing
  ideas → v1 gate when built). Suggestions naming unbuilt
  backends (DRC explain — Stage 8) stay deleted until built.
- Chat history is local component state; every assistant message
  carries its `action_id` and either evidence chips or the refusal
  marker. No message renders without one of the two.
- Dumb-frontend holds: no metric math, no vector parsing, no
  prompt engineering in TypeScript. Prompts live server-side,
  versioned (`prompt_version` on every `AIAction` row).

## 9. Build order (commits, each independently green)

1. v0: intent classifier + chat route (explain-or-refuse) +
   refusal Eval harness + AssistPanel rewire + Playwright
   (grounded answer shows chips; out-of-domain shows refusal).
2. v1: `CandidateCircuitIR` generation path (mock/local model) +
   Review modal + accept/reject wiring + `human_decision`
   ledger proof + Playwright (accept instantiates, reject
   instantiates nothing).
3. Docs sync (ADR-036 audience/horizon freeze + ADR-037 tutor
   sequencing law) + push.

## 10. Open questions for review (blocking)

1. v0 intent classifier: keyword rules (deterministic, reviewable)
   or a tiny local classifier (needs training data we lack)?
   Proposal: keyword rules; ML only with an Eval it can fail.
2. Refusal Eval: is 20 prompts enough, and who authors the
   adversarial half (recommend the ChatGPT-Plus adversarial
   separation per engine roster)?
3. Per-seat token caps: enforce server-side now or log-only
   metering first?
4. Should v0 ship behind a feature flag until the Eval harness
   is green in CI, or is CI-green sufficient to expose?
