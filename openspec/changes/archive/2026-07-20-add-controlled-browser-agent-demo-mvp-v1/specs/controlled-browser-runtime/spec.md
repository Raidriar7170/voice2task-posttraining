## ADDED Requirements

### Requirement: Strict runtime models preserve the V1 contract boundary
The runtime SHALL expose strict Pydantic schemas for sessions, actions, plans, policy results, verification, and events while treating the existing BrowserTaskContract V1 schema and semantic validator as authoritative.

#### Scenario: Contract validation succeeds
- **WHEN** an inference provider returns all eight valid V1 fields with valid task semantics
- **THEN** the runtime SHALL preserve the canonical contract and report schema and semantic validity

#### Scenario: Unknown runtime field is supplied
- **WHEN** a client or provider supplies an extra action, plan, or public API model field
- **THEN** validation SHALL fail closed and SHALL NOT start execution

### Requirement: Session transitions and events are explicit and durable
The runtime SHALL enforce the declared session transition table, append strictly increasing events, and atomically persist a transition with its event.

#### Scenario: Valid transition
- **WHEN** a session advances through a permitted state edge
- **THEN** its stored status and one new event SHALL commit together with the next sequence number

#### Scenario: Invalid transition
- **WHEN** a caller requests an edge not present in the transition table
- **THEN** the runtime SHALL reject it without changing state or appending a success event

#### Scenario: Server restarts during execution
- **WHEN** startup finds accepted input or a session in a transient transcription, inference, compilation, execution, or verification state
- **THEN** the runtime SHALL mark it failed with `SERVER_RESTART_INTERRUPTED` and SHALL NOT replay any action

#### Scenario: Graceful shutdown reaches an already durable recovery boundary
- **WHEN** shutdown cancels and awaits a still-owned task after that task has persisted audio `TRANSCRIPT_READY`, `PLAN_READY`, `AWAITING_CONFIRMATION`, or `CONFIRMED`
- **THEN** the runtime SHALL preserve that stable state for explicit user resumption instead of replacing it with a shutdown failure

### Requirement: Plans are deterministic and capability bound
The compiler SHALL map a validated contract and persisted SessionContext to a stable plan containing only reviewed capability, locator, value-source, timeout, and postcondition identifiers.

#### Scenario: Search contract compiles
- **WHEN** the contract is `search/search_web` with one non-empty query slot
- **THEN** the compiler SHALL emit navigate, fill, and click actions for `demo_search` without a selector or URL field

#### Scenario: Help navigation compiles
- **WHEN** the contract is `navigate/open_url` with the trusted help alias
- **THEN** the compiler SHALL map it to `demo_help` and SHALL discard the model-provided URL value from the action plan

#### Scenario: Unknown slot or alias is supplied
- **WHEN** a contract contains a slot outside its task allowlist, an empty required value, or an unknown capability alias
- **THEN** compilation SHALL fail closed with no executable actions

#### Scenario: Identical inputs are recompiled
- **WHEN** the same canonical contract, SessionContext, plan version, issued-at, and registry version are compiled again
- **THEN** the plan identifier, actions, postconditions, and expiry SHALL be identical

### Requirement: Policy blocks unsafe and unconfirmed execution
The policy gate SHALL allow only the four localhost demo capabilities and SHALL require one valid confirmation before the profile field can change.

#### Scenario: Read-only plan is allowed
- **WHEN** a valid non-expired Search, Navigate, or Extract plan is evaluated
- **THEN** policy SHALL allow it without confirmation but execution SHALL still require an explicit execute request

#### Scenario: Form fill lacks confirmation
- **WHEN** a `demo_profile_form` plan has not consumed its bound confirmation
- **THEN** policy and executor SHALL prevent all actions from running

#### Scenario: Payment or forbidden target is requested
- **WHEN** a blocked payment contract, non-allowlisted URL, private address, forbidden scheme, login, upload, download, or script action reaches policy
- **THEN** policy SHALL return a stable reason code and no browser context SHALL be created

### Requirement: Confirmation and execution are at-most-once
The runtime SHALL bind a confirmation challenge to one session, plan ID, plan version, and five-minute expiry, SHALL consume it before execution, and SHALL atomically claim at most one execution.

#### Scenario: Confirmation is approved once
- **WHEN** the correct unexpired token and plan version are submitted from `AWAITING_CONFIRMATION`
- **THEN** the token SHALL be consumed and the session SHALL enter `CONFIRMED`

#### Scenario: Confirmation succeeds without executing
- **WHEN** the bound challenge is consumed successfully
- **THEN** the response SHALL expose `CONFIRMED` and no browser action SHALL run until a separate execute request claims the same plan version

#### Scenario: Confirmation or execute is repeated
- **WHEN** the same token or execute request is submitted after consumption or execution claim
- **THEN** the runtime SHALL return a conflict and SHALL NOT repeat a browser action

### Requirement: Playwright execution is isolated and localhost only
The executor SHALL use a fresh BrowserContext per session, exact-origin request routing, bounded actions and timeouts, and guaranteed context cleanup.

#### Scenario: Registered action executes
- **WHEN** an allowed plan is explicitly executed
- **THEN** each action SHALL emit start/completion events, save a random-ID screenshot, and close the context after verification

#### Scenario: External egress is attempted
- **WHEN** a page or test attempts HTTP, HTTPS, or WebSocket access outside the exact sandbox origin
- **THEN** the request SHALL be aborted before egress and the execution SHALL fail closed

### Requirement: Verification is deterministic and immutable
The verifier SHALL compare deterministic URL, heading, field, result, extraction, and no-execution postconditions without an LLM judge or success repair.

#### Scenario: Executable scenario matches postconditions
- **WHEN** Search, Navigate, Extract, or Form Fill produces the expected local page state
- **THEN** every check SHALL pass and the session SHALL enter `COMPLETED`

#### Scenario: Postcondition fails
- **WHEN** an observed value differs from the expected deterministic value
- **THEN** the verification SHALL remain failed and the session SHALL enter `FAILED`

#### Scenario: Blocked or clarify contract terminates
- **WHEN** compiler/policy returns blocked or clarification required
- **THEN** verification SHALL record `browser_context_created=false` and `action_count=0`

### Requirement: Execution evidence preserves independent observation sources
The runtime SHALL model execution evidence as strict, separate action-output and fresh DOM-snapshot mappings. An action SHALL write only its direct output, the post-action DOM collector SHALL create a new snapshot without receiving or mutating action outputs, and SQLite SHALL preserve the exact evidence JSON after close/reopen.

#### Scenario: Extract output matches the fresh DOM snapshot
- **WHEN** the Extract action returns a non-empty product price and a fresh post-action DOM read independently observes the same price
- **THEN** verification SHALL compare `action_outputs["product_price"]` with `dom_snapshot["product_price"]`, compare the DOM value with registry expected `¥199.00`, and may pass those checks

#### Scenario: Extract action output is missing
- **WHEN** `action_outputs["product_price"]` is absent or empty regardless of later evidence
- **THEN** verification SHALL fail with `EXTRACT_ACTION_OUTPUT_MISSING`

#### Scenario: Extract DOM snapshot is missing
- **WHEN** action output is non-empty but `dom_snapshot["product_price"]` is absent or empty
- **THEN** verification SHALL fail with `EXTRACT_DOM_SNAPSHOT_MISSING`

#### Scenario: Extract output differs from the fresh DOM snapshot
- **WHEN** the Extract action output and fresh post-action DOM observation differ
- **THEN** verification SHALL remain failed with `EXTRACT_EVIDENCE_MISMATCH` even if either individual source is non-empty

#### Scenario: Matching Extract evidence differs from registry expected
- **WHEN** both sources are non-empty and equal but the DOM value is not registry expected `¥199.00`
- **THEN** verification SHALL remain failed with `EXTRACT_EXPECTED_VALUE_MISMATCH`

#### Scenario: Extract evidence passes but another check fails
- **WHEN** both sources are non-empty and equal to registry expected `¥199.00` but URL or another non-Extract postcondition fails
- **THEN** verification SHALL fail with `VERIFICATION_FAILED`

#### Scenario: Non-extract postconditions are verified
- **WHEN** Search, Navigate, or Form Fill verification reads page state
- **THEN** it SHALL read the fresh DOM snapshot and SHALL NOT treat an action output as observed DOM state

### Requirement: Controlled benchmark has explicit claim boundaries
The benchmark SHALL run exactly the six approved fixture scenarios, serialize only fixture-safe Extract action/DOM/registry evidence needed to audit the verifier, and publish aggregate orchestration evidence with all model-quality, real-ASR, and internet-generalization claims false.

#### Scenario: Fixture benchmark passes
- **WHEN** all approved scenarios run through a local application
- **THEN** 6/6 SHALL reach expected terminal states, 4/4 executable scenarios SHALL verify, and unsafe, external, blocked, clarify, and unconfirmed execution counts SHALL be zero
