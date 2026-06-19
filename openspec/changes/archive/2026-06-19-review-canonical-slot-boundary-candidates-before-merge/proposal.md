## Why

The archived `materialize-canonical-slot-boundary-candidates` phase produced
standalone, report-local canonical slot-boundary examples. Those examples are
review inputs only: they are not approved formal public sample rows, SFT rows,
DPO pairs, postprocessor behavior, prediction evidence, or model-quality
evidence.

Before any later formal merge, deterministic postprocessor work, or training
retry, this phase reviews the materialized candidates and records which
candidate classes are eligible for a separate bounded formal-merge proposal,
which remain diagnostic/display-only, and which are rejected or deferred as
non-equivalence cases.

## What Changes

- Add review-only evidence under
  `reports/public-sample/canonical-slot-boundary-candidate-review/`.
- Read the standalone candidate materialization report under
  `reports/public-sample/canonical-slot-boundary-candidates/` as the source
  artifact.
- Classify the candidate groups:
  - slot-key alias candidates as eligible for a later bounded formal-merge
    proposal only;
  - conservative slot-value boundary candidates as eligible for a later
    bounded formal-merge proposal only;
  - normalized-command display candidates as diagnostic/display-only;
  - excluded non-equivalence cases as blocked from formal merge unless a later
    policy explicitly changes the boundary.
- Keep `approved_for_formal_merge_now=false` for every candidate class.
- Add focused tests for review artifact presence, source traceability,
  classification boundaries, execution-scope flags, and public leak-scan
  cleanliness.
- Generate a concise Chinese Human Brief HTML for the phase.
- Non-goals: formal public sample mutation, JSONL seed candidate generation,
  SFT/DPO row generation, manifest rebuild, split changes, postprocessor
  implementation, training, prediction reruns, A100 execution, prompt changes,
  evaluator definition changes, strict-exact relaxation, LLM judging,
  semantic-equivalence scoring, prediction repair, checkpoint/adapter release,
  held-out recovery claims, model-improvement claims, production-readiness
  claims, safety-readiness claims, and live-browser benchmark claims.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `slot-canonicalization-policy`: add review-only evidence for canonical
  slot-boundary candidates before any later bounded formal public sample merge
  proposal.

## Impact

- New review artifacts under
  `reports/public-sample/canonical-slot-boundary-candidate-review/`.
- New focused tests under `tests/`.
- Status updates to `CONTEXT.md` / `reports/final_status.md` if the phase
  completes.
- No changes to formal public sample data, generated SFT/DPO artifacts,
  evaluator definitions, model configs, predictions, checkpoints, adapters, or
  A100 workflows.
