## Context

`design-and-evaluate-contract-v2-projection` stopped with
`PROJECTION_BLOCKED_OR_INVALID` because the current step-matched ablation report
root includes aggregate metrics and row summaries but not raw prediction/gold
contracts. The next phase must recover the exact row-level inputs that would
make the projection rerun evidence-bearing.

The current source of truth is the committed
`reports/public-sample/step-matched-canonical-slot-ablation/` report root plus
the corresponding step-matched train/prediction configs, manifests, split
artifacts, evaluator code, and run metadata. `CONTEXT.md` is useful background
but must not be the only source of truth.

## Goals / Non-Goals

**Goals:**

- Discover original step-matched raw Control/Treatment dev/test predictions and
  dev/test gold contracts locally or under approved A100 run roots.
- Verify run IDs, config hashes, manifest IDs, sample IDs, gold hashes, prompt
  hashes, evaluator hashes, and adapter identities.
- Sanitize and write row-level artifacts to
  `reports/public-sample/step-matched-canonical-slot-ablation/raw-inputs/`.
- Recompute required aggregate metrics using the committed evaluator and compare
  with `control/dev-metrics.json`, `control/test-metrics.json`,
  `treatment/dev-metrics.json`, and `treatment/test-metrics.json`.
- Emit one of the approved decision labels and set
  `projection_inputs_ready=true` only for recovered artifacts whose
  metrics reproduce.

**Non-Goals:**

- No SFT, DPO, GRPO, retraining, continued training, adapter rebuild, model
  change, LoRA change, prompt change, decoding change, evaluator change,
  normalization change, gold change, split change, prediction repair, LLM
  judge, semantic-equivalence scoring, data merge/expansion, Contract V2
  implementation, or Contract V2 projection execution.
- No adapter/checkpoint release, production readiness, safety readiness,
  live-browser benchmark, model improvement, or held-out recovery claim.

## Decisions

### Decision 1: Use a strict recovery decision tree

The phase follows three paths:

1. Original artifacts found and verified:
   `RECOVERED_FROM_EXISTING_ARTIFACTS`.
2. Otherwise fail closed with one of the invalid/blocking labels.

Rationale: aggregate metrics and row summaries cannot substitute for raw
prediction contracts. Prediction-only reproduction is outside this applied
recovery phase and would require a separate bounded proposal.

### Decision 2: Validate metrics before declaring readiness

Recovered artifacts are not projection-ready until the committed
aggregate metrics reproduce within `1e-9` absolute tolerance, unless a source
artifact provides exact numerator/denominator rounding evidence.

Rationale: row-level artifacts must be proven to correspond to the committed
step-matched experiment, not merely look plausible.

### Decision 3: Keep public artifacts sanitized and path-free

The committed `artifact-manifest.json` records hashes, run labels, manifest IDs,
and validation results, but not absolute local paths, remote paths, SSH aliases,
IPs, hostnames, tokens, private adapter paths, checkpoint contents, or raw
private logs.

Rationale: the project can preserve auditability without exposing private A100
or local runtime details.

### Decision 4: Add retention only as a narrow guardrail

If existing prediction/eval code does not retain row-level predictions, gold,
manifest, config hash, prompt hash, evaluator hash, and reproduction metadata,
add the smallest reusable retention helper and tests.

Rationale: preventing this exact blocker from recurring is in scope; turning
the codebase into a generic experiment platform is not.

## Risks / Trade-offs

- Original raw outputs may be absent and fresh adapter identity may not be
  verifiable -> write `RECOVERY_BLOCKED_ADAPTER_UNAVAILABLE` and stop.
- Recovered artifacts may differ from committed aggregate metrics -> write
  `RECOVERY_INVALID_METRIC_MISMATCH` and stop without altering old metrics.
- Public-safe row-level artifacts may require sanitizing input text or raw model
  outputs -> keep hashes and sanitized text rather than private content.
- A100 inspection is read-only for this applied phase; do not run prediction
  reproduction inside this change.

## Migration Plan

This phase has no runtime migration. It adds recovery artifacts and optional
retention helpers/tests. Rollback is removing the recovery report directory,
OpenSpec change, docs updates, and any narrow helper/test added by the phase.

## Open Questions

- Whether original raw outputs still exist under the approved A100 project root.
  If not, this applied recovery phase must block rather than run prediction.
