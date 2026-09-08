# Stage 5 — AI Diagnostics & Copilot (Stage Brief, Layer 2)

Source of truth: `final_build.md` Stage 5 + `final_prompt.md` Stage 5 (+ AI addendum).
Global rules: `AGENTS.md` (§9 AI laws apply from here on).

## 1. Scope (Atomic Commits, ~100–250 lines each)

| Commit | Content | Done-When |
|---|---|---|
| 5A | Deterministic taxonomy classifier + `AIAction` table (migration v8) | Prefix/category/spec evidence maps to exactly one of the 12 categories or raises; AIAction rows round-trip with FK-free ID references |
| 5B | `LLMProvider` (Gemini stdlib-urllib + Mock) + residency guard + secret filter | Alias-resolved models, mode-gated dispatch, redacted payloads; Mock-only tests, zero live calls |
| 5C | Grounded explainer + demos | (prose, cited_ids) with per-factual-claim citations; refusal string on empty evidence; failed-run + opt-run demos green |

## 2. Non-Goals (Out of Scope)

- No LangGraph (Stage 6 only).
- No vector DB, embeddings, or local model weights.
- No UI, no topology proposals (Stage 6), no autonomous actions.
- No `OpenAIProvider` (no caller exists).
- No live hosted calls in tests, ever — Mock only.

## 3. Design Rules (binding)

- CLASSIFY FIRST, EXPLAIN SECOND: the classifier is deterministic code over
  observed artifacts, never a model call. Unknown evidence fails closed
  (raises) instead of guessing a category.
- Every model call routes through `LLMProvider`; model IDs resolve via
  `GEMINI_*` aliases (UNCONFIGURED fails closed). Bare SDK/inline HTTP calls
  to a model endpoint are forbidden outside provider implementations.
- Residency default is `LOCAL_ONLY`; hosted dispatch requires explicit
  `HOSTED_ALLOWED` per call site + recorded opt-in. Secrets never leave the
  host and never persist in provenance.
- Grounding is per FACTUAL CLAIM (shared citations allowed), checked in code.
  Empty citations return exactly `"Insufficient data to explain this failure."`.
- AIAction rows are written BEFORE downstream consumption, for explanations
  and narrations alike — including refused ones (refusal is provenance too).

## 4. Checkpoint (AGENTS.md §8 — advisory)

Explainer narrations are advisory-gated: each factual claim must cite an
`ErrorRecord`/`Measurement`/`Experiment` ID or the call refuses. First
live hosted narration (if a key is ever provided) is new-pattern evidence.
