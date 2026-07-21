## Why

Voice2Task currently stops at a schema-valid Browser Task Contract, so reviewers cannot run a complete, visible flow from Chinese text or audio input through a controlled browser action and deterministic verification. This change adds a localhost-only, fixture-capable MVP that demonstrates orchestration and safety without changing model training or claiming internet or ASR generalization.

## What Changes

- Add a typed runtime with explicit session transitions, append-only events, deterministic plan compilation, policy gating, one-time confirmation, isolated Playwright execution, and deterministic verification.
- Add fixture/private-model inference providers and disabled/fixture/allowlisted-HTTP ASR providers while reusing the current V1 contract, unified gold-free prompt, strict parser, and semantic validation.
- Add FastAPI HTTP/WebSocket interfaces, SQLite persistence, public-safe artifacts, deterministic localhost sandbox pages, and one-command production-style local serving.
- Add a React/TypeScript/Vite operation console for input, transcript confirmation, contract/plan inspection, write confirmation, live timeline, verifier evidence, screenshots, and history replay.
- Add a six-scenario controlled fixture benchmark, focused no-lockbox tests, bilingual documentation, screenshots, and a Draft PR evidence surface.
- Close review findings in ordered slices: strict four-stage Extract evidence, recoverable two-stage confirmation, asynchronous `202 Accepted` orchestration, microphone/local-state cleanup, then final no-lockbox validation, delta-spec sync, archive, and stacked Draft integration.
- Keep existing training, dataset, evaluator, historical metric, lockbox, and experiment artifacts unchanged.
- Explicit non-goals: generic chat fine-tuning, skill routing, GUI action-policy learning, SFT/DPO/GRPO or other training, arbitrary/public-web automation, real-ASR benchmarking, production deployment, checkpoint/adapter publication, full-corpus publication, or live-browser/model-quality improvement claims.

## Capabilities

### New Capabilities

- `controlled-browser-runtime`: Typed session, compiler, policy, executor, verifier, persistence, and controlled fixture benchmark behavior.
- `controlled-browser-demo-api`: Local FastAPI, WebSocket, inference/ASR provider, sandbox, artifact, and uniform-error interfaces.
- `controlled-browser-demo-web`: React/Vite UI, explicit mode labels, confirmation flow, event replay, verifier evidence, responsive behavior, and screenshot requirements.

### Modified Capabilities

None. BrowserTaskContract V1, training, data, and evaluation requirements remain unchanged.

## Impact

- New code under `src/voice2task/runtime/`, `apps/api/`, `apps/web/`, `demo/`, `scripts/`, and focused runtime/demo tests.
- New optional Python `demo` dependencies plus a locked local frontend dependency set; existing base dependencies remain unchanged.
- New ignored runtime state under `var/demo/` and new committed controlled benchmark/documentation evidence under `reports/demo-mvp/` and `docs/demo/`.
- Exact implementation base: `38db1244884ddcc7df155a06e342d9e061ff0bcd` from `origin/codex/materialize-manifest-bound-train-only-sft-v1`.
- No lockbox reads, training/GPU work, historical metric rewrites, release, deployment, or merge are authorized by this change.
- This review round explicitly authorizes delta-spec sync and OpenSpec archive only after every review-fix task and the final no-lockbox verification gate pass. It also authorizes a Draft stacked integration against `codex/materialize-manifest-bound-train-only-sft-v1` after archive; those ordered closeout actions are not part of the Extract-only implementation slice.
