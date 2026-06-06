# A100 output-boundary retry-policy schema guard summary

Status: strict schema recovery was not observed. This summary records row-level schema guard behavior without repairing or rescoring predictions.

## Counts

- prediction_count: 3
- raw_attempt_schema_valid_count: 0
- retry_attempted_count: 3
- retry_attempt_schema_valid_count: 0
- validated_output_schema_valid_count: 0
- raw_json_object_count: 3
- raw_missing_task_type_count: 3
- retry_prose_markdown_wrapper_count: 3
- retry_task_type_search_visible_count: 3

## Interpretation

The output-boundary prompt repair changed the raw shape from the prior non-JSON pattern into whole JSON objects for 3/3 rows, but all raw objects still omitted `task_type`. The retry prompt exposed `task_type=search` for 3/3 rows, yet the model wrapped the retry in prose/Markdown, so the strict whole-object parser rejected every retry. These are diagnostic observations only; no semantic-equivalence scoring, slot normalization, prediction repair, or metric relaxation was applied.
