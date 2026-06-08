# First-pass Markdown Fence Suppression

This is local generation-time behavior change only: first-pass and retry generation now pass tokenizer-derived Markdown fence token sequences as `bad_words_ids` when those sequences are available.

## What Changed

- Added `markdown_fence_suppression_enabled=true` to prediction decoding policy metadata.
- Added `markdown_fence_suppression_strategy=bad_words_ids`.
- Derived token sequences from the active tokenizer for ```` ``` ```` , ```` ```json ```` , and ```` ```JSON ```` rather than hardcoding tokenizer ids.
- Passed suppression sequences to real trained-adapter generation when non-empty sequences are available.
- Propagated the same decoding policy into prompt snapshots and prediction metadata.

## Strict Boundary

- Wrapped JSON fragments still remain invalid under strict parsing.
- No embedded JSON extraction, fence stripping, prediction repair, output coercion, evaluator metric change, re-score, semantic-equivalence scoring, or slot normalization was performed.
- This phase does not rewrite or reinterpret prior A100 predictions.

## Prior A100 Context

- Prior first-pass boundary rerun: `reports/public-sample/a100-first-pass-output-boundary-rerun/`.
- Prior wrapper-persistence diagnosis: `reports/public-sample/a100-first-pass-wrapper-persistence-diagnosis/`.
- Prior strict schema-valid output: `0/3`.
- Prior strict exact match: `0.0`.
- Prior Markdown-wrapped predictions: `3/3`.

## Validation Snapshot

- RED: `PYTHONPATH=src pytest -q tests/test_a100_sft_prediction_smoke.py::test_sft_prediction_metadata_uses_configured_max_new_tokens tests/test_a100_sft_prediction_smoke.py::test_real_sft_prediction_generate_suppresses_markdown_fence_tokens` -> `2 failed before implementation`.
- GREEN: `PYTHONPATH=src pytest -q tests/test_a100_sft_prediction_smoke.py::test_sft_prediction_metadata_uses_configured_max_new_tokens tests/test_a100_sft_prediction_smoke.py::test_real_sft_prediction_generate_suppresses_markdown_fence_tokens tests/test_a100_sft_prediction_smoke.py::test_real_sft_prediction_generate_suppresses_markdown_fence_tokens_on_retry tests/test_a100_sft_prediction_smoke.py::test_sft_prediction_fixture_mode_writes_sidecars_and_metadata_links tests/test_a100_sft_prediction_smoke.py::test_real_sft_prediction_rejects_markdown_wrapped_raw_attempt_even_when_fragment_is_valid tests/test_a100_sft_prediction_smoke.py::test_real_sft_prediction_rejects_markdown_wrapped_retry_even_when_fragment_is_valid` -> `6 passed after implementation and reviewer coverage fix`.

## Non-Claims

This local phase does not prove trained-adapter output behavior changed. It does not claim A100 execution, training, checkpoint release, adapter release, model recovery, model-quality improvement, held-out generalization, production readiness, public full-corpus release, or live-browser benchmark improvement.

## Recommended Next Step

After local validation and archive, run a bounded A100 prediction-only train-split rerun using this decoding policy to observe whether Markdown fences decrease without changing strict parser or evaluator semantics.
