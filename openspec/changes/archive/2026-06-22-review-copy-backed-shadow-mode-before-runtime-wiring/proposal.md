# review-copy-backed-shadow-mode-before-runtime-wiring

## Why
The previous `integrate-copy-backed-slot-verification-shadow-mode` phase attached deterministic sidecars to 828/828 current prediction contracts, but those sidecars still mixed online provenance diagnostics with offline gold correctness audit fields. Before any prediction-pipeline shadow hook is proposed, the project needs a bounded review-and-hardening phase that freezes the copy-backed scope policy, proves the online sidecar can be generated without gold, tightens trusted provenance semantics to exact unique source spans only, and regenerates public-safe evidence with explicit denominators.

## What Changes
- Freeze `copy-backed-scope-policy-v1` for exactly three enabled task-scoped triples:
  - `search:search_web:query`
  - `form_fill:fill_form:field`
  - `extract:extract_page:target`
- Split the shadow interface into:
  - an `OnlineShadowSidecar` surface that depends only on input text, prediction contract, frozen policy, verifier output, request/sample identifiers, and hashes;
  - an offline `EvaluationAudit` surface that joins online sidecars with gold/evaluator evidence.
- Make `VERIFIED_EXACT_UNIQUE` the only trusted provenance status. `VERIFIED_NORMALIZED_UNIQUE` remains candidate-only and never trusted.
- Require full span validation before trusted provenance: policy enabled, exact status/match kind, one candidate span, valid offsets/hash, matching current input hash, and exact back-slice equality.
- Regenerate review evidence under `reports/public-sample/copy-backed-shadow-mode-review/` with corrected metric names, denominators, per-scope breakdowns, deterministic rerun hashes, leak scan status, and a local CPU latency microbenchmark.
- Publish `docs/copy-backed-shadow-interface.md`, update the repo truth surface, and generate a concise Chinese Human Brief.

## Out Of Scope
- Online prediction-pipeline hook, runtime wiring, runtime enforcement, action enablement, evaluator changes, model/prediction/data/training changes, A100/SSH/GPU work, new split generation, semantic aliasing, LLM judging, URL resolution, prediction repair, or automatic next-stage implementation.

## Success Criteria
- Online sidecars are generated for 828/828 prediction contracts without any gold fields and without any gold parameter in the generation function.
- Offline audits align to the sidecars and are the only surface containing gold correctness fields.
- Policy hash and enabled triples are stable; action remains disabled; normalized provenance is candidate-only.
- `provenance_false_accept_count`, `silent_fallback_count`, `contract_mutation_count`, `runtime_decision_delta_count`, and V1 evaluator metric deltas are all 0.
- Deterministic sidecar/audit replay hash match rate is 1.0.
- Per-scope metrics and latency microbenchmark are present.
- Final decision label is one of the bounded review labels, with exactly one next change and no runtime/enforcement claim.
