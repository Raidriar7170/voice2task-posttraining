# Compact query slot preservation

This is local prompt/data reinforcement evidence for compact `slots.query` preservation. It is derived from the existing public residual diagnosis and the current committed public sample artifacts.

## Conclusion

The public DPO sample now includes one `decomposed_search_slots` hard negative for the weather/search seed row. The chosen contract keeps compact `slots.query`, while the rejected contract uses `city/date/topic`.

## Checks

- Public sample SFT rows: `12`
- Public sample DPO pairs: `27`
- `decomposed_search_slots` rejected pairs: `1`
- Chosen compact slots: `{"query":"北京明天天气"}`
- Rejected decomposed slots: `{"city":"北京","date":"明天","topic":""}`
- Prompt policy exposes compact `slots.query`, rejects `city/date/topic`, and records that this is target-formatting guidance rather than evaluator normalization.

## Source Residual

- Prior diagnosis: `reports/public-sample/fence-suppression-slot-residual-diagnosis/slot_residual_diagnosis.json`
- Residual row: `seed-search-weather-aug-1`
- Historical gold slots: `{"query":"北京明天天气"}`
- Historical predicted slots: `{"city":"北京","date":"明天","topic":""}`

## Boundary

- No A100 execution was performed in this phase.
- No training, prediction rerun, evaluator metric change, parser change, slot normalization, semantic-equivalence scoring, prediction repair, prediction replacement, or re-score was performed.
- Prior A100 predictions remain historical evidence and are not repaired, normalized, re-scored, or reinterpreted as exact-match recovery.
- This is not model recovery evidence, model-quality improvement evidence, held-out generalization, production readiness, checkpoint or adapter release, or live-browser benchmark evidence.

## Validation

- `PYTHONPATH=src pytest -q tests/test_formatting_training.py tests/test_dataset_builder.py tests/test_dpo_validation.py tests/test_a100_sft_prediction_smoke.py::test_compact_query_slot_preservation_pack_is_public_safe_and_bounded`: `31 passed`.
- `PYTHONPATH=src pytest -q`: `192 passed`.
- `PYTHONPATH=src python -m voice2task.cli.data validate --sft data/public-samples/sft_public_sample.jsonl --dpo data/public-samples/dpo_public_sample.jsonl --manifest data/public-samples/manifest_public_sample.json --public`: `ok=true`, `sft_rows=12`, `dpo_pairs=27`.
- `PYTHONPATH=src python -m voice2task.cli.data dpo-check --dpo data/public-samples/dpo_public_sample.jsonl`: `27` total pairs with `decomposed_search_slots=1`.
- `uv run ruff check .`: passed.
- `uv run mypy src`: passed.
- `OPENSPEC_TELEMETRY=0 openspec validate --all --strict`: `4 passed, 0 failed`.
- `git diff --check`: passed.
