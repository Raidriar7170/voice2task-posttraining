## ADDED Requirements

### Requirement: Publish search-query slot wrapper-boundary diagnosis
The system SHALL publish public-safe local evidence that separates observed generation facts, Markdown wrapper symptoms, and wrapper-boundary evidence gaps after the A100 search-query slot-policy rerun.

#### Scenario: Record observed wrapper facts
- **WHEN** the diagnosis is generated from the latest public-safe search-query slot evidence
- **THEN** it MUST record compact `slots.query` fragments, Markdown-wrapped prediction counts, raw and retry parse status, strict final JSON validity, strict final exact match, and row-level observations without changing predictions or metrics

#### Scenario: Record evidence gaps
- **WHEN** the diagnosis relies on public-safe sidecars and reports only
- **THEN** it MUST state that the wrapper origin is not proven and MUST NOT infer model recovery, output postprocessing success, or parser acceptance from compact fragments alone

#### Scenario: Bound diagnosis claims
- **WHEN** reports, manifests, tests, or Human Briefs describe this phase
- **THEN** they MUST state that no A100 execution, training, decoding change, parser relaxation, slot normalization, metric relaxation, prediction repair, prediction re-score, semantic-equivalence scoring, model-quality claim, held-out generalization claim, or live-browser benchmark improvement claim is made
