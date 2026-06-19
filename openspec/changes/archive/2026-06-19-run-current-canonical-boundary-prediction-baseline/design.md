## Context

The current formal public sample manifest is
`public-sample-20260619T090925Z` after the canonical slot-boundary formal merge.
The latest observed model evidence is still the A100 scaled-manifest retry under
`reports/public-sample/a100-scaled-public-sample-current-123-adapter-prediction-baseline-after-a100-recovery/`,
which targets `public-sample-20260617T152259Z`. That evidence remains useful as
history, but it is no longer the clean current-boundary baseline.

The repository already has a strict formal held-out prediction report writer,
dev/test prediction config templates, public-safe leak scanning, and precedent
for observed-or-blocked A100 prediction evidence. This phase should reuse those
paths and only change the target boundary and evidence location.

## Goals / Non-Goals

**Goals:**

- Produce current-boundary prediction-only evidence for dev/test rows of
  `public-sample-20260619T090925Z`, or fail closed with blocked evidence.
- Keep strict `contract_exact_match` and strict `slot_f1` authoritative while
  labeling `slot_f1_soft` diagnostic-only.
- Record source adapter/runtime lineage separately from the target manifest
  boundary.
- Commit only sanitized predictions, metrics, reports, manifests, preflight
  summaries, leak scans, status docs, and a Human Brief.

**Non-Goals:**

- No SFT, DPO, GRPO, broad data generation, prompt changes, evaluator changes,
  postprocessor implementation, slot normalization, prediction repair,
  checkpoint or adapter release, public full-corpus release, production
  readiness, or live-browser benchmark claim.
- No direct comparison to older metrics as improvement or regression unless the
  comparison boundary explicitly allows it.

## Decisions

1. Reuse the formal public held-out report shape.
   - Rationale: `write_formal_public_heldout_prediction_report` already records
     observed/blocked status, strict metrics, claim boundaries, and
     public-safe artifact paths.
   - Alternative considered: create a new bespoke report kind. Rejected because
     it would duplicate metric semantics and raise comparison-boundary risk.

2. Use an observed-or-blocked execution policy.
   - Rationale: A100 access, idle GPU placement, remote dependencies, and the
     private adapter are external prerequisites. If any cannot be verified
     safely, the public repo should record blocked evidence rather than
     fabricated metrics.
   - Alternative considered: skip the phase when remote execution fails.
     Rejected because a fail-closed artifact is useful durable evidence.

3. Keep source adapter lineage distinct from target manifest.
   - Rationale: the existing private adapter was trained on an older train
     boundary. The report must make clear whether this is a current-target
     prediction baseline, not current-boundary training evidence.
   - Alternative considered: treat it as a current manifest model result without
     source lineage. Rejected because it would overstate the result.

4. Keep all private runtime details outside committed artifacts.
   - Rationale: public evidence may include sanitized metrics and prediction
     rows, but must omit host details, SSH details, private paths, raw logs,
     private overrides, checkpoints, adapters, caches, tokens, and private
     corpus rows.

## Risks / Trade-offs

- A100 prerequisites unavailable -> publish blocked evidence with no fabricated
  prediction rows or metrics.
- Existing adapter may underperform on the new boundary -> report strict metrics
  as observed evidence without recovery or quality claims.
- New manifest target may invite invalid old/new comparisons -> make
  `comparison_boundary.changed=true` and direct improvement/regression
  comparison invalid.
- Sanitized prediction evidence may still contain sensitive strings if upstream
  commands are not scanned -> run leak scan over configs, committed reports,
  Human Brief, and OpenSpec artifacts before archive.
