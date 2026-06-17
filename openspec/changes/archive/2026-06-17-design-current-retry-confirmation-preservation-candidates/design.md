## Context

The current authoritative diagnosis is
`reports/public-sample/current-train-split-sft-retry-tradeoff-diagnosis/`,
bound to `public-sample-20260616T165835Z`. It shows that the current
118-row SFT retry recovered dev safety without safety regressions, but created
confirmation regressions:

- dev: `5` confirmation regressions, all in `family-blocked_payment`;
- test: `2` confirmation regressions, both in `family-navigation`;
- dominant trade-off:
  `confirmation_regression_after_safety_recovery`.

The next step is design-only. It should create reviewable candidates that can
later be materialized into train-only public-safe seed rows, but it must not
modify `data/public-samples/`, rebuild the manifest, train, generate
predictions, or change evaluator behavior.

## Goals / Non-Goals

**Goals:**

- Derive candidate families from committed trade-off diagnosis evidence.
- Preserve accepted target shapes for rows where confirmation regressed:
  `blocked/deny` unsafe payment rows that still require confirmation, and
  public-readonly navigation rows that should not require confirmation.
- Record accepted target sketches, rejected drift sketches, source row ids,
  support counts, and suggested public-safe utterance templates.
- Publish JSON/Markdown design evidence, refresh status docs, and generate a
  concise Chinese Human Brief.
- Recommend only a later bounded materialization phase after candidate coverage
  is explicit.

**Non-Goals:**

- No public seed/SFT/DPO/manifest mutation.
- No local/private corpus mutation.
- No SFT, DPO, GRPO, A100 execution, prediction generation, prompt change,
  evaluator change, semantic-equivalence scoring, slot normalization,
  prediction repair, checkpoint release, adapter release, production-readiness
  claim, held-out recovery claim, or live-browser benchmark claim.

## Decisions

1. **Use the trade-off diagnosis as the only source artifact.**
   The design reads committed public-safe diagnosis evidence and the current
   public manifest. It does not inspect private training logs, remote adapter
   internals, or raw private corpora.

2. **Represent candidates as design records, not seed rows.**
   Each candidate should include a stable id, candidate family, source row ids,
   source split/family, accepted target sketch, rejected drift sketches,
   suggested public utterance templates, and intended later action. This keeps
   the design reviewable and prevents accidental public-sample mutation.

3. **Cover both confirmation regression modes.**
   The primary family is unsafe payment confirmation preservation:
   `blocked/deny`, `safety.allow=false`, `safety.reason="unsafe_payment"`,
   and `confirmation_required=true`. The secondary family is public navigation
   non-confirmation preservation: `navigate/open_url`,
   `safety.reason="public_readonly"`, and `confirmation_required=false`.

4. **Keep rejected drift sketches explicit.**
   For unsafe payment rows, rejected sketches should cover
   `confirmation_required=false` blocked output and `form_fill/fill_form`
   allow-drift. For navigation rows, rejected sketches should cover
   `clarify/clarify` drift with `confirmation_required=true` and canonical URL
   drift.

5. **Defer materialization and training.**
   The design may recommend
   `materialize-current-retry-confirmation-preservation-candidates`, but any
   seed row writing, public manifest rebuild, SFT retry, or prediction
   comparison requires a separate OpenSpec change.

## Risks / Trade-offs

- Small support counts can overfit a narrow cluster -> preserve source row ids,
  support counts, and split/family labels in the design report.
- Candidate sketches can be mistaken for committed gold data -> set explicit
  flags such as `formal_public_sample_modified=false`,
  `candidate_seed_rows_materialized=false`, and `training_run=false`.
- Unsafe payment phrasing is safety-sensitive -> keep accepted target sketches
  conservative and do not soften `unsafe_payment` into `requires_confirmation`.
- Navigation confirmation regressions are secondary but real -> include them as
  a smaller candidate family instead of burying them under the payment cluster.
- Design evidence does not prove model improvement -> require later
  materialization plus strict held-out evaluation before any quality claim.
