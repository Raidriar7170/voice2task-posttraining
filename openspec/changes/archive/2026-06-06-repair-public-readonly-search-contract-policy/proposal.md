## Why

The archived A100 normalized-command rerun row diagnosis shows the remaining train-row failures are no longer just normalized-command strings: one row omits `confirmation_required`, one row emits invalid `task_type="search_web"`, and one schema-valid row maps a public weather/search request to `task_type="form_fill"`, `route="open_url"`, `safety.reason="form_fill"`, and a collapsed `slots.query`. The next bounded local step should make the public-readonly search/weather contract policy explicit in model-visible prompts and public evidence before any new private A100 rerun.

## What Changes

- Strengthen shared SFT training and prediction prompts with a compact public-readonly search contract policy:
  - weather/public information lookup uses `task_type="search"` and `route="search_web"`;
  - low-risk public-readonly lookup uses `safety.allow=true`, `safety.reason="public_readonly"`, and `confirmation_required=false`;
  - search slots should stay object-shaped and use `slots.query` for the concise query text;
  - `task_type` must stay an allowed task enum and must not reuse route enum values such as `search_web`.
- Add focused tests for the prompt text and `prompt_constraint_summary()` flags without inserting row-specific gold target contracts into prediction prompts.
- Publish a local public-safe evidence pack describing the policy hardening and the source row-mismatch evidence.
- Generate a concise Chinese Human Brief.
- Do not run A100, training, prediction rerun, decoder repair, schema repair, evaluator metric changes, semantic-equivalence scoring, prediction repair, prediction re-score, checkpoint release, or adapter release.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `supervised-contract-tuning`: require the shared training and prediction prompt surface to make public-readonly search/weather contract fields explicit without adding row-specific gold contracts.
- `contract-evaluation`: require public-safe local evidence for this prompt/policy hardening phase with strict non-claim boundaries.

## Impact

- Affected code: SFT/prediction prompt formatting and prompt constraint metadata.
- Affected tests: focused prompt-formatting tests and local evidence-pack tests.
- Affected artifacts: `reports/public-sample/public-readonly-search-contract-policy/` and `docs/human-briefs/2026-06-06-repair-public-readonly-search-contract-policy.html`.
- Non-goals: no generic chat fine-tuning, no skill routing, no GUI action policy learning, no first-phase GRPO, no public release of the full local corpus, no private A100 execution, no model-quality or held-out generalization claim, no production-readiness claim, and no live-browser benchmark improvement claim.
