# A100 schema retry wrapper-boundary train-split rerun

Status: train-internal A100 diagnostic rerun after local retry wrapper-boundary prompt hardening. This is not a benchmark, not a release, and no held-out generalization claim is made.

## Result

The rerun produced `3` train predictions from the private A100 adapter path. Prediction metadata and prompt snapshot include the new retry prompt constraints, including no-prefix/no-suffix, no `Here is`, no trailing analysis, no second JSON object, and strict-parser rejection warning.

Observed strict final-contract `json_valid_rate=0.0000` and `contract_exact_match=0.0000`. Raw outputs remain whole JSON objects for `3/3` rows, but all three still omit `task_type`. Retry attempts still visibly include `task_type=search` and remain prose/Markdown-wrapped for `3/3` rows, so the strict parser rejects every retry.

## Boundary

The evidence pack contains sanitized public-sample contract predictions, aggregate metrics, schema guard summaries, row-level retry-wrapper diagnosis, and leak-scan status. It does not copy raw logs, checkpoints, adapters, remote caches, private configs, host details, tokens, SSH details, or private corpus rows into git.

No parser relaxation, semantic-equivalence scoring, slot normalization, evaluator metric relaxation, prediction repair, re-score, training, checkpoint release, adapter release, production-readiness claim, held-out generalization claim, model-quality claim, or live-browser benchmark improvement claim is made.
