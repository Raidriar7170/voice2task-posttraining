## Context

The previous A100 rerun showed two separate row-level issues:

1. raw output shape improved to whole JSON object, but `task_type` was missing for all rows.
2. retry output showed the desired `task_type="search"` field, but the model added prose and Markdown fences, so `_extract_strict_json_object()` correctly rejected it as `json_fragment_object`.

The current retry prompt already says JSON-only. The missing local repair is stronger wrapper-boundary phrasing that names the exact rejected pattern and makes the completion contract explicit in a form tests can pin down.

## Decision

Update `_schema_retry_prompt()` with a compact, high-salience wrapper boundary block:

- the answer must contain exactly one object and no text before or after it
- forbidden wrapper tokens include Markdown fences, headings, explanatory sentences, and trailing analysis
- retry should copy the canonical skeleton shape, then fill values, without adding a second object or commentary
- if the prior output had useful fields, those fields remain diagnostic input only and are not a repair path

Keep strict parsing untouched. If a model still wraps the retry output, the prediction must remain invalid and the sidecars must preserve the rejected retry evidence.

## Alternatives Considered

- **Relax parser to extract fenced JSON**: rejected because this would change success semantics and could hide the A100 failure mode.
- **Postprocess missing `task_type` locally**: rejected because this would be prediction repair and would overstate model recovery.
- **Immediately run another A100 rerun**: rejected for this local phase because the repo first needs a public-safe prompt-boundary evidence pack.

## Risks

- Prompt wording alone may not make the model comply on A100. The phase must not claim model recovery.
- Adding too much text can dilute the prompt. Keep the added block short and test for the exact constraints.
- Evidence must avoid private paths, host details, raw logs, adapters, checkpoints, caches, and private overrides.
