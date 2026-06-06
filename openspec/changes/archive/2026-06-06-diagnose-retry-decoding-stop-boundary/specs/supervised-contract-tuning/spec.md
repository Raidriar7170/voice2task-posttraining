## ADDED Requirements

### Requirement: Preserve retry stop-boundary diagnostic boundary
The system SHALL preserve retry decoding stop-boundary diagnosis as a local evidence step before any future behavior-changing decoding or instrumentation work.

#### Scenario: Diagnose before changing decoding behavior
- **WHEN** A100 retry output remains prose-wrapped or Markdown-wrapped after prompt boundary hardening
- **THEN** the system MUST first document observed retry symptoms and missing retry generation trace evidence before changing decoding parameters, parser behavior, or prediction postprocessing

#### Scenario: Keep model output unchanged
- **WHEN** local diagnosis evidence is generated
- **THEN** the system MUST preserve existing predictions, raw decoded summaries, generation traces, metrics, schema guard summaries, and manifests as source evidence without extracting, coercing, replacing, normalizing, repairing, or re-scoring outputs
