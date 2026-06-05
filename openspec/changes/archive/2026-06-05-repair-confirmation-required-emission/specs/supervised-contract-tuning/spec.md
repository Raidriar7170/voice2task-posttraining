## ADDED Requirements

### Requirement: Expose confirmation-required in SFT prompts
The system SHALL make `confirmation_required` visible as a required boolean Browser Task Contract field in shared SFT training text and trained-adapter prediction prompts.

#### Scenario: Serialize confirmation-aware SFT examples
- **WHEN** the formatter converts an SFT dataset row into training text
- **THEN** the rendered text MUST include `confirmation_required` in the required-field guidance or contract skeleton and MUST preserve the assistant target as canonical Browser Task Contract JSON rather than explanatory prose

#### Scenario: Serialize confirmation-aware prediction prompts
- **WHEN** the formatter builds a trained-adapter prediction prompt
- **THEN** the prompt MUST include `confirmation_required` as a required boolean field and MUST NOT include the gold target contract

#### Scenario: Show confirmation false in low-risk search example
- **WHEN** the shared prompt or canonical one-shot example demonstrates a low-risk weather/search command
- **THEN** the example MUST include `"confirmation_required": false` together with the legal `search_web` route and `search` task type
