## Context

The latest archived phase, `design-slot-canonicalization-policy`, produced
policy artifacts under `reports/public-sample/slot-canonicalization-policy/`
and updated the project status contract. Its evidence says current slot keys
are comparatively stable (`slot_key_f1` dev/test `0.9872` / `0.9769`), while
slot values and `normalized_command` dominate strict residuals
(`slot_value_mismatch=336`, `normalized_command_mismatch=194`). Its
recommended next bounded step is
`materialize-canonical-slot-boundary-candidates`.

This phase should materialize reviewable candidate examples from that policy,
not merge them into the formal public sample. It must preserve strict exact and
layered evaluator semantics.

## Goals / Non-Goals

**Goals:**

- Write standalone public-safe candidate artifacts under
  `reports/public-sample/canonical-slot-boundary-candidates/`.
- Include candidates traceable to the slot key policy, slot value policy,
  normalized-command policy, and model-target boundary.
- Include explicit excluded non-equivalence examples so later phases cannot
  silently normalize them.
- Include machine-readable execution-scope flags proving that formal data,
  SFT/DPO rows, splits, evaluator definitions, predictions, and training remain
  untouched.
- Produce focused tests, leak-scan evidence, status docs, and a Human Brief.

**Non-Goals:**

- No mutation of `data/public-samples/seed_traces.jsonl`,
  `sft_public_sample.jsonl`, `dpo_public_sample.jsonl`, or
  `manifest_public_sample.json`.
- No formal public sample merge, SFT/DPO row generation, train/dev/test split
  change, training, prediction rerun, A100 job, prompt change, evaluator
  definition change, strict-exact relaxation, LLM judge, semantic-equivalence
  scoring, prediction repair, deterministic postprocessor implementation,
  checkpoint/adapter release, model-improvement claim, held-out recovery claim,
  production-readiness claim, safety-readiness claim, or live-browser benchmark
  claim.

## Decisions

1. **Materialize examples as report-local candidates only.**
   The candidates should live under the report directory as standalone JSON/MD
   evidence. They must not enter formal seed traces or derived SFT/DPO files.

2. **Use policy-driven candidate groups.**
   Candidate groups should cover:
   - slot key aliases that are safe to review (`search_text -> query`,
     `site -> url`, `field/value -> field_name/field_value`);
   - conservative slot value formatting boundaries;
   - excluded non-equivalence cases such as date, city, product, URL host, or
     price changes;
   - normalized-command display/diagnostic examples that remain outside strict
     exact and core executable-contract pass changes.

3. **Keep normalized-command display cases separate from slot repair.**
   Examples may show display/template candidates, but must not declare
   equivalence or re-score residuals.

4. **Prefer static materialization over new shared code unless tests require a
   helper.**
   This phase can create deterministic artifacts directly if focused tests
   validate structure and boundaries. Do not introduce a broad generator
   abstraction unless it removes real duplication.

## Risks / Trade-offs

- [Risk] Standalone candidates may be mistaken for approved formal data. ->
  Mitigation: use report-local paths, execution-scope flags, and explicit
  `formal_public_sample_modified=false` fields.
- [Risk] Non-equivalence examples may accidentally be included as accepted
  candidates. -> Mitigation: tests must assert excluded cases are not in
  accepted candidate groups.
- [Risk] `normalized_command` examples may be overread as model improvement. ->
  Mitigation: keep them diagnostic/display-only and outside strict exact.
- [Risk] Existing stale active change `merge-scaled-clarify-slot-boundary-candidates`
  could be conflated with this phase. -> Mitigation: do not modify that change
  or its candidate artifacts.
