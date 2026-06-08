## ADDED Requirements

### Requirement: Reinforce compact query slot preservation in prompts
The shared SFT training and trained-adapter prediction prompt SHALL make the rejected decomposed search-slot shape visible without including row-specific gold target contracts in prediction prompts.

#### Scenario: Serialize prompt with decomposed slot rejection
- **WHEN** SFT training text or trained-adapter prediction prompt is rendered
- **THEN** the model-visible system prompt MUST state that public-readonly search/weather contracts preserve compact `slots.query`
- **AND** it MUST state that decomposed `city/date/topic` slot objects are rejected for the same search query
- **AND** it MUST state that this is target-formatting guidance, not evaluator normalization, semantic-equivalence scoring, prediction repair, or re-score

#### Scenario: Preserve prediction prompt gold exclusion
- **WHEN** a trained-adapter prediction prompt is rendered for a row with a target-only slot value
- **THEN** the prompt MUST include the generic compact-query/decomposed-slot policy
- **AND** it MUST NOT include the row-specific gold target contract or target-only slot value
