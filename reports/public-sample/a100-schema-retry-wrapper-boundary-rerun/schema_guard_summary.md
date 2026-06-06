# A100 schema retry wrapper-boundary schema guard summary

Strict schema recovery was not observed. Raw output remained whole JSON objects missing `task_type` for 3/3 rows, and retry output remained prose/Markdown-wrapped for 3/3 rows even though the retry prompt constraints were visible in metadata.

- raw_json_object_count: 3/3
- raw_missing_task_type_count: 3/3
- retry_prose_markdown_wrapper_count: 3/3
- retry_attempt_schema_valid_count: 0/3
- validated_output_schema_valid_count: 0/3
