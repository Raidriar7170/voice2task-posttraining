## Context

The archived `materialize-canonical-slot-boundary-candidates` phase created
public-safe standalone examples under
`reports/public-sample/canonical-slot-boundary-candidates/`. Its accepted
groups cover slot-key aliases, conservative slot-value boundaries, and
normalized-command display diagnostics. It also records explicit
non-equivalence exclusions for date, city/location, product, URL host,
price/amount, query/product, location/destination, and action/reason changes.

The materialization phase intentionally stopped before formal data mutation.
This review phase should decide whether candidate classes are ready to become
inputs to a separate bounded formal-merge proposal. It must not perform the
merge itself.

## Goals / Non-Goals

**Goals:**

- Write review-only artifacts under
  `reports/public-sample/canonical-slot-boundary-candidate-review/`.
- Preserve source traceability to
  `reports/public-sample/canonical-slot-boundary-candidates/summary.json`.
- Classify each materialized candidate group into one of:
  `eligible_for_later_formal_merge_proposal`, `diagnostic_display_only`, or
  `blocked_or_deferred_non_equivalence`.
- Keep all classes unapproved for immediate formal merge.
- Record machine-readable execution-scope flags proving formal public sample
  data, SFT/DPO artifacts, manifests, splits, evaluator definitions,
  predictions, and training remain untouched.
- Produce focused tests, leak-scan evidence, status docs, and a Human Brief.

**Non-Goals:**

- No mutation of `data/public-samples/seed_traces.jsonl`,
  `sft_public_sample.jsonl`, `dpo_public_sample.jsonl`, or
  `manifest_public_sample.json`.
- No JSONL candidate seed generation, SFT/DPO row generation, train/dev/test
  split change, formal public sample merge, training, prediction rerun, A100
  job, prompt change, evaluator definition change, strict-exact relaxation,
  LLM judge, semantic-equivalence scoring, prediction repair, deterministic
  postprocessor implementation, checkpoint/adapter release, model-improvement
  claim, held-out recovery claim, production-readiness claim,
  safety-readiness claim, or live-browser benchmark claim.

## Decisions

1. **Review classes, not individual private rows.**
   The source artifacts are already public-safe sketches. This phase should
   classify candidate classes and representative candidate ids without
   reaching into private rows or raw logs.

2. **Allow only proposal eligibility, not immediate merge approval.**
   Slot-key aliases and conservative slot-value boundaries may be marked
   eligible for a later bounded formal-merge proposal, but every review record
   must keep `approved_for_formal_merge_now=false` and
   `requires_separate_openspec_change=true`.

3. **Keep normalized-command outside merge eligibility.**
   Normalized-command examples remain diagnostic/display-only. They must not
   declare equivalence, alter strict exact or executable-contract metrics, or
   repair prior predictions.

4. **Keep explicit non-equivalence exclusions blocked.**
   Excluded cases remain blocked or deferred. Any future change that wants to
   revisit them must own a separate policy boundary; this review does not
   loosen the slot-value policy.

5. **Prefer static review evidence over a broad generator.**
   A deterministic JSON/MD review artifact with focused tests is enough for
   this phase. Avoid adding shared generation code unless tests reveal real
   duplication or drift risk.

## Risks / Trade-offs

- [Risk] Review evidence may be misread as data approval. -> Mitigation:
  every class records `approved_for_formal_merge_now=false`, and the
  recommended next step is a separate bounded proposal.
- [Risk] Normalized-command display templates may be overread as strict metric
  repair. -> Mitigation: classify them as `diagnostic_display_only`.
- [Risk] Non-equivalence exclusions may get reintroduced as accepted data. ->
  Mitigation: tests assert excluded cases remain blocked from merge.
- [Risk] Existing stale active
  `merge-scaled-clarify-slot-boundary-candidates` could be conflated with this
  phase. -> Mitigation: do not modify that change or its artifacts.
