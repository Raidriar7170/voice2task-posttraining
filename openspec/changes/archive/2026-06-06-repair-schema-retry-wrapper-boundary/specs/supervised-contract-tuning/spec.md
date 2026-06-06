## ADDED Requirements

### Requirement: Repair schema retry wrapper boundary
The system SHALL make schema retry prompts explicitly reject prose, Markdown, and any text outside a single Browser Task Contract JSON root while preserving strict parser semantics.

#### Scenario: Build no-wrapper retry prompt
- **WHEN** schema retry is triggered after a schema-invalid prediction
- **THEN** the retry prompt MUST state that the response contains exactly one JSON object, the first non-whitespace character is `{`, the last non-whitespace character is `}`, and there is no text before or after that object

#### Scenario: Prohibit wrapper failure modes
- **WHEN** schema retry is triggered after a prose-wrapped, Markdown-wrapped, or fragment-like failure
- **THEN** the retry prompt MUST explicitly prohibit Markdown fences, headings, explanatory prose, natural-language prefaces, trailing analysis, and second JSON objects

#### Scenario: Preserve strict retry rejection
- **WHEN** a retry attempt still emits Markdown, explanatory prose, JSON fragments, missing required fields, illegal enum values, or otherwise schema-invalid output
- **THEN** the prediction artifact MUST preserve the invalid retry attempt, set `validated_output_schema_valid=false`, and MUST NOT extract, coerce, replace, normalize, or re-score the fragment

#### Scenario: Keep retry boundary repair local
- **WHEN** this repair is validated locally
- **THEN** it MUST NOT run A100, run training, rerun private prediction, change parser semantics, change evaluator metrics, repair historical predictions, normalize slots or strings, release checkpoints/adapters, or claim model recovery
