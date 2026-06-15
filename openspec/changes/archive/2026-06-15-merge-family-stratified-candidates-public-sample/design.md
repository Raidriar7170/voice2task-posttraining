## Context

The formal public sample currently contains the previously merged slot-value
candidate rows and carries public evidence with 14 seed rows, 42 SFT rows, and
125 DPO pairs. The new family-stratified candidate dataset is independent,
public-safe, and already materialized as 63 seed rows / 189 SFT rows across
seven families.

The user has approved merging this reviewed family-stratified candidate surface
into the formal public sample. The merge changes the public data boundary, so
the phase must be explicit, reproducible, and evidence-backed. It must not be
retold as training, held-out recovery, or evaluator improvement.

## Goals / Non-Goals

**Goals:**

- Merge exactly the reviewed family-stratified candidate seed rows into the
  formal public sample.
- Preserve candidate split labels so train/dev/test become family-stratified in
  the formal sample.
- Rebuild formal SFT, DPO, and manifest artifacts from `seed_traces.jsonl`.
- Preserve existing slot-value candidate metadata in the manifest.
- Record family-stratified source summary, counts, split counts, and claim
  boundaries in public-safe evidence.
- Add tests that fail before implementation and lock the committed artifacts.

**Non-Goals:**

- No SFT/DPO/GRPO training, no A100 prediction, and no live-browser benchmark.
- No evaluator semantic changes, exact-match relaxation, or prediction repair.
- No visual-reference, skill-routing, GUI action policy, generic chat data, or
  private corpus release.
- No model recovery, held-out recovery, checkpoint, adapter, production, or
  private-corpus generalization claim.

## Decisions

1. Preserve split labels from the candidate file.
   - Rationale: the candidate dataset was designed to give every family
     train/dev/test coverage with disjoint slot signatures. Forcing all rows
     into train would destroy that design and blur the next held-out question.
   - Alternative considered: convert all candidate rows to train like the
     slot-value merge. Rejected because this family-stratified phase explicitly
     expands the formal dev/test surfaces too.

2. Validate exact reviewed candidate IDs before merge.
   - Rationale: the public sample should not silently absorb extra or mutated
     candidate rows. The merge function should fail on missing, extra,
     duplicate, or already-merged rows.
   - Alternative considered: merge whatever rows are present. Rejected because
     this repo's public evidence depends on deterministic row counts.

3. Reuse the normal public sample builder after seed merge.
   - Rationale: SFT expansion, DPO hard-negative generation, manifest counts,
     and public validation should stay centralized in existing code paths.
   - Alternative considered: manually concatenate SFT/DPO artifacts. Rejected
     because it risks stale manifests and divergent DPO behavior.

4. Add a merge evidence report separate from the manifest.
   - Rationale: the manifest is an authoritative dataset artifact; the report
     is a human-readable/public-safe explanation of what changed and what was
     not claimed.
   - Alternative considered: rely on the manifest only. Deferred because prior
     phases use evidence packs and Human Briefs to keep claims conservative.

## Risks / Trade-offs

- **Risk:** The merge is mistaken for model-quality progress.
  **Mitigation:** evidence and Human Brief state that no training/prediction
  happened and strict exact match remains the future evaluation metric.
- **Risk:** New dev/test rows make old held-out metrics incomparable.
  **Mitigation:** manifest and report record that the formal public sample data
  boundary changed; later eval must use the new manifest ID.
- **Risk:** Candidate rows are accidentally merged twice.
  **Mitigation:** merge validation rejects duplicate row IDs already present in
  the formal seed file.
- **Risk:** Family metadata disappears during SFT/DPO rebuild.
  **Mitigation:** provenance conversion preserves `family_id`,
  `family_stratification`, and candidate source references.

## Migration Plan

1. Add RED tests for family-stratified candidate merge behavior and committed
   artifact expectations.
2. Implement merge validation, formal provenance conversion, CLI wiring, and
   merge evidence report writing.
3. Run the merge against committed formal public sample files.
4. Generate a Chinese Human Brief from the evidence and validation output.
5. Run focused tests, full tests, leak scan, OpenSpec strict validation, and
   diff hygiene checks.
6. Archive the OpenSpec change after successful validation.

Rollback: revert this commit to restore the previous 14-seed formal sample and
remove the merge evidence. No private or remote artifacts are introduced.

## Open Questions

- Later A100 training/evaluation should be a separate phase keyed to the new
  manifest ID.
- DPO expansion quality should be diagnosed after prediction evidence, not
  assumed from the larger DPO count alone.
