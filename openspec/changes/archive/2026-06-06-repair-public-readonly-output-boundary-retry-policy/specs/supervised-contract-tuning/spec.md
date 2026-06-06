## ADDED Requirements

### Requirement: Repair public-readonly output-boundary and retry policy
The system SHALL make public-readonly search contract generation and retry prompts explicitly preserve a single-root Browser Task Contract JSON object without prose, Markdown, route-alias task types, or fields outside the root object.

#### Scenario: Serialize single-root public-readonly prompts
- **WHEN** the formatter builds SFT training text or prediction prompts
- **THEN** the system prompt MUST state that the output is exactly one JSON object, all eight top-level fields stay inside the same root object, no extra closing brace may appear before `normalized_command`, and no Markdown/prose wrapper is allowed

#### Scenario: Preserve public-readonly task type guidance
- **WHEN** the formatter builds a public-readonly search prompt
- **THEN** it MUST state that public-readonly search uses `task_type="search"` and `route="search_web"`, and MUST state that `search_web` is never a valid `task_type`

#### Scenario: Retry with strict JSON-only contract shape
- **WHEN** schema retry is triggered after an invalid prediction
- **THEN** the retry prompt MUST ask for exactly one minified Browser Task Contract JSON object, preserve all eight required fields inside the root object, prohibit prose/Markdown/code fences, and repeat the `task_type="search"` not `search_web` guidance

#### Scenario: Keep prompt repair local and bounded
- **WHEN** this repair is validated locally
- **THEN** it MUST NOT change strict parser semantics, repair historical predictions, normalize slots or strings, rerun private prediction, run A100, train a model, release checkpoints/adapters, or claim model recovery
