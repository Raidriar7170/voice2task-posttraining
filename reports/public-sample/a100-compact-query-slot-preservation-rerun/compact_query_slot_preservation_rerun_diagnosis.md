# A100 compact query slot preservation rerun diagnosis

This is a train-split-only prediction diagnostic, not a held-out generalization claim and not model-quality evidence.

## Result

- Strict JSON/schema validity: `1.0000`
- Strict contract exact match: `0.0000`
- Strict slot F1: `0.6667`
- Target residual row: `seed-search-weather-aug-1`
- Target outcome: `strict_mismatch_preserved`

## Validation Commands

- `PYTHONPATH=src pytest -q`: 193 passed.
- `uv run ruff check .`: All checks passed.
- `uv run mypy src`: Success, no issues found in 16 source files.
- `OPENSPEC_TELEMETRY=0 openspec validate --all --strict`: 5 passed pre-archive; 4 passed post-archive.
- Public data validation: ok=true; sft_rows=12; dpo_pairs=27; decomposed_search_slots=1.
- Leak scans: ok=true; findings=[].

## Boundary

- A100 prediction-only, train-split-only prediction diagnostic.
- No training, parser relaxation, evaluator metric change, slot normalization, semantic-equivalence scoring, prediction repair, or re-score.
- Do not claim checkpoint release, adapter release, held-out generalization, production readiness, live-browser benchmark improvement, or model recovery.
