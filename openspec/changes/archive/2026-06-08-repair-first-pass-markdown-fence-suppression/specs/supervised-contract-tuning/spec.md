## ADDED Requirements

### Requirement: Suppress first-pass Markdown fence generation
The system SHALL configure trained-adapter prediction generation to suppress Markdown code-fence token sequences when the active tokenizer can provide non-empty token ids, while preserving strict parser and prediction provenance behavior.

#### Scenario: Build generation kwargs with fence suppression
- **WHEN** trained-adapter prediction calls model generation with a tokenizer that can encode Markdown fence strings
- **THEN** the generation kwargs MUST include `bad_words_ids` for non-empty tokenizer-derived Markdown fence token sequences
- **AND** the call MUST keep greedy decoding, configured `max_new_tokens`, and the existing pad token policy

#### Scenario: Preserve strict parser behavior for fenced output
- **WHEN** a model still emits a valid Browser Task Contract wrapped in Markdown fences
- **THEN** the strict parser MUST continue to reject it as a non-whole JSON-object prediction rather than extracting, repairing, coercing, normalizing, re-scoring, or replacing the embedded fragment

#### Scenario: Report suppression policy in prediction metadata
- **WHEN** prediction metadata or prompt snapshots summarize trained-adapter prediction behavior
- **THEN** they MUST expose machine-readable Markdown fence suppression policy fields separate from parser, retry, and output-boundary prompt metadata

#### Scenario: Keep local behavior phase bounded
- **WHEN** Markdown fence suppression is implemented locally
- **THEN** the phase MUST NOT run A100 prediction, train a model, release an adapter/checkpoint, rewrite prior A100 artifacts, change evaluator metrics, relax parsing, or claim model-quality improvement
