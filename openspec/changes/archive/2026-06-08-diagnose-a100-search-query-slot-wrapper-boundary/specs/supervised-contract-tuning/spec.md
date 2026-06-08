## ADDED Requirements

### Requirement: Preserve wrapper-boundary diagnosis before behavior changes
The system SHALL preserve the A100 search-query slot wrapper-boundary diagnosis as a local evidence step before any future decoding, instrumentation, or output-postprocessing change.

#### Scenario: Diagnose before changing output behavior
- **WHEN** compact query content still appears inside Markdown-wrapped predictions
- **THEN** the system MUST first document the observed wrapper symptoms and evidence gaps before changing decoding parameters, output parsing, retry policy, or any postprocessing step

#### Scenario: Keep source evidence untouched
- **WHEN** local diagnosis evidence is generated
- **THEN** the system MUST preserve existing predictions, raw decoded summaries, generation traces, metrics, schema guard summaries, and manifests as source evidence without extracting, coercing, replacing, normalizing, repairing, or re-scoring outputs
