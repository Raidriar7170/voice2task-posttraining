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
- **THEN** the API SHALL return `ASR_PROVIDER_UNAVAILABLE` while keeping text input available

#### Scenario: Audio validation or transcription completes
- **WHEN** valid bounded audio is handled by fixture or explicitly configured HTTP ASR
- **THEN** the temporary input SHALL be deleted and the session SHALL stop at `TRANSCRIPT_READY` until the user confirms or edits the transcript

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
- **THEN** the API SHALL return a session ID and asynchronously prepare a validated contract and policy outcome

#### Scenario: Session is deleted
- **WHEN** a terminal inactive session is deleted
- **THEN** its database rows and local artifacts SHALL be removed without affecting any other session

#### Scenario: Invalid API request occurs
- **WHEN** request validation, state conflict, media validation, lookup, or an internal operation fails
- **THEN** the response SHALL use `{"error":{"code","message","retryable"}}` and SHALL NOT expose an exception stack or private metadata

### Requirement: WebSocket events are replayable and non-blocking
The WebSocket endpoint SHALL replay events after a requested sequence, stream new ordered events, send transport heartbeats, and isolate slow clients.

#### Scenario: Client reconnects
- **WHEN** a known session connects with `after_seq=N`
- **THEN** it SHALL receive each stored event with `seq>N` once, followed by new events without re-executing work

#### Scenario: Client is slow or session is terminal
- **WHEN** a client queue fills or replay reaches a terminal session
- **THEN** only that client SHALL disconnect, or the terminal connection SHALL close normally after replay

### Requirement: Public payloads are sanitized
All persisted/public event, error, config, artifact, and session payloads SHALL omit or redact absolute paths, secrets, hostnames, PIDs, GPU identifiers, raw selectors, and exception traces.

#### Scenario: Internal exception contains private metadata
- **WHEN** an internal provider or browser exception includes private values
- **THEN** the client and persisted event SHALL receive only a controlled message and stable error code

### Requirement: Sandbox pages are deterministic and same origin
FastAPI SHALL provide Search, Help, Product, and Profile pages with fixed test IDs, no external resources, and content sufficient for deterministic verification.

#### Scenario: Sandbox page is loaded
- **WHEN** Playwright visits a registered capability path
- **THEN** the page SHALL load entirely from the exact FastAPI origin and expose the registered verifier elements
