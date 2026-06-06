## ADDED Requirements

### Requirement: Expose public-readonly search contract policy in SFT prompts
The system SHALL make the shared SFT training and trained-adapter prediction prompt explicitly state the Browser Task Contract field policy for low-risk public-readonly search/weather requests.

#### Scenario: Serialize training prompt with public-readonly search policy
- **WHEN** SFT training text is rendered for a public-readonly weather or public information lookup row
- **THEN** the model-visible system prompt MUST state that public-readonly information lookup uses `task_type="search"`, `route="search_web"`, `safety.allow=true`, `safety.reason="public_readonly"`, `confirmation_required=false`, and object-shaped `slots.query`
- **AND** it MUST state that `task_type` remains one of the legal task enum values and MUST NOT reuse route enum values such as `search_web`

#### Scenario: Serialize prediction prompt without row-specific gold contract
- **WHEN** a trained-adapter prediction prompt is rendered
- **THEN** the prompt MUST include the public-readonly search policy
- **AND** it MUST NOT include the row-specific gold target contract or row-specific gold-only tokens beyond text already present in the user input

#### Scenario: Surface prompt constraint metadata
- **WHEN** prompt constraint metadata is recorded in prediction metadata, prompt snapshots, manifests, reports, or evidence packs
- **THEN** it MUST include explicit booleans for public-readonly search policy visibility, `public_readonly` safety reason visibility, search query slot guidance visibility, and task-type-not-route-enum guidance visibility
