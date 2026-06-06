# A100 retry generation trace train-split rerun

Status: train-internal A100 diagnostic rerun after local retry generation trace instrumentation. This is not a benchmark, not a release, and no held-out generalization claim is made.

## Result

The rerun produced `3` train predictions from the private A100 adapter path. The prior comparable A100 phase recorded `3` generation trace rows and no retry-attempt trace rows; this rerun recorded `6` generation trace rows including `3` retry-attempt rows.

Observed strict final-contract `json_valid_rate=0.0000` and `contract_exact_match=0.0000`. Raw outputs remain whole JSON objects for `3/3` rows but still omit `task_type`. Retry attempts still include wrapped/prose JSON fragments for `3/3` rows and remain strict-parser failures.

The new evidence is the trace boundary: raw attempts observed EOS for `3/3` rows, while retry attempts had `no_eos_observed` for `3/3` rows. That is useful diagnostic evidence, but the retry stop-boundary claim remains unproven and this is not model recovery.

## Boundary

The evidence pack contains sanitized public-sample contract predictions, aggregate metrics, schema guard summaries, retry trace diagnosis, and leak-scan status. It does not copy raw logs, checkpoints, adapters, remote caches, private configs, host details, tokens, SSH details, or private corpus rows into git.

No training, checkpoint release, adapter release, decoding behavior change, retry prompt change, parser relaxation, evaluator metric change, semantic-equivalence scoring, slot normalization, prediction repair, prediction re-score, production-readiness claim, held-out generalization claim, model-quality claim, public full-corpus release, or live-browser benchmark improvement claim is made.
