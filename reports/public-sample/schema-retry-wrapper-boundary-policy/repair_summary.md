# Schema retry wrapper-boundary policy repair

Status: local retry prompt boundary hardening only. No A100 execution, training, private prediction rerun, parser relaxation, evaluator metric change, prediction repair, or model recovery claim is made.

## Source diagnosis

The prior A100 output-boundary retry-policy rerun remained strict schema-invalid: `json_valid_rate=0.0000` and `contract_exact_match=0.0000`. Raw output became whole JSON objects for `3/3` rows, but all rows omitted `task_type`. Retry output visibly contained `task_type=search` for `3/3` rows, but was prose/Markdown-wrapped and rejected by the strict parser.

## Local repair

The retry prompt now explicitly says:

- no prefix or suffix text
- no `这是` / `以下` / `Here is` style prefaces
- no Markdown fences, headings, prose, trailing analysis, or user-input restatement after JSON
- no second JSON object
- strict parser will reject the retry attempt unless the whole response is exactly one JSON object

## Boundary

This evidence observes prompt text only. It does not change parser semantics, repair historical predictions, normalize fields, re-score outputs, rerun A100, train a model, or claim model recovery.
