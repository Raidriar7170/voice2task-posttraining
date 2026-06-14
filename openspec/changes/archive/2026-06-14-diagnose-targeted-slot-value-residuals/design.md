## Context

The archived `run-targeted-family-coverage-probe` phase shows:

- train: `contract_exact_match=1.0`
- dev: `contract_exact_match=1/6`
- test: `contract_exact_match=1/6`
- dev/test: JSON validity, schema validity, task type, route, safety, and confirmation are all correct.

The residuals are value mismatches:

- dev open-url rows: `normalized_command` paraphrases differ from strict gold.
- dev clarify rows: `slots.ambiguity` phrases differ from strict gold.
- test form rows: `slots.field` uses `email` instead of `邮箱`.
- test blocked-purchase rows: `normalized_command` paraphrases differ from strict gold.

## Approach

1. Add a diagnosis function that reads split gold rows, predictions, alignment diagnostics, and the targeted probe manifest.
2. For each mismatching row, record:
   - split
   - row id
   - source family
   - field path
   - gold/predicted value summaries
   - drift bucket
   - whether schema/task/route/safety/confirmation were already correct at split level
3. Aggregate by split, field, source family, and drift bucket.
4. Write public-safe JSON/Markdown artifacts plus a manifest that records bounded claims.
5. Generate a Human Brief that answers the user-facing question: this is now a slot value/generalization diagnosis, not a reason to immediately run broad scaling or DPO.

## Taxonomy

- `normalized_command_paraphrase_drift`: strict command phrase mismatch with otherwise correct contract structure.
- `slot_value_language_variant`: same slot key but value switches language or representation, for example `邮箱` vs `email`.
- `slot_value_canonical_phrase_drift`: same slot key but canonical explanatory phrase differs, for example clarify ambiguity wording.
- `other_value_drift`: fallback for mismatches that do not match the known public residual buckets.

## Boundaries

- The diagnosis must not rewrite predictions.
- The diagnosis must not alter metrics or promote soft slot F1 to primary.
- The diagnosis must not claim held-out recovery.
- The diagnosis must not include private paths, host details, SSH details, raw logs, adapters, checkpoints, caches, or private corpus rows.

## Risks

- **Risk:** The taxonomy may overfit the small public sample.
  **Mitigation:** Label it as public-sample residual evidence only and keep recommendations narrow.
- **Risk:** The report could make slot soft match look like success.
  **Mitigation:** Explicitly keep strict `contract_exact_match` as primary and use soft slot F1 only as diagnostic context.
