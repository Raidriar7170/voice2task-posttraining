## Why

The A100 route-ontology train-split rerun shows that route/task ontology now matches the gold train rows (`search_web` / `search`), but every strict final contract remains schema-invalid because `confirmation_required` is absent. A prior general required-field repair added a contract skeleton and guard metadata, so the next bounded local fix should target the remaining `confirmation_required` emission gap without changing evaluation criteria or treating post-hoc field insertion as model recovery.

## What Changes

- Strengthen the SFT/prediction contract instructions so `confirmation_required` is explicitly called out as a required boolean field with a clear defaulting rule for non-sensitive commands.
- Add or update focused tests that prove the shared prompt/example surface contains `confirmation_required` and that weather/search examples include `"confirmation_required": false`.
- Improve local public-safe diagnostics/evidence so missing `confirmation_required` is surfaced as its own required-field failure count.
- Generate a concise Chinese Human Brief for this local repair phase.
- Do not run A100 training or prediction in this phase; a later prediction-only train-split rerun may evaluate whether the local repair changes private-adapter outputs.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `supervised-contract-tuning`: require SFT/prediction prompt examples and contract instructions to make `confirmation_required` visibly required and boolean-valued.
- `contract-evaluation`: require public-safe diagnostics for train-split recovery evidence to surface missing `confirmation_required` separately from other schema failures when observable.

## Impact

- Affected code is expected around SFT formatting/prompt text, prediction prompt snapshots, schema/failure diagnostics, and focused tests.
- No dependency changes, no private A100 execution, no checkpoint/adapter release, no full-private-corpus publication, no generic chat fine-tuning, no skill routing, no GUI action policy learning, no first-phase GRPO, no production-readiness claim, no held-out generalization claim, and no live-browser benchmark improvement claim.
