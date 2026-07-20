## 1. Foundation and Runtime Contracts

- [x] 1.1 Add bounded demo dependencies, ignored local-state paths, package roots, and one-command Make targets without changing existing CLI defaults.
- [x] 1.2 Write failing tests for strict Pydantic runtime models, public JSON schemas, sanitization, and V1 schema/semantic delegation.
- [x] 1.3 Implement runtime models, enums, public payload sanitization, and compatibility adapters until the model tests pass.
- [x] 1.4 Write failing tests for the explicit state machine, atomic event sequence, restart recovery, and duplicate execution claim.
- [x] 1.5 Implement state/session/storage/event primitives with temporary-SQLite tests passing.

## 2. Providers, Compilation, and Policy

- [x] 2.1 Write failing tests for six exact fixture inference mappings, unsupported fixture input, private no-fallback behavior, strict parser reuse, and one schema-only retry.
- [x] 2.2 Implement fixture/private inference providers and public-safe readiness behavior without loading a private model in tests.
- [x] 2.3 Write failing tests for disabled/fixture/HTTP ASR, transcript confirmation/edit tracking, MIME/size/filename validation, exact endpoint rules, and temporary cleanup.
- [x] 2.4 Implement ASR providers and bounded audio input handling until provider tests pass.
- [x] 2.5 Write failing tests for the static capability registry, deterministic plans, six task outcomes, trusted help alias, slot rejection, plan expiry, and policy reason codes.
- [x] 2.6 Implement capability registry, pure compiler, one-time confirmation, and policy gate until tests pass.

## 3. Controlled Execution and Verification

- [x] 3.1 Add deterministic same-origin Search, Help, Product, and Profile sandbox pages and write verifier fixtures/tests first.
- [x] 3.2 Implement deterministic executable and no-execution verifier checks with immutable failures.
- [x] 3.3 Write failing Playwright tests for four executable scenarios, confirmation-before-mutation, exact-origin egress blocking, screenshots, bounded failures, and context cleanup.
- [x] 3.4 Implement application-scoped Chromium, per-session contexts, guarded actions, artifact metadata, events, and cleanup until executor tests pass.

## 4. API, WebSocket, and Orchestration

- [x] 4.1 Write failing API tests for health/config/schema, text/audio session creation, transcript confirmation, confirmation/rejection, execute/cancel/history/delete, artifacts, and uniform errors.
- [x] 4.2 Implement FastAPI dependency lifecycle, orchestrator, HTTP routes, exception handlers, and same-origin production static serving until API tests pass.
- [x] 4.3 Write failing WebSocket tests for replay after sequence, ordered live events, heartbeat, terminal close, unknown sessions, and slow-client isolation.
- [x] 4.4 Implement the bounded event hub and `/ws/sessions/{session_id}` until replay tests pass.

## 5. React/Vite User Interface

- [x] 5.1 Create the locked React/TypeScript/Vite test setup and write failing component tests for mode labels, input, transcript, contract, plan, confirmation, timeline, verifier, history, errors, and reconnect deduplication.
- [x] 5.2 Implement the accessible responsive operation console and native WebSocket hooks until component and type tests pass.
- [x] 5.3 Build production assets and write Playwright UI tests for Search, Form confirmation, Blocked, zero console errors, and no overflow at 390x844 and 1440x900.
- [x] 5.4 Fix UI/E2E failures and preserve fixture and non-claim labels in every tested viewport.

## 6. Benchmark, Documentation, and Evidence

- [x] 6.1 Write benchmark expectation tests, then implement the temporary-app six-scenario runner and JSON/Markdown outputs with controlled-fixture claim flags.
- [x] 6.2 Add demo README, architecture, bilingual root README entry, run commands, limitations, and reproducible public-safe screenshot capture.
- [x] 6.3 Generate the six-scenario benchmark report and four fixture-safe desktop/mobile screenshots without committing traces, audio, caches, or runtime state.
- [x] 6.4 Update the Chinese Human Brief from proposed to ready-for-review using OpenSpec, diff, verification, evidence, risks, and exact non-claims.

## 7. Focused Validation and Draft Publication

- [x] 7.1 Run all new runtime/API/executor/E2E tests plus existing V1 schema/formatting compatibility tests; do not collect lockbox or global truth-surface tests.
- [x] 7.2 Run frontend tests, TypeScript check, production build, Ruff, focused strict mypy, OpenSpec strict validation, and `git diff --check`.
- [x] 7.3 Run existing public dataset validation, schema-metric fixture checks, and DPO pair validation read-only or into a temporary directory; confirm no tracked data, prediction, metric, or lockbox artifact changed.
- [x] 7.4 Run a targeted public-leak/private-path scan over every new public artifact and inspect ignored/untracked files for models, adapters, audio, logs, caches, browser traces, or absolute paths.
- [x] 7.5 Perform a structured read-only diff/acceptance self-review, fix every Must Fix through a new failing test, and rerun the complete focused verification bundle.
- [x] 7.6 Mark all OpenSpec implementation tasks complete while leaving the change active and unarchived.
- [x] 7.7 Commit scoped changes, push `codex/voice2task-controlled-browser-demo-mvp-v1`, create a Draft PR against `codex/materialize-manifest-bound-train-only-sft-v1`, and verify Draft/Open/unmerged state.

## 8. Review Fixes

- [x] 8.1 Review fix #1: preserve strict independent action-output and fresh DOM-snapshot evidence; enforce ordered `EXTRACT_ACTION_OUTPUT_MISSING`, `EXTRACT_DOM_SNAPSHOT_MISSING`, `EXTRACT_EVIDENCE_MISMATCH`, and `EXTRACT_EXPECTED_VALUE_MISMATCH` codes against registry expected `¥199.00`; preserve `VERIFICATION_FAILED` for later non-Extract failures; prove executor independence plus model/SQLite/API/benchmark serialization; and rerun the focused tests, Ruff, strict mypy, OpenSpec strict validation, and diff checks.
- [x] 8.2a Review fix #2 backend: replace create/transcript raw-token responses with a bound, rotating confirmation-challenge endpoint; preserve separate confirm and execute requests; and test binding, expiry, rejection, duplicate, hash-only persistence, and recoverable pre-claim execution safety.
- [x] 8.2b Review fix #2 frontend: recover only a matching pending challenge from `sessionStorage`, preserve the separate confirm/execute UI flow, and test refresh/expiry/rejection/duplicate safety without `localStorage`.
- [x] 8.3a Review fix #3 backend: make accepted text/audio/transcript work return `202 Accepted`, retain and observe one owned task per session in `SessionTaskRegistry`, persist controlled background failures, and test task lifecycle, duplicate ownership, disconnect independence, cancellation, shutdown, and reconnect/replay behavior.
- [x] 8.3b Review fix #3 frontend: refresh authoritative session snapshots after WebSocket state signals, refetch when replay is newer than the concurrently loaded snapshot, and test reconnect/history snapshot behavior.
- [x] 8.4 Review fix #4: stop/clear microphone resources and revoke object URLs on every exit, remove server artifacts/temp audio and client challenge state on deletion, add precise local-storage disclosure, and test cleanup paths.
- [x] 8.4b Final Reviewer cleanup follow-up: sanitize event strings before SQLite/REST/WebSocket exposure, generation-guard pending microphone acquisition, transfer staged-audio cleanup ownership cancellation-safely, and keep session rows retryable when artifact unlink fails; cover each root cause with focused regressions.
- [x] 8.5 Run the final focused no-lockbox backend/frontend/E2E verification bundle, Ruff, strict mypy, build/type checks, public leak scan, OpenSpec strict validation, and `git diff --check`; confirm training, dataset, historical metric, prediction, and lockbox surfaces are unchanged.
- [x] 8.6 Sync all three delta specs to main specs and archive `add-controlled-browser-agent-demo-mvp-v1` only after 8.2-8.5 are complete and the final gate is green.
- [x] 8.7 Prepare and verify the scoped result as a Draft stacked integration against `codex/materialize-manifest-bound-train-only-sft-v1`; keep it Draft/Open/unmerged and do not release, deploy, train, or merge.
