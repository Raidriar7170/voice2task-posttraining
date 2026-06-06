## ADDED Requirements

### Requirement: Instrument generation stop-boundary evidence
The system SHALL record public-safe stop-boundary evidence fields in trained-adapter generation trace rows without changing decoding, retry, parser, metric, or prediction output behavior.

#### Scenario: Record stop-boundary evidence fields
- **WHEN** a trained-adapter prediction export writes `generation_trace.jsonl`
- **THEN** each generation trace row MUST preserve the existing id, attempt, prediction source kind, strategy, sampling, max-token limit, generated token count, EOS visibility, and finish-state fields and MUST also include max-token-hit status, finish-state basis, stop-boundary evidence, and whether an actual model/generation stop reason was recorded

#### Scenario: Preserve prediction behavior
- **WHEN** stop-boundary evidence instrumentation is added
- **THEN** the system MUST NOT change decoding parameters, retry prompt text, strict parser semantics, schema guard source selection, final predictions, evaluator metrics, output repair behavior, prediction re-scoring, semantic-equivalence scoring, slot normalization, or training behavior

#### Scenario: Keep stop-reason claims conservative
- **WHEN** a trace row has `finish_state=no_eos_observed`
- **THEN** the row MUST make clear that the finish state is based on tokenizer EOS membership and MUST NOT claim an actual model/generation stop reason unless such a reason is explicitly recorded
