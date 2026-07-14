## 1. Contract and Test Harness

- [x] 1.1 Add focused failing output-policy tests for missing/relative roots, relative/equal/escaping candidates, parent/final symlinks, non-empty targets, valid new child, tracked paths, and pre-load drift
- [x] 1.2 Add focused failing CLI tests for one-JSON stdout and zero/non-zero exit mapping across dry-run, preflight, completed, skipped, unavailable, output-blocked, preflight-blocked, and runtime-exception states
- [x] 1.3 Add focused failing preflight tests for config, dependency, GPU, model, dataset, objective, Git, and output ready/blocked outcomes without network, GPU, or real model loading

## 2. Shared Preflight and Output Policy

- [x] 2.1 Implement canonical fail-closed output policy with stable sanitized blockers and a no-write unsafe path contract
- [x] 2.2 Implement schema-versioned shared `run_sft_preflight` covering Git, config, dependencies, GPU, dataset, objective, local model, and output facts
- [x] 2.3 Reuse the shared preflight and repeat output policy immediately before tokenizer/model loading to close preflight-to-load drift

## 3. CLI and Runtime Wiring

- [x] 3.1 Add `sft-preflight` arguments, one-JSON rendering, sanitized runtime failure handling, and truthful exit-code mapping
- [x] 3.2 Wire local-only Qwen2.5-7B BF16/low-memory loading, EOS pad fallback, gradient checkpointing/use-cache policy, bounded TrainingArguments, and metadata
- [x] 3.3 Enforce smoke postconditions and `SMOKE_COMPLETED` without full-weight, prediction, evaluation, or clean-readiness claims
- [x] 3.4 Add disabled public-safe `configs/sft-a100-smoke.example.json` and verify any private config remains ignored and untracked

## 4. Verification and Gated Execution

- [x] 4.1 Run focused RED/GREEN tests and the full `PYTHONPATH=src pytest -q` suite
  - Reviewer module: `95 passed`; existing A100 module: `52 passed`; combined training-focused regression: `176 passed`; CLI matrix: `12 passed`.
  - Full suite: `1353 passed, 4 failed`. The four failures are preserved lifecycle/frozen-boundary guards caused solely by this active OpenSpec change; they were not bypassed.
- [x] 4.2 Run `ruff`, targeted `mypy`, strict OpenSpec validation, truth-surface check, public-leak/ignore checks, and `git diff --check`
  - `ruff`, strict OpenSpec validation (`16 passed, 0 failed`), public-leak/ignore checks, and `git diff --check` passed.
  - Targeted `mypy` reports only the two pre-existing imported-file diagnostics; the isolated touched-file result matches the four-error origin/main baseline.
  - Truth-surface check remains non-green only because `enable-private-a100-sft-smoke-v1` is correctly active.
- [x] 4.3 Run private `sft-preflight` only if the authorized ignored config exists; run exactly one real one-step smoke only after `ready=true` on one explicitly selected idle A100, otherwise record the exact blocker and stop
  - The ignored private config is absent. On a clean committed HEAD, actual CLI preflight exited `1` with one JSON document, empty stderr, and the sole blocker `CONFIG_FILE_MISSING`.
  - A read-only occupancy probe against the existing authorized A100 alias timed out three times, so no GPU or local-model facts were obtained and no training followed.
- [x] 4.4 Update the Human Brief with final verification and execution state while preserving all clean-evaluation blockers

## 5. Reviewer Hardening

- [x] 5.1 Return one public preflight report plus an immutable private execution context; bind exact rows and rehash config, manifest, SFT, and model inventory before loading
- [x] 5.2 Tighten canonical formal-data, A100/Qwen geometry, private-config, output claim/recheck, and DPO output-bypass contracts
- [x] 5.3 Tighten public-safe exception handling and smoke postconditions for finite loss, exact rows, adapter config/weights, and whole-run full-weight scanning
- [x] 5.4 Add direct bypass/regression coverage and update OpenSpec/Human Brief truth surfaces without bypassing active-change lifecycle guards
  - Reviewer module: `95 passed`; existing A100 module: `52 passed`; combined training-focused regression: `176 passed`; CLI boundary: `12 passed`.
  - Second-review-ready final rerun: full pytest `1353 passed, 4 failed` (only preserved active-change lifecycle/frozen-boundary guards); Ruff passed; strict OpenSpec `16 passed, 0 failed`; `git diff --check` passed; targeted Mypy contains zero touched-file diagnostics and only two pre-existing imported-module errors.

## 6. Final Reviewer Closure

- [x] 6.1 Make real SFT invoke the safe shared core before all legacy reads, return a minimal no-write blocked result, and build ready metadata only from the immutable context
- [x] 6.2 Bind the exact model facts returned by the validated probe, derive DPO repository identity from the supplied manifest checkout, and pass that identity explicitly to the runner
- [x] 6.3 Validate `max_seq_length` as a non-boolean integer in `1..4096`, whitelist public config facts, and convert every unexpected shared-core exception to `PREFLIGHT_INTERNAL_ERROR`
- [x] 6.4 Add direct regressions for legacy-read bypass, model-fact mutation, unrelated DPO cwd/fail-closed checkout, malformed private config values, and both public/real preflight exception paths
  - Fresh focused result: reviewer module `108 passed`; reviewer + existing A100 + formatting regression `189 passed`.
- [x] 6.5 Run final Ruff, targeted Mypy, strict OpenSpec validation, and `git diff --check`; then update the Human Brief to final-review-ready without rerunning the repository-wide suite
  - Ruff passed; strict OpenSpec validation passed `16/16`; `git diff --check` passed.
  - The exact targeted Mypy command reports only the two pre-existing imported-module diagnostics in `slot_error_analysis.py:574` and `copy_backed_shadow_interface.py:357`; neither touched training file has a diagnostic.
  - Per final-review scope, the repository-wide pytest suite was not rerun; the prior second-review result remains recorded separately and is not presented as fresh third-review evidence.

## 7. Exact Integer Budget Closure

- [x] 7.1 Add parameterized RED regressions for JSON booleans and floats in `max_train_rows`, `max_steps`, per-device batch size, and gradient accumulation, plus unsafe `seed` and `logging_steps` encodings
- [x] 7.2 Require exact non-boolean integers for all smoke budget fields, an integer `seed`, and positive integer `logging_steps`; malformed row limits select zero rows
- [x] 7.3 Run the final focused and static verification without full-suite, GPU, commit, or archive actions
  - Fresh reviewer module: `123 passed`; final Reviewer combined regression: `214 passed`; final verdict `Pass` with no Must Fix or Should Fix.
  - Ruff passed; strict OpenSpec validation passed `16/16`; `git diff --check` passed.
  - The exact targeted Mypy command still reports only the two pre-existing imported-module diagnostics; neither touched training file has a diagnostic.

## 8. Independent Pre-Commit Verification

- [x] 8.1 Refresh `origin/main` and confirm the bounded change still starts at `4c99e8d6cf1fe2782b2760e36437ff5fae164dff`
- [x] 8.2 Run the repository-wide suite after the exact-integer closure
  - Fresh result: `1381 passed, 4 failed`; the four failures are only the preserved active-change lifecycle/frozen-boundary guards.
- [x] 8.3 Run all requested static and truth-surface commands
  - Ruff, strict OpenSpec validation (`16/16`), and `git diff --check` passed.
  - Truth-surface check exits `1` only because this bounded change remains active.
  - Exact targeted Mypy exits `1` only for the two pre-existing imported-module diagnostics; neither touched training file has a diagnostic.
- [x] 8.4 Exercise the real execution gate from a clean committed HEAD and stop fail-closed
  - Shared CLI preflight: exit `1`, exactly one stdout JSON document, empty stderr, sole blocker `CONFIG_FILE_MISSING`.
  - Authorized A100 alias: three read-only occupancy probes timed out; no remote writes, model-path search, training, prediction, or evaluation occurred.

## 9. Changes-Requested Hardening

- [x] 9.1 Replace regex-based public training metadata with a strict allowlist result builder and prove arbitrary absolute private paths never reach CLI stdout
- [x] 9.2 Bind output-root and parent filesystem identities, require the parent to pre-exist, and claim the leaf descriptor-relatively without pathname cleanup after uncertainty
- [x] 9.3 Add free-memory and zero-compute-process GPU readiness facts and repeat the same occupancy probe before model-weight loading
- [x] 9.4 Validate assistant-only labels against the tokenizer offset-derived assistant token region and reject any prompt-label leakage
- [x] 9.5 Record before/after adapter-state digests, changed finite adapter tensor counts, and SHA-256 adapter-file inventory as required smoke postconditions
- [x] 9.6 Add no-GPU/no-model RED/GREEN regressions, update the Human Brief, and run focused verification without training, archive, commit, push, or PR actions
  - RED: `17 failed` in the new review-hardening module before production changes.
  - GREEN: combined focused suite `200 passed`; focused Ruff passed; strict change validation passed.
  - Targeted Mypy reports only the two pre-existing imported-module diagnostics and no touched-file diagnostic.
- [x] 9.7 Record the user-authorized output-claim threat-model clarification: checkpoint-observable races remain defended, while malicious same-UID namespace rename inside the final identity-checkpoint-to-`mkdirat` boundary is a deployment precondition rather than a syscall-atomicity claim
