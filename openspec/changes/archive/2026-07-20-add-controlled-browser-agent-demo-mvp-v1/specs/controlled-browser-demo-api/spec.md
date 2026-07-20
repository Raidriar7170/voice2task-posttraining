## ADDED Requirements

### Requirement: Inference modes are explicit and fail closed
The API SHALL construct exactly the configured fixture or private-model provider, expose that mode publicly, and SHALL never substitute fixture output for an unavailable private model.

#### Scenario: Supported fixture utterance is submitted
- **WHEN** fixture mode receives one of the six exact approved utterances
- **THEN** it SHALL return the corresponding validated V1 contract with `inference_mode=fixture`

#### Scenario: Unsupported fixture or unavailable private model is used
- **WHEN** fixture text is unmatched or private configuration/loading is unavailable
- **THEN** the session SHALL fail with a stable provider code and no plan or execution SHALL be fabricated

#### Scenario: Private output is schema-invalid
- **WHEN** the first strict whole-object private generation fails schema validation
- **THEN** the provider SHALL retry once with the current schema retry prompt and then fail closed if still invalid

### Requirement: Audio input is bounded and provider controlled
The API SHALL accept browser recording or upload only for allowed MIME types and size, avoid persistent raw audio by default, and require transcript confirmation before inference.

#### Scenario: ASR is disabled
- **WHEN** an audio session is created in the default ASR mode
- **THEN** creation SHALL return the accepted `INPUT_RECEIVED` snapshot and the owned background task SHALL fail the session with `ASR_PROVIDER_UNAVAILABLE`, remove temporary audio, and keep text input available

#### Scenario: Audio validation or transcription completes
- **WHEN** valid bounded audio is handled by fixture or explicitly configured HTTP ASR
- **THEN** the temporary input SHALL be deleted and the session SHALL stop at `TRANSCRIPT_READY` until the user confirms or edits the transcript

#### Scenario: Request is cancelled before audio task registration
- **WHEN** cancellation occurs after a validated upload is staged but before `SessionTaskRegistry` accepts ownership
- **THEN** request-scope cleanup SHALL delete the staged file, while a successfully registered task SHALL own exactly one idempotent completion cleanup

#### Scenario: Invalid audio metadata is supplied
- **WHEN** MIME, size, endpoint, or response violates the allowlist
- **THEN** the API SHALL reject it without third-party fallback or retained audio

#### Scenario: Client filename contains path components
- **WHEN** an upload supplies an absolute or traversal-like client filename
- **THEN** the API SHALL ignore that filename, use a server-generated random temporary name, and remove the temporary file

### Requirement: HTTP resources expose the controlled session lifecycle
The API SHALL implement health, public config/schema, session create/read/list/delete, transcript confirmation, plan confirmation, execute, cancel, events, and artifact endpoints with consistent state guards.

#### Scenario: Text session is created
- **WHEN** valid text and SessionContext are posted
- **THEN** the API SHALL return `202 Accepted` with a session ID and initial persisted snapshot while `SessionTaskRegistry` asynchronously prepares a validated contract and policy outcome

#### Scenario: Runtime evidence schemas are inspected
- **WHEN** a client reads `GET /api/schemas/runtime`
- **THEN** the response SHALL expose strict `ExecutionEvidence` and `ExecutionOutcome` schemas whose evidence fields are independent `action_outputs` and `dom_snapshot` mappings, without the retired shared `values` field

#### Scenario: Confirmation challenge is approved
- **WHEN** the client submits the correct challenge and plan version
- **THEN** the API SHALL consume the challenge and return `CONFIRMED` without executing; a separate execute request SHALL be required

#### Scenario: Confirmation challenge is issued or rotated
- **WHEN** `POST /api/sessions/{session_id}/confirmation-challenge` is accepted for an unexpired `AWAITING_CONFIRMATION` plan
- **THEN** the response SHALL contain exactly `confirmation_token`, `plan_id`, `plan_version`, and `expires_at`; only the token hash SHALL be persisted and every prior token SHALL become invalid

#### Scenario: Session is deleted
- **WHEN** a terminal inactive session is deleted
- **THEN** its database rows, local artifacts, and any temporary audio SHALL be removed without affecting any other session

#### Scenario: Artifact deletion fails
- **WHEN** a local artifact cannot be removed during session deletion
- **THEN** the API SHALL return retryable `ARTIFACT_DELETE_FAILED` and SHALL retain the session and artifact rows so deletion can be retried without an orphaned file

#### Scenario: Invalid API request occurs
- **WHEN** request validation, state conflict, media validation, lookup, or an internal operation fails
- **THEN** the response SHALL use `{"error":{"code","message","retryable"}}` and SHALL NOT expose an exception stack or private metadata

### Requirement: WebSocket events are replayable and non-blocking
The WebSocket endpoint SHALL replay events after a requested sequence, stream new ordered events, send transport heartbeats, isolate slow clients, and signal clients to refresh the authoritative HTTP session snapshot without embedding a second snapshot authority in event payloads.

#### Scenario: Client reconnects
- **WHEN** a known session connects with `after_seq=N`
- **THEN** it SHALL receive each stored event with `seq>N` once, followed by new events without re-executing work, and the client SHALL be able to refresh the current session snapshot

#### Scenario: Client is slow or session is terminal
- **WHEN** a client queue fills or replay reaches a terminal session
- **THEN** only that client SHALL disconnect, or the terminal connection SHALL close normally after replay

### Requirement: Accepted session work has explicit task ownership
The API SHALL retain every accepted non-terminal background operation in a `SessionTaskRegistry`, allow at most one owned task per session stage, observe task failures, and remove completed task references without treating in-memory state as authoritative.

#### Scenario: Accepted work continues after the response
- **WHEN** create or transcript confirmation returns `202 Accepted`
- **THEN** the registry SHALL own the scheduled task until completion and GET/WebSocket clients SHALL observe progress from persisted snapshots/events

#### Scenario: Duplicate work is requested
- **WHEN** the same session already has an owned active task for that stage
- **THEN** the API SHALL reject or reuse the existing ownership without launching duplicate inference or execution

### Requirement: Public payloads are sanitized
All persisted/public event, error, config, artifact, and session payloads SHALL omit or redact absolute paths, secrets, hostnames, PIDs, GPU identifiers, raw selectors, and exception traces.

#### Scenario: Internal exception contains private metadata
- **WHEN** an internal provider or browser exception includes private values
- **THEN** sanitization SHALL occur before event persistence and WebSocket publication, and REST, replay, and live event clients SHALL receive only a controlled message and stable error code

### Requirement: Sandbox pages are deterministic and same origin
FastAPI SHALL provide Search, Help, Product, and Profile pages with fixed test IDs, no external resources, and content sufficient for deterministic verification.

#### Scenario: Sandbox page is loaded
- **WHEN** Playwright visits a registered capability path
- **THEN** the page SHALL load entirely from the exact FastAPI origin and expose the registered verifier elements
