# Generation stop-reason boundary instrumentation

Conclusion: this local phase adds public-safe stop-boundary evidence fields to future `generation_trace.jsonl` rows. It keeps prediction behavior unchanged and records that the actual stop reason remains unrecorded by the current code.

## What changed

- `generation_trace.jsonl` keeps its existing fields.
- New fields are added: `max_new_tokens_hit`, `finish_state_basis`, `stop_reason_evidence`, `actual_stop_reason_recorded`, and `actual_stop_reason`.
- `finish_state` remains backward compatible; the new `finish_state_basis` field states whether it came from tokenizer EOS membership or fixture status.
- `max_new_tokens_hit` is recorded as a boundary signal, not as a full stop-reason capture.

## TDD evidence

- RED observed: focused tests failed because trace rows did not include `max_new_tokens_hit`.
- GREEN observed: the direct trace-row test, raw sidecar test, retry sidecar test, and evidence-pack test passed after the minimal instrumentation change.

## Validation

- `PYTHONPATH=src pytest -q tests/test_a100_sft_prediction_smoke.py::test_generation_trace_row_records_stop_boundary_evidence_without_actual_stop_reason tests/test_a100_sft_prediction_smoke.py::test_real_sft_prediction_sidecars_summarize_sanitized_decoded_and_generation_trace tests/test_a100_sft_prediction_smoke.py::test_real_sft_prediction_generation_trace_records_retry_attempt tests/test_a100_sft_prediction_smoke.py::test_generation_stop_reason_boundary_instrumentation_pack_is_public_safe_and_bounded`: `4 passed`.
- `PYTHONPATH=src pytest -q`: `164 passed`.
- `uv run ruff check .`: `All checks passed`.
- `uv run mypy src`: `Success: no issues found in 16 source files`.
- `PYTHONPATH=src python -m voice2task.cli.data validate --sft data/public-samples/sft_public_sample.jsonl --dpo data/public-samples/dpo_public_sample.jsonl --manifest data/public-samples/manifest_public_sample.json --public`: `ok=true`, `sft_rows=12`, `dpo_pairs=26`.
- `PYTHONPATH=src python -m voice2task.cli.data dpo-check --dpo data/public-samples/dpo_public_sample.jsonl`: `total_pairs=26`.
- `PYTHONPATH=src python -m voice2task.cli.report leak-scan reports/public-sample/generation-stop-reason-boundary-instrumentation docs/human-briefs/2026-06-06-instrument-generation-stop-reason-boundary.html openspec/changes/instrument-generation-stop-reason-boundary --output reports/public-sample/generation-stop-reason-boundary-instrumentation/phase_validation_leak_scan_result.json`: `ok=true`, `findings=[]`.
- `git diff --check`: passed.
- `OPENSPEC_TELEMETRY=0 openspec validate --all --strict`: `5 passed`, `0 failed`.
- Post-archive `OPENSPEC_TELEMETRY=0 openspec validate --all --strict`: `4 passed`, `0 failed`.
- Post-archive leak scans: `ok=true`, `findings=[]`.

## Interpretation boundary

- `eos_token_seen=false` means tokenizer EOS was not observed in the generated token slice.
- `finish_state=no_eos_observed` is still not an actual model stop reason.
- `generated_token_count < max_new_tokens` still does not prove why generation stopped.
- The current trace records `actual_stop_reason_recorded=false` and `actual_stop_reason=null`.

## Historical boundary

- Prior A100 artifacts are not rewritten.
- Prior `generation_trace.jsonl` files only prove the fields they already recorded.
- A future A100/private-adapter rerun is required before making real stop-boundary claims for trained-adapter output.

## Non-claims

No A100 execution, training, private prediction rerun, decoding change, retry prompt change, parser relaxation, evaluator metric change, prediction repair, re-score, semantic-equivalence scoring, slot normalization, checkpoint release, adapter release, model recovery claim, model-quality claim, public full-corpus release, or live-browser benchmark improvement claim is made.
