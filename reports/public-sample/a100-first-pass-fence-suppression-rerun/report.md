# A100 first-pass fence-suppression rerun

## Conclusion
The A100 prediction-only rerun observed 0/3 Markdown-wrapped predictions and 3/3 strict schema-valid raw outputs with generation-time Markdown fence suppression active.

## Evidence
- predictions: `reports/public-sample/a100-first-pass-fence-suppression-rerun/predictions.jsonl`
- prediction_metadata: `reports/public-sample/a100-first-pass-fence-suppression-rerun/prediction_metadata.json`
- prompt_snapshot: `reports/public-sample/a100-first-pass-fence-suppression-rerun/prompt_snapshot.json`
- raw_decoded_summary: `reports/public-sample/a100-first-pass-fence-suppression-rerun/raw_decoded_summary.jsonl`
- generation_trace: `reports/public-sample/a100-first-pass-fence-suppression-rerun/generation_trace.jsonl`
- metrics_json: `reports/public-sample/a100-first-pass-fence-suppression-rerun/metrics.json`
- schema_guard_summary: `reports/public-sample/a100-first-pass-fence-suppression-rerun/schema_guard_summary.json`
- fence_suppression_rerun_diagnosis: `reports/public-sample/a100-first-pass-fence-suppression-rerun/fence_suppression_rerun_diagnosis.json`

## Observed Metrics
- json_valid_rate: `1.0`
- contract_exact_match: `0.6666666666666666`
- slot_f1: `0.6666666666666666`
- markdown_wrapped_prediction_count: `0`
- validated_output_schema_valid_count: `3`

## Remaining Risk
One train row still has a strict slot mismatch. This phase does not normalize, repair, or re-score that mismatch.

## Boundary
- A100 prediction-only, train-split-only evidence.
- No training, parser relaxation, evaluator metric change, prediction repair, prediction re-score, slot normalization, semantic-equivalence scoring, checkpoint release, or adapter release.
- Do not claim held-out generalization, production readiness, live-browser benchmark improvement, model recovery, or broad model-quality improvement.
