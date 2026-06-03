# SFT Target-Template Alignment - SFT target-template alignment diagnostic

This diagnostic compares public-sample SFT training rendering with prediction prompts. It does not run private prediction, retrain, repair outputs, or replace prior diagnostic artifacts.

## Boundary

- This is not a checkpoint release.
- This is not an adapter release.
- This is not dev/test generalization evidence.
- This makes no production-readiness claim.
- This is not a live-browser benchmark improvement claim.

## Summary

- Diagnostic status: `public_safe_structural_evidence`
- Rows compared: `3`
- Prediction split: `train`
- Same system/user prefix for all rows: `True`
- Assistant target in all training text: `True`
- Assistant target excluded from all prediction prompts: `True`
- Structural target span status: `found`

## Label-Mask Evidence

- Status: `labels_unavailable`
- True label-mask status: `unavailable`
- Prompt tokens masked: `None`
- Assistant tokens carry loss: `None`
- Evidence gaps: `['real_training_labels_not_inspected', 'real_training_label_provenance_missing']`

## Chat Template Evidence

- Rendering source: `fallback`
- Fallback policy: `deterministic_role_plain_text`
- Tokenizer template status: `not_loaded`
- Evidence gaps: `['tokenizer_chat_template_not_loaded']`

## Adapter/Base Metadata Alignment

- Base model status: `prediction_metadata_private_placeholder`
- Base model training config: `Qwen/Qwen2.5-0.5B-Instruct`
- Base model prediction metadata: `<private_base_model>`
- Model source matches: `True`
- Stack matches: `True`
- Prediction split matches: `True`
- Adapter gate: `{'adapter_configured': True, 'cli_run_prediction': True, 'config_allow_private_prediction': True, 'fixture_mode': False, 'will_run_private_prediction': True, 'adapter_path_public_safe': '<configured_not_disclosed>'}`
- Adapter release status: `not_released`
- Prediction source kind: `private_a100_adapter`
- Formatting policy matches: `True`

## Prior Artifacts Linked

- `generation_trace`: `reports/public-sample/a100-train-split-overfit-diagnostic/generation_trace.jsonl`
- `leak_scan`: `reports/public-sample/a100-train-split-overfit-diagnostic/leak_scan_result.json`
- `manifest`: `reports/public-sample/a100-train-split-overfit-diagnostic/manifest.json`
- `metrics`: `reports/public-sample/a100-train-split-overfit-diagnostic/metrics.json`
- `metrics_markdown`: `reports/public-sample/a100-train-split-overfit-diagnostic/metrics.md`
- `objective_inspection`: `reports/public-sample/a100-train-split-overfit-diagnostic/objective_inspection.json`
- `predictions`: `reports/public-sample/a100-train-split-overfit-diagnostic/predictions.jsonl`
- `prompt_snapshot`: `reports/public-sample/a100-train-split-overfit-diagnostic/prompt_snapshot.json`
- `raw_decoded_summary`: `reports/public-sample/a100-train-split-overfit-diagnostic/raw_decoded_summary.jsonl`
- `report`: `reports/public-sample/a100-train-split-overfit-diagnostic/report.md`

## Row Evidence

### `seed-search-weather`

- Same system/user prefix: `True`
- Assistant target in training text: `True`
- Assistant target in prediction prompt: `False`
- Prediction prompt ends with generation boundary: `True`
- Structural proxy status: `assistant_target_span_found`
- Assistant target span: `{'status': 'found', 'start': 587, 'end': 815}`
- Training text SHA-256: `9d7f10b146a5814760bdf2a2682c8409c3ef21ece6b22b59a923a74378c5eca1`
- Prediction prompt SHA-256: `fa9a524462f0f4309bd376a41c57dbc8a8718cade5c025af07c900838de7db1a`
- Assistant target SHA-256: `a5b21804fd7f2c927ffa2895b1abc876727b49e231020d1a3080276ffcf288ce`
- Training text characters: `815`
- Prediction prompt characters: `586`
- Assistant target characters: `228`

### `seed-search-weather-aug-1`

- Same system/user prefix: `True`
- Assistant target in training text: `True`
- Assistant target in prediction prompt: `False`
- Prediction prompt ends with generation boundary: `True`
- Structural proxy status: `assistant_target_span_found`
- Assistant target span: `{'status': 'found', 'start': 585, 'end': 813}`
- Training text SHA-256: `eb9bafa73234629f7ab1778208635a625abcd39bdcd8fa63bca0cd031291bf43`
- Prediction prompt SHA-256: `98d0f5e5e0c37ad335100c972ad992d5e85f6dac82277f06cab190adc21db436`
- Assistant target SHA-256: `a5b21804fd7f2c927ffa2895b1abc876727b49e231020d1a3080276ffcf288ce`
- Training text characters: `813`
- Prediction prompt characters: `584`
- Assistant target characters: `228`

### `seed-search-weather-aug-2`

- Same system/user prefix: `True`
- Assistant target in training text: `True`
- Assistant target in prediction prompt: `False`
- Prediction prompt ends with generation boundary: `True`
- Structural proxy status: `assistant_target_span_found`
- Assistant target span: `{'status': 'found', 'start': 584, 'end': 812}`
- Training text SHA-256: `64a160139192aa1c0efdac4839190984b27d08edc6875e9c6c9f6a770fec8384`
- Prediction prompt SHA-256: `022c2a88fa5608840362ae9bf200e4b380554957e2e10f5dcb70be645973e706`
- Assistant target SHA-256: `a5b21804fd7f2c927ffa2895b1abc876727b49e231020d1a3080276ffcf288ce`
- Training text characters: `812`
- Prediction prompt characters: `583`
- Assistant target characters: `228`
