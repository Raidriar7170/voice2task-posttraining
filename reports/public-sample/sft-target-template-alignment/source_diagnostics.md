# SFT target-template alignment diagnostic

This source diagnostic is evidence-only: invalid predictions remain invalid. It does not repair, normalize, coerce, or replace predictions.

## Boundary

- This is not a checkpoint release.
- This is not an adapter release.
- This makes no production-readiness claim.
- This makes no full-private-corpus claim.
- This is not a live-browser benchmark or benchmark-improvement claim.

## Summary

- Gold rows: `12`
- Predictions: `3`
- Missing predictions: `9`
- Gold path-like route targets: `0`
- Gold list-shaped slots targets: `0`
- Prediction path-like routes: `0`
- Prediction list-shaped slots: `0`
- Schema-invalid predictions: `3`

## Split And Training Coverage

- Configured training split: `train`
- Configured prediction split: `train`
- Training rows in gold sample: `3`
- Prediction-split gold rows: `3`
- Gold split counts: `{'dev': 3, 'test': 6, 'train': 3}`
- Training task_type coverage: `{'search': 3}`
- Training route coverage: `{'search_web': 3}`

## Current Prompt Constraints

These describe the current formatter and future rerun preparation. They are not proof that older prediction artifacts used this strengthened prompt.

- task_type enum visible: `True`
- route enum visible: `True`
- route is not a URL/path visible: `True`
- slots object-not-array visible: `True`

## Prediction-Run Prompt Evidence

- prompt constraints present in metadata: `True`
- fields present: `['route_enum_visible', 'route_not_url_or_path_visible', 'slots_object_not_array_visible', 'task_type_enum_visible']`
- constraints: `{'task_type_enum_visible': True, 'route_enum_visible': True, 'route_not_url_or_path_visible': True, 'slots_object_not_array_visible': True}`
- evidence gaps: `[]`
- current prompt constraints are rerun preparation, not old-run evidence: `False`

## Decoding Evidence

Evidence gaps are missing evidence, not inferred cause.

- decoding_policy present: `True`
- fields present: `['do_sample', 'max_new_tokens', 'raw_decoded_sidecar_written', 'schema_repair_applied', 'strategy']`
- policy: `{'strategy': 'greedy', 'do_sample': False, 'max_new_tokens': 256, 'raw_decoded_sidecar_written': True, 'schema_repair_applied': False}`
- evidence gaps: `['generated_token_count', 'eos_or_finish_state']`

## Symptom Examples

- none
