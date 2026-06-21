## ADDED Requirements

### Requirement: Project V1 contracts into experimental V2 Core
The system SHALL provide a deterministic, pure projection from a V1 Browser Task
Contract into an experimental V2 Core that contains only `task_type`, `route`,
`safety`, `confirmation_required`, and `slots`.

#### Scenario: Projection removes derived fields
- **WHEN** a valid V1 contract is projected to V2 Core
- **THEN** the projected contract MUST omit `normalized_command`, `language`,
  and `contract_version`
- **AND** it MUST preserve task type, route, safety allow/reason,
  confirmation requirement, and slots without model calls or network access

#### Scenario: V1 schema remains unchanged
- **WHEN** projection code is added
- **THEN** the formal BrowserTaskContract V1 schema and validation behavior
  MUST remain unchanged

### Requirement: Validate and canonicalize V2 Core deterministically
The system SHALL validate V2 Core shape and produce deterministic canonical JSON
for repeatable comparison.

#### Scenario: Core validation accepts only allowed fields
- **WHEN** a V2 Core object includes fields outside task type, route, safety,
  confirmation requirement, and slots
- **THEN** validation MUST fail

#### Scenario: Canonical JSON is stable
- **WHEN** the same V2 Core object is canonicalized multiple times
- **THEN** every canonical JSON output MUST be byte-identical

### Requirement: Build experimental V2 envelope from V2 Core
The system SHALL build a deterministic experimental V2 envelope by adding fixed
derived metadata and a renderer-produced display command.

#### Scenario: Envelope fixes derived metadata
- **WHEN** a valid V2 Core object is converted to an envelope
- **THEN** the envelope MUST set `language` to `zh-CN`
- **AND** it MUST set `contract_version` to `v2`
- **AND** it MUST not read those values from the V1 model prediction

#### Scenario: Envelope is deterministic
- **WHEN** the same V2 Core object is converted to an envelope multiple times
- **THEN** every envelope output MUST be byte-identical

### Requirement: Render normalized command as bounded display prototype
The system SHALL provide an experimental deterministic normalized-command
renderer for evaluation coverage only.

#### Scenario: Renderer uses core fields only
- **WHEN** the renderer builds a display command
- **THEN** it MUST use only task type, route, and slots from V2 Core
- **AND** it MUST not read the original or predicted `normalized_command`

#### Scenario: Renderer fails closed
- **WHEN** a task type, route, or slot pattern cannot be rendered by a bounded
  template
- **THEN** the renderer MUST return an unsupported result with a reason instead
  of generating free-form text

#### Scenario: Renderer preserves distinct slot values
- **WHEN** core slots contain different cities, dates, products, URLs, field
  values, or other concrete values
- **THEN** renderer output MUST NOT merge, substitute, or collapse those values

### Requirement: Keep projection offline and bounded
The system SHALL keep Contract V2 projection local, offline, and evidence-only.

#### Scenario: Projection does not trigger model work
- **WHEN** projection evaluation runs
- **THEN** it MUST NOT train, run DPO or GRPO, generate new predictions, invoke
  A100 or SSH, change prompts, mutate data, change splits, or call an LLM judge

#### Scenario: Projection does not implement production V2
- **WHEN** projection artifacts recommend a later Contract V2 implementation
- **THEN** this phase MUST NOT modify runtime consumers, production schemas, SFT
  or DPO formatting, or Voice-to-Browser Agent integration
