## ADDED Requirements

### Requirement: Publish retry decoding stop-boundary diagnosis
The system SHALL publish public-safe local evidence that separates observed generation facts, retry wrapper symptoms, and retry stop-boundary evidence gaps after the A100 schema retry wrapper-boundary rerun.

#### Scenario: Record observed decoding facts
- **WHEN** the diagnosis is generated from the latest public-safe A100 sidecars
- **THEN** it MUST record raw attempt generation finish state, EOS visibility, generated token counts, max token limit, retry parse status, retry wrapper counts, and strict final metrics without changing any predictions

#### Scenario: Record retry evidence gaps
- **WHEN** retry decoded summaries are available but retry generation traces are not available
- **THEN** the diagnosis MUST state that retry attempt EOS/stop-token/generated-token evidence is missing and MUST NOT infer retry stop behavior from raw attempt traces

#### Scenario: Bound diagnosis claims
- **WHEN** evidence, reports, tests, specs, or Human Briefs describe this phase
- **THEN** they MUST state that no A100 execution, training, private prediction rerun, decoding change, parser relaxation, evaluator metric change, prediction repair, prediction re-score, semantic-equivalence scoring, slot normalization, checkpoint release, adapter release, model recovery claim, model-quality claim, or live-browser benchmark improvement claim is made
