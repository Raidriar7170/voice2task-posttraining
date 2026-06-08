# A100 compact query slot preservation rerun

## Conclusion

A100 prediction-only train-split diagnostic evidence still preserves the `seed-search-weather-aug-1` strict compact slots.query mismatch: the row remains schema-valid but emits `city/date/topic` slots, so it is not exact-match recovery.

## Evidence

- Predictions: `reports/public-sample/a100-compact-query-slot-preservation-rerun/predictions.jsonl`
- Metrics: `reports/public-sample/a100-compact-query-slot-preservation-rerun/metrics.json`
- Diagnosis: `reports/public-sample/a100-compact-query-slot-preservation-rerun/compact_query_slot_preservation_rerun_diagnosis.json`
- Target row outcome: `strict_mismatch_preserved`

## Validation Commands

- `PYTHONPATH=src pytest -q`: 193 passed.
- `uv run ruff check .`: All checks passed.
- `uv run mypy src`: Success, no issues found in 16 source files.
- `OPENSPEC_TELEMETRY=0 openspec validate --all --strict`: 5 passed pre-archive; 4 passed post-archive.
- Public data validation: ok=true; sft_rows=12; dpo_pairs=27; decomposed_search_slots=1.
- Leak scans: ok=true; findings=[].

## Boundary

- A100 prediction-only train-split diagnostic.
- Strict compact slots.query remains the target policy; the result does not use slot normalization or semantic-equivalence scoring.
- No training, parser relaxation, evaluator metric change, prediction repair, re-score, checkpoint release, adapter release, held-out generalization, production readiness, live-browser benchmark, or model-quality claim.
