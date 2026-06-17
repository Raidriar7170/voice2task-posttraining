## Context

The formal public sample has advanced to `public-sample-20260617T152259Z`
with 240 seed rows and 207-row dev/test splits. The latest observed model
metrics are still bound to the prior `public-sample-20260617T045941Z`
boundary, and the first scaled-manifest baseline attempt stopped before
prediction because the configured A100 SSH alias timed out.

This phase resumes only after the user reported that the A100 development
machine recovered. It must therefore re-check the remote state instead of
assuming the previous blocked evidence is stale or treating connectivity
recovery as model-quality evidence.

## Goals / Non-Goals

**Goals:**

- Produce a fresh A100 preflight record for the scaled-manifest prediction
  retry.
- If safe, run prediction-only exports for dev and test rows using the
  existing private `a100-current-train-split-sft-retry` adapter.
- Evaluate predictions with the existing strict contract ladder.
- Commit only sanitized evidence, status docs, tests, and Human Brief content.
- Preserve an explicit comparison boundary between the source adapter manifest
  and the target scaled manifest.

**Non-Goals:**

- No SFT, DPO, GRPO, curriculum, or hyperparameter retry.
- No data mutation, prompt change, decoder change, evaluator relaxation,
  semantic equivalence scoring, slot normalization, prediction repair, or
  prediction replacement.
- No public release of adapters, checkpoints, private corpora, raw logs, host
  details, SSH details, caches, or private override configs.
- No production-readiness, live-browser benchmark, safety-readiness, or model
  recovery claim.

## Decisions

1. **Create a new retry evidence directory instead of overwriting the blocked
   baseline.**
   This preserves the original fail-closed timeout evidence and makes the A100
   recovery retry auditable.

2. **Run private prediction from a resolved remote-only override.**
   The committed configs remain placeholder-based and public-safe. Any resolved
   approved private A100 workspace paths stay on the A100 development machine
   and are not copied into git.

3. **Treat the result as a baseline on a new manifest, not a direct improvement
   claim.**
   The source adapter was trained on `public-sample-20260617T045941Z`, while
   the target prediction boundary is `public-sample-20260617T152259Z`, so the
   report must mark direct improvement/regression comparison as invalid.

4. **Fail closed if any remote prerequisite is unsafe.**
   If GPU placement, adapter path, remote project path, environment, or command
   execution cannot be verified safely, the phase writes refreshed blocked
   evidence and does not fabricate predictions or metrics.

## Risks / Trade-offs

- **A100 is reachable but no GPU is safely idle** -> Record blocked evidence
  with no prediction run.
- **Remote code or data is stale** -> Sync or verify only tracked project
  inputs under the approved remote root before prediction; do not patch remote
  code ad hoc without reflecting committed local source.
- **Prediction succeeds but metrics regress** -> Report strict metrics as a new
  scaled-manifest baseline; do not reinterpret regression as training failure
  recovery or success.
- **Sanitization misses private details** -> Run leak scans over evidence,
  Human Brief, and status docs before archive and integration.
