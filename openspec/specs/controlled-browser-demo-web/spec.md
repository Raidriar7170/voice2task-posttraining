# controlled-browser-demo-web Specification

## Purpose
Define the visible provenance, recoverable confirmation, replayable evidence, microphone cleanup, retention disclosure, accessibility, and responsive behavior of the controlled demo web console.

## Requirements

### Requirement: Runtime modes and input provenance are always visible
The web application SHALL display inference, ASR, and execution modes in the header and SHALL never hide fixture provenance.

#### Scenario: Default demo loads
- **WHEN** public configuration reports fixture inference and disabled ASR
- **THEN** visible labels SHALL state `Fixture Inference`, `ASR Disabled`, and local sandbox execution

### Requirement: Users can supply text or bounded audio input
The input panel SHALL support text, MediaRecorder audio, audio upload, profile email, and the six recommended examples, with transcript review for audio.

#### Scenario: Audio transcript is edited
- **WHEN** an audio session reaches `TRANSCRIPT_READY` and the user edits then confirms the transcript
- **THEN** the UI SHALL submit the edited text and display that an edit was recorded before inference continues

### Requirement: Contract, plan, policy, and confirmation are inspectable
The web application SHALL show the validated contract fields, raw JSON, plan actions/postconditions, policy outcome, and a concrete confirmation dialog before any form-field mutation.

#### Scenario: Form Fill requires approval
- **WHEN** a form plan enters `AWAITING_CONFIRMATION`
- **THEN** the dialog SHALL list the local action, state that no real website is accessed, and provide explicit Approve and Reject controls

#### Scenario: Approval or rejection is selected
- **WHEN** the user approves
- **THEN** the UI SHALL submit only the bound confirmation challenge and render the returned `CONFIRMED` snapshot with a separate explicit execution button for the same plan version; it SHALL NOT auto-execute, and rejection SHALL cancel without execution

#### Scenario: Confirmation page refreshes
- **WHEN** a same-tab refresh occurs while a challenge is pending
- **THEN** the UI SHALL recover the challenge from `sessionStorage`, refresh the authoritative session snapshot, and retain it only when session, plan version, expiry, and `AWAITING_CONFIRMATION` still match; it SHALL never use `localStorage`

### Requirement: Timeline, verifier, screenshots, and history are replayable
The web application SHALL render ordered WebSocket events, elapsed time, controlled failure codes, verification checks, screenshot evidence, and recent session history without replaying browser actions.

#### Scenario: WebSocket reconnects or history is opened
- **WHEN** the connection drops or a prior session is selected
- **THEN** the UI SHALL request events after its highest sequence, deduplicate them, refresh the authoritative HTTP session snapshot after state-bearing events, and render history only

### Requirement: Microphone and local evidence cleanup are explicit
The web application SHALL stop every MediaRecorder track and clear stream references on stop, error, unmount, and recording replacement; SHALL revoke temporary object URLs; SHALL remove the matching confirmation challenge after terminal state or deletion; and SHALL disclose local retention precisely.

#### Scenario: Recording ends or the component exits
- **WHEN** recording stops, fails, is replaced, switches input mode, or its component unmounts, including while `getUserMedia` is still pending
- **THEN** an acquisition generation guard SHALL reject the stale result, all acquired tracks SHALL be stopped, stream references SHALL be cleared, created object URLs SHALL be revoked, and repeated pending clicks SHALL NOT create concurrent acquisitions

#### Scenario: Session is deleted or storage disclosure is read
- **WHEN** the user deletes a terminal session or reads the input/history copy
- **THEN** the UI SHALL remove its matching `sessionStorage` challenge and state that raw audio is temporary, session metadata/screenshots remain local until deletion, and `localStorage` is not used

### Requirement: The UI is professional, accessible, and responsive
The application SHALL use bundled assets, system fonts, semantic status tokens, keyboard-visible focus, human-readable errors, reduced motion, and layouts without horizontal overflow at 390 by 844 and 1440 by 900.

#### Scenario: Automated UI acceptance runs
- **WHEN** production assets are served by FastAPI at desktop and mobile viewports
- **THEN** Search, Form confirmation, and Blocked flows SHALL complete with zero console errors and no horizontal scrolling

### Requirement: Public copy preserves demonstration boundaries
The UI and documentation SHALL position the system only as a verifiable controlled browser-agent demo for Chinese voice input.

#### Scenario: Reviewer reads the public surfaces
- **WHEN** the header, README, benchmark, screenshots, or Human Brief is inspected
- **THEN** it SHALL NOT claim generic-agent capability, public-web generalization, real-ASR benchmarking, production readiness, deployment, or model-quality improvement
