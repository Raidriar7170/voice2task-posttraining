## Context

The residual diagnosis found:

- `slot_value_language_variant`: 3 rows, `slots.field="email"` instead of `邮箱`.
- `slot_value_canonical_phrase_drift`: 3 rows, clarify ambiguity phrase drift.
- `normalized_command_paraphrase_drift`: 4 rows, open-url and blocked-payment command wording drift.

The public sample already has train analogs for the same contract families, but the analogs do not force the exact held-out canonical values:

- form train analog uses `昵称`, while test residual needs `邮箱`.
- clarify train analog uses `目标不明确，未指定具体页面`, while dev residual needs `目标不明确，未指定具体网站或页面`.
- blocked train analog uses transfer wording, while test residual needs payment wording.
- navigate train analog uses help-center wording, while dev residual needs open-site wording.

## Approach

1. Read the residual diagnosis as the source of truth.
2. Derive one candidate case group per residual bucket and source family.
3. For each group, record:
   - target residual bucket
   - source family
   - affected field paths
   - canonical gold value to preserve
   - observed wrong value pattern
   - proposed case purpose
   - recommended split role, initially `candidate_train_or_validation_design_only`
   - whether user approval is required before materializing rows
4. Write JSON, Markdown, and manifest artifacts.

## Design Boundaries

- The artifact is a case design, not a dataset mutation.
- Candidate cases must not be treated as actual train/dev/test rows until a later OpenSpec change explicitly materializes them.
- The design must preserve strict `contract_exact_match` as primary and must not add evaluator-side normalization.
- The design must recommend a later bounded materialization step rather than broad scaling or DPO.

## Case Buckets

1. `slot_value_language_variant`
   - Purpose: teach Chinese canonical field values such as `邮箱` rather than English aliases like `email`.
2. `slot_value_canonical_phrase_drift`
   - Purpose: teach stable clarify ambiguity phrases, especially scope phrases that mention both website and page.
3. `normalized_command_paraphrase_drift`
   - Purpose: teach concise canonical command wording rather than acceptable-but-strict-wrong paraphrases.

## Risks

- **Risk:** Candidate cases are mistaken for training evidence.
  **Mitigation:** Mark all generated artifacts as `design_only`, with `new_data_generated=false`.
- **Risk:** The design leaks held-out answers into train without review.
  **Mitigation:** Stop before materialization; require the later change to explicitly choose split policy.
- **Risk:** The design encourages evaluator relaxation.
  **Mitigation:** Keep exact-match and non-repair boundaries in manifest, report, and tests.
