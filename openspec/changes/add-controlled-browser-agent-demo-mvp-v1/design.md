## Context

Voice2Task currently owns the Chinese transcript-to-BrowserTaskContract boundary and has a strict V1 schema, a unified gold-free prediction prompt, whole-object parsing, semantic validation, and private PEFT inference code. It intentionally has no browser controller. This change adds a separate demo runtime on the stable training-infrastructure base `38db1244884ddcc7df155a06e342d9e061ff0bcd` while preserving every training, dataset, evaluator, lockbox, and historical metric surface.

The demo must work without a GPU or private service, make fixture provenance visible, execute only deterministic localhost pages, and expose enough state and evidence for a reviewer to understand why an action ran or was blocked. It is a local demonstration, not a generic browser agent or deployment architecture.

## Goals / Non-Goals

**Goals:**

- Run the six approved text scenarios end to end through inference, contract validation, deterministic compilation, policy, explicit execution, and verification.
- Provide pluggable but fail-closed private PEFT and ASR adapters without requiring either for the default demo.
- Make every lifecycle transition, confirmation, action, screenshot, verifier result, and failure visible through persisted events and a reconnectable WebSocket.
- Guarantee that model/client inputs cannot inject selectors, URLs, scripts, code, or unsupported actions into Playwright.
- Keep the local product easy to start, test, review, and demonstrate from one repository.

**Non-Goals:**

- Arbitrary or public-web automation, login, payment, download/upload, production security, multi-user authentication, distributed workers, or cloud deployment.
- Training, prediction experiments, lockbox access, model-quality measurement, natural-ASR measurement, internet generalization, checkpoint/adapter publication, or historical metric changes.
- Posthoc contract repair, semantic-equivalence scoring, LLM judging, model-authored selectors/actions, or silent fixture fallback.

## Decisions

### Preserve BrowserTaskContract V1 and add a strict runtime adapter

The existing dataclass in `voice2task.schemas` remains authoritative. Runtime API models use Pydantic v2 with `extra="forbid"`, then delegate schema and semantic checks to `validate_contract_status`/`as_contract`. This provides OpenAPI/JSON Schema without modifying training targets or maintaining an independent semantic contract.

Alternative rejected: converting the existing training schema to Pydantic. That would create a large compatibility change unrelated to the demo.

### Persist an explicit state machine and append-only event log

`SessionStatus` has a closed transition table. SQLite stores session snapshots, the last event sequence, confirmation state, execution claim, verification, and artifact metadata. A status change and its event append occur in one `BEGIN IMMEDIATE` transaction. The session row owns `last_event_seq`; `(session_id, seq)` is unique.

Only an atomic `claim_execution` transition can enter EXECUTING, so retrying HTTP requests cannot repeat browser actions. In-flight sessions are marked `FAILED/SERVER_RESTART_INTERRUPTED` at startup; plans waiting for confirmation or execution remain resumable. No action is automatically replayed.

Alternative rejected: in-memory-only state, because it cannot support history/replay or prove duplicate prevention across requests.

### Separate providers, compiler, policy, executor, and verifier

`Voice2TaskInferenceProvider` emits a validated contract result; `ASRProvider` emits a transcript result. The compiler is a pure function of the validated contract and persisted `SessionContext`, producing only typed capability/locator/value-source actions. A static registry owns actual paths and selectors. Policy evaluates the plan and capability classification before an executor may claim it. The verifier reads deterministic page state and executor evidence; it never changes a failure to success.

Fixture inference matches only six exact utterances. Private inference lazily loads one locally configured model/adapter, uses local-only model loading and greedy decoding, retries only one schema-invalid generation, and never falls back to fixtures. HTTP ASR uses one explicitly configured endpoint, no redirects, bounded input, exact MIME validation, and sanitized typed output.

Alternative rejected: model-generated Playwright plans or a general agent framework, because neither is necessary and both would weaken the safety boundary.

### Make plan metadata deterministic and confirmation separate

The orchestrator persists session ID, plan version, and plan issued-at in `SessionContext`. The compiler hashes canonical contract/context/registry inputs for `plan_id` and derives expiry from issued-at, so recompiling the same inputs is stable. Confirmation is a separate random nonce; only its hash is stored, it is bound to session/plan/version, expires after five minutes, and is consumed atomically once.

Read-only plans remain `PLAN_READY` until the user clicks Execute. Write plans enter `AWAITING_CONFIRMATION`; the UI approval performs confirm followed by execute, while rejection enters CANCELLED.

### Restrict Playwright at both plan and network layers

One application-scoped headless Chromium is shared, but each execution receives a fresh context that is closed in `finally`. The executor resolves a trusted capability path against the exact FastAPI sandbox origin and aborts every other request. WebSocket routes, downloads, file choosers, and popups are blocked. It does not call `evaluate`, persist storage state, or run more than five actions.

Screenshots receive random IDs and live only under ignored `var/demo/artifacts`; the database and API expose a relative artifact reference, never a host path. Committed documentation screenshots are regenerated only from public fixture values.

### Use a single-process async orchestration model

FastAPI owns SQLite, provider instances, Chromium, a bounded per-client event hub, and background session tasks. The database is authoritative; in-memory locks optimize single-process concurrency but do not replace transactional guards. WebSocket replay first reads `seq > after_seq`, then subscribes to a bounded queue; heartbeats are transport messages, not persisted events.

Alternative rejected: Redis/Celery or a multi-agent runtime, which adds deployment complexity without improving this local MVP.

### Use a same-origin local web application

Vite development proxies `/api`, `/ws`, and `/sandbox` to FastAPI. The production-style demo builds static assets and lets FastAPI serve `apps/web/dist` after registering API and sandbox routes. The four sandbox pages use deterministic same-origin HTML; Search uses a normal GET form and server-rendered results, avoiding page-side network code.

The React UI uses local component state and native WebSocket. It reconnects with the highest observed sequence, deduplicates events, and never performs business-policy decisions. The visual system uses bundled assets, system fonts, semantic tokens, visible focus, reduced motion, and responsive single-column behavior at 390px.

### Treat benchmark results as orchestration evidence only

The benchmark starts a temporary local application with fixture inference and SQLite, drives all six scenarios through the real HTTP/orchestrator/executor path, and reports contract, plan/policy, execution, confirmation, verifier, external-navigation, unsafe-action, and latency fields. Its metadata explicitly sets all model-quality, real-ASR, and internet-generalization claims to false.

## Risks / Trade-offs

- [Private PEFT code can be expensive or unavailable] -> load lazily once, expose readiness without paths, test with injected fakes, and never silently use fixture output.
- [Cancellation cannot terminate a blocking model thread instantly] -> record cancellation, discard late results, and prohibit later stages or actions; executor cancellation remains cooperative between bounded actions.
- [SQLite and in-memory event queues are single-process] -> document one Uvicorn worker as the supported MVP topology and rely on database replay for reconnects.
- [User-entered data can appear in local screenshots] -> keep runtime artifacts ignored/local, commit only fixture screenshots, and sanitize all metadata/error payloads.
- [A stale plan or duplicated HTTP request could mutate twice] -> plan expiry, version binding, one-time confirmation, and atomic execution claim all fail closed.
- [A browser feature may attempt unexpected egress] -> exact-origin request routing plus WebSocket, popup, download, and file-chooser blocks; tests attempt egress and verify abort before network access.
- [OpenSpec active state conflicts with historical zero-active truth checks] -> do not weaken historical truth guards; use focused no-lockbox validation and leave this authorized change complete/active for Draft review.

## Migration Plan

1. Add optional demo dependencies, ignored local-state paths, and isolated runtime/API/web modules without changing current CLI defaults.
2. Build and verify fixture mode, then generate controlled reports and screenshots.
3. Publish a Draft PR against `codex/materialize-manifest-bound-train-only-sft-v1`; existing users and CLIs remain unchanged unless they install `[demo]` and run a demo command.
4. Rollback is deletion/revert of the new demo change; no database migration or existing artifact rewrite is required.

## Open Questions

None. The approved plan fixes the provider modes, local-only capability set, API behavior, evidence boundary, and integration target.
