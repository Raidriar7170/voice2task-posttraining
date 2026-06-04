## ADDED Requirements

### Requirement: Constrain contract decoding without coercive repair
The system SHALL make trained-adapter prediction retry prompts canonical, JSON-only, and explicit about legal Browser Task Contract values while preserving invalid model outputs as failures.

#### Scenario: Build canonical retry prompt
- **WHEN** schema guard retry is triggered after a schema-invalid prediction
- **THEN** the retry prompt MUST include a complete canonical Browser Task Contract JSON object skeleton, legal `task_type` and `route` enum values, required `safety.allow` boolean shape, and instructions forbidding Markdown, explanatory prose, code fences, path-like routes, and legacy enum aliases

#### Scenario: Preserve invalid retry output
- **WHEN** the retry attempt still emits Markdown, explanatory prose, illegal enum values, path-like routes, missing required fields, or otherwise schema-invalid output
- **THEN** the prediction artifact MUST preserve the raw and retry attempts as observed evidence, set `validated_output_schema_valid=false`, and MUST NOT substitute fixture-mode, rule-baseline, gold-contract, or locally coerced output

#### Scenario: Accept only schema-valid model output
- **WHEN** raw or retry model output parses to a Browser Task Contract that passes `BrowserTaskContract.from_dict()`
- **THEN** the prediction artifact MAY use that model output as the validated output source and record whether it came from the raw or retry attempt
