## Context

The prior A100 search-query slot-policy rerun and wrapper-boundary diagnosis narrowed the current failure: compact search-query content can appear in decoded fragments, but predictions remain Markdown-wrapped and strict whole-string schema parsing still rejects them. Existing retry prompts already contain stronger machine-only retry boundary language, while the first-pass prediction system prompt carries weaker and less instrumented output-boundary metadata.

This phase is a user-confirmed behavior change, but it remains local and bounded. It prepares the first-pass prediction path for a later A100 prediction-only rerun without changing parser acceptance, evaluator metrics, or historical evidence.

## Goals / Non-Goals

**Goals:**

- Make first-pass prediction prompts explicitly require exactly one machine-readable Browser Task Contract JSON object.
- Expose first-pass output-boundary visibility as machine-readable prompt metadata.
- Add focused tests proving the boundary is visible and wrapped JSON remains invalid under strict parsing.
- Publish public-safe local evidence and a Human Brief that separate local behavior change from model-quality claims.

**Non-Goals:**

- No A100 execution, training, adapter/checkpoint release, deployment, or private corpus publication.
- No parser relaxation, JSON-fragment extraction, prediction repair, output coercion, evaluator metric change, re-score, semantic-equivalence scoring, or slot normalization.
- No claim of model recovery, held-out generalization, production readiness, public full-corpus readiness, or live-browser benchmark improvement.

## Decisions

1. Harden first-pass prompt policy instead of parser behavior.

   The failure is observed as model output wrapping, not as an evaluator inability to locate embedded JSON. Relaxing the parser would make invalid machine-output boundaries look successful, so this phase keeps `_extract_strict_json_object` whole-string only.

2. Add first-pass boundary metadata instead of reusing retry-only metadata.

   Retry metadata proves the retry prompt contains machine-only clauses, but the latest failure appears in both raw and retry decoded attempts. First-pass prediction needs its own summary so future prompt snapshots and metadata can prove which boundary was visible before generation.

3. Keep evidence local before any new A100 rerun.

   The change can be validated with prompt rendering, metadata, strict parser tests, leak scans, and public-safe evidence. A later A100 rerun can then test whether model behavior changed, but this phase does not itself provide model-output recovery evidence.

## Risks / Trade-offs

- [Risk] More prompt text can consume sequence budget. → Keep clauses concise and preserve the existing public-sample sequence budget test.
- [Risk] Prompt hardening may still not change trained-adapter behavior. → Evidence and Human Brief must state that only a later real rerun can test adapter behavior.
- [Risk] Metadata could be misread as a successful output fix. → Evidence must include explicit non-claims and current prior strict metrics.
- [Risk] Boundary phrases may duplicate retry clauses. → Share the conceptual policy, but keep first-pass and retry summaries separate so failures can be attributed cleanly.
