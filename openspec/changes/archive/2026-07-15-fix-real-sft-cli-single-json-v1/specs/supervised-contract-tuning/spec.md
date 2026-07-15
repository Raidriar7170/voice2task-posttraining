## MODIFIED Requirements

### Requirement: Return truthful CLI exit status and one JSON result
The training CLI MUST reserve stdout for exactly one final sanitized JSON document. All Python-level stdout emitted by downstream command execution, including model or tokenizer loading, trainer construction, training callbacks, and trainer progress, MUST be streamed to stderr as prefixed diagnostics that cannot be parsed as a second result JSON. Dry-run success, ready preflight, and `training_status=training_completed` MUST exit 0. Skipped-by-config, unavailable, output-policy-blocked, preflight-blocked, and runtime-exception results MUST exit non-zero. Stderr MUST NOT contain a second result JSON.

#### Scenario: Map successful results
- **WHEN** dry-run succeeds, preflight is ready, or training completes
- **THEN** the CLI emits one JSON document and exits 0

#### Scenario: Map non-success results
- **WHEN** training is skipped, unavailable, output-policy-blocked, preflight-blocked, or raises at runtime
- **THEN** the CLI emits one sanitized JSON document and exits non-zero without a competing result document on stderr

#### Scenario: Isolate downstream training progress
- **WHEN** an SFT or DPO backend prints Python objects, progress, or JSON-shaped text to stdout before returning a result
- **THEN** the CLI streams that output to stderr with a non-JSON diagnostic prefix and keeps stdout parseable as exactly one final result JSON

#### Scenario: Restore result stdout after a noisy runtime exception
- **WHEN** a backend writes progress to stdout and then raises at runtime
- **THEN** the CLI restores result stdout, emits exactly one sanitized failure JSON there, exits non-zero, and leaves only prefixed diagnostics on stderr
