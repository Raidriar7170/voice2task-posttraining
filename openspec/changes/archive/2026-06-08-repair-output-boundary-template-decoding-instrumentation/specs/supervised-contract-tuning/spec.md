## ADDED Requirements

### Requirement: Harden first-pass prediction output boundary
The system SHALL expose a machine-only first-pass prediction output boundary for trained-adapter prediction prompts without changing strict parser, evaluator, training, retry, or prediction repair behavior.

#### Scenario: Build machine-only first-pass prediction prompt
- **WHEN** the formatter builds a trained-adapter prediction prompt
- **THEN** the prompt MUST require exactly one root Browser Task Contract JSON object, require the first non-empty character to be `{`, require the last non-empty character to be `}`, prohibit Markdown/code fences/prose/prefix/suffix/trailing analysis, prohibit second JSON objects, and state that wrapped fragments remain invalid under the strict whole-object parser

#### Scenario: Report first-pass output-boundary visibility
- **WHEN** prediction metadata or prompt snapshots summarize first-pass prediction behavior
- **THEN** they MUST expose machine-readable booleans for exact JSON-only output, no Markdown/code-fence/prose wrapper, no preamble/suffix/trailing analysis, no second JSON object, first/last brace requirements, and strict whole-object parser rejection visibility

#### Scenario: Preserve strict first-pass parsing
- **WHEN** a first-pass prediction contains a valid Browser Task Contract embedded inside Markdown, prose, wrapper text, or explanatory text
- **THEN** the strict parser MUST continue to reject it as a non-whole JSON-object prediction rather than extracting, repairing, coercing, normalizing, re-scoring, or replacing the embedded fragment

#### Scenario: Keep behavior-change phase local
- **WHEN** first-pass output-boundary hardening is implemented
- **THEN** the phase MUST NOT run A100 prediction, train a model, release an adapter/checkpoint, change evaluator metrics, relax parsing, rewrite prior A100 artifacts, or claim model-quality improvement
