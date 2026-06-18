## Why

The archived `design-slot-canonicalization-policy` phase concluded that slot
keys are comparatively stable while slot values and `normalized_command`
dominate strict residuals. The next bounded step is to turn that policy into
reviewable, public-safe standalone candidate examples before any formal public
sample merge, deterministic postprocessor work, or training retry.

## What Changes

- Add standalone candidate materialization evidence under
  `reports/public-sample/canonical-slot-boundary-candidates/`.
- Read the archived slot canonicalization policy artifacts as the source of
  truth for aliases, non-equivalence cases, value boundaries,
  `normalized_command` positioning, and model/postprocessor boundaries.
- Generate public-safe candidate examples for canonical slot key aliases,
  conservative slot value boundaries, non-equivalence exclusions, and
  normalized-command display/diagnostic cases.
- Keep candidates standalone and reviewable; do not mutate
  `data/public-samples/seed_traces.jsonl`, formal SFT/DPO artifacts, manifests,
  or train/dev/test splits.
- Add focused tests for source traceability, candidate schema, non-equivalence
  exclusion, design-only/materialization-only boundaries, required artifacts,
  and public leak-scan cleanliness.
- Generate a Chinese Human Brief HTML for the phase.
- Non-goals: generic chat fine-tuning, skill routing, GUI action policy
  learning, first-phase GRPO, public release of the full local corpus, formal
  public sample merge, SFT/DPO row generation, split changes, training,
  prediction reruns, A100 execution, deterministic postprocessor
  implementation, evaluator relaxation, LLM judging, semantic-equivalence
  scoring, prediction repair, checkpoint/adapter release, held-out recovery
  claims, production-readiness claims, safety-readiness claims, and
  live-browser benchmark claims.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `slot-canonicalization-policy`: add standalone public-safe canonical
  slot-boundary candidate materialization evidence from the archived policy
  before later formal data merge, postprocessor, or training phases.

## Impact

- New standalone report and candidate artifacts under
  `reports/public-sample/canonical-slot-boundary-candidates/`.
- New or updated tests under `tests/`.
- Status updates to `CONTEXT.md` / `reports/final_status.md` only if the phase
  completes.
- No changes to formal public sample data, generated SFT/DPO artifacts,
  evaluator definitions, model configs, predictions, checkpoints, adapters, or
  A100 workflows.
