## Why

The false-trust diagnosis showed that source attestation is source-only evidence, not semantic correctness, and that the current per-scope recommendation surface still depended on hard-coded scope names and fixture-guided taxonomy shortcuts. Before any Policy V2 review, the scope decision process needs a deterministic, auditable design that treats small samples, adapter imbalance, high-risk semantic mismatches, and downward-only semantic review explicitly.

## What Changes

- Add a bounded Policy V2 scope design engine that computes post-hardening metrics from committed challenge/diagnosis artifacts.
- Split `CHALLENGE_FIXTURE_OR_GOLD_AMBIGUITY` into `TRUE_GOLD_OR_FIXTURE_AMBIGUITY` and `CANONICAL_STRING_MISMATCH` in the current diagnosis interpretation layer.
- Mark mismatch attribution as `fixture_guided` with explicit attribution source and deterministic checks per case.
- Define reproducible gate rules for `OBSERVE_ENABLED`, `OBSERVE_LIMITED`, `CANDIDATE_ONLY`, `PROPOSE_DISABLE`, and `INSUFFICIENT_EVIDENCE`.
- Emit a proposed, inactive `configs/copy-backed-scope-policy-v2.proposed.json` and compact public-safe design reports for review.
- Keep `configs/copy-backed-scope-policy-v1.json`, challenge v1, gold, predictions, sidecars, evaluator, prompt, decoding, runtime hook, model weights, and training data unchanged.

## Capabilities

### New Capabilities
- `copy-shadow-scope-policy-v2-design`: deterministic, review-only design surface for proposed copy-shadow scope policy v2 decisions.

### Modified Capabilities

None.

## Impact

- Adds a small design/report module, report script, tests, proposed inactive policy JSON, docs, OpenSpec artifacts, and a concise Human Brief.
- Does not add runtime loading of Policy V2 and does not change prediction or evaluation behavior.
- Does not claim slot accuracy, executable quality, policy generalization, production readiness, or safety readiness.
