## Context

The preceding `materialize-scaled-clarify-slot-boundary-candidates` phase
generated `9` reviewed, public-safe clarify slot-boundary candidate seeds and
`27` SFT candidate rows. Those artifacts are standalone sidecars:

- `data/public-samples/scaled_clarify_slot_boundary_seed_candidates.jsonl`
- `reports/public-sample/scaled-clarify-slot-boundary-candidate-materialization/`

The current formal public sample remains bound to manifest
`public-sample-20260617T152259Z` with `240` seeds, `675` SFT rows, and `2046`
DPO pairs. This phase creates a new formal data boundary by promoting the 9
standalone clarify candidates into the formal public sample and rebuilding the
derived public artifacts.

## Goals / Non-Goals

**Goals:**

- Promote exactly the 9 reviewed scaled clarify slot-boundary candidate seeds
  into the formal public sample.
- Preserve each candidate's reviewed `train`, `dev`, or `test` split label.
- Rebuild synchronized formal public seed, SFT, DPO, and manifest artifacts.
- Publish public-safe merge evidence with pre/post counts, source identity,
  validation status, split counts, and comparison-boundary warnings.
- Update `CONTEXT.md`, `reports/final_status.md`, and a concise Chinese Human
  Brief so project status no longer treats these candidates as standalone-only.

**Non-Goals:**

- SFT, DPO, GRPO, A100 execution, prediction generation, or live-browser
  execution.
- Prompt changes, evaluator metric changes, slot normalization, or prediction
  repair/replacement.
- Checkpoint or adapter publication.
- Model recovery, held-out recovery, safety improvement, production readiness,
  private-corpus generalization, public full-corpus release, or live-browser
  benchmark claims.
- Generic chat fine-tuning, skill routing, or GUI action policy learning.

## Decisions

1. Preserve candidate split labels.

   The standalone candidate file already carries reviewed train/dev/test split
   labels. The formal merge keeps those labels so the new manifest boundary is
   deterministic and does not silently convert held-out-style clarify cases into
   training-only data.

2. Reuse the existing public dataset builder for derived artifacts.

   The merge should append promoted seed rows into the formal seed file, then
   rebuild SFT/DPO/manifest artifacts through the existing public builder. This
   keeps DPO construction, SFT expansion, and public validation aligned with
   existing formal-sample behavior.

3. Treat the merge as a comparison-boundary change.

   The new manifest will include additional clarify rows and therefore cannot be
   directly compared against prior held-out metrics unless a later phase binds
   its prediction/training evidence to the new manifest id.

4. Fail closed on provenance, candidate shape, and claims.

   The merge path must reject missing, duplicate, already-formal, unreviewed,
   non-public-safe, non-standalone, or non-clarify candidate rows before
   rewriting formal public sample artifacts. Report generation must reject true
   scope or claim fields that imply training, prediction, A100 execution, model
   recovery, checkpoint release, adapter release, or metric relaxation.

## Risks / Trade-offs

- [Risk] A formal merge can be mistaken for model improvement.
  -> Mitigation: evidence, manifest, Human Brief, and status docs state that no
  model-quality claim exists until a later strict prediction or training
  evaluation binds to the new manifest.

- [Risk] Split-count changes can make old and new metrics look comparable.
  -> Mitigation: merge evidence records the previous and new manifest ids and
  labels the change as a comparison-boundary update.

- [Risk] Candidate sidecar provenance could be lost during formal promotion.
  -> Mitigation: promoted rows retain source artifact, candidate theme id,
  materialization provenance, and a formal candidate status.

- [Risk] Rebuilding formal DPO artifacts could introduce silent drift.
  -> Mitigation: run public dataset validation, DPO checks, focused tests, full
  tests, OpenSpec strict validation, leak scan, and `git diff --check`.
