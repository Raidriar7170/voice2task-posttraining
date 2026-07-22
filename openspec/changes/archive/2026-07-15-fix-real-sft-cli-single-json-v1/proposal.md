## Why

The first authorized real one-step SFT process exposed that Transformers/TRL callback output can reach CLI stdout before the final result, so a successful process can violate the existing one-JSON protocol even though the final metadata is valid. The CLI boundary must own stdout and route dependency progress elsewhere before any additional real smoke can be considered.

## What Changes

- Isolate training-library stdout while the CLI invokes SFT so stdout contains only the final sanitized result JSON.
- Route ordinary training progress to stderr without emitting a second result JSON.
- Preserve the existing typed exit-code policy and public-result allowlist for success and runtime exceptions.
- Add a regression test reproducing the real two-line Python mapping output observed from `Trainer.train()` and proving the complete stdout parses as exactly one JSON document.
- Record the fix in the supervised contract-tuning specification and an auditable Human Brief.
- Explicitly do not authorize or perform a second real smoke, full training, prediction, evaluation, DPO, GRPO, lockbox access, or any model-improvement claim.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `supervised-contract-tuning`: Strengthen the existing training CLI one-JSON requirement so third-party training progress cannot contaminate stdout during real execution.

## Impact

- Affected code: `src/voice2task/cli/train.py` and focused CLI tests.
- Affected contract: the existing stdout/stderr and exit-status requirement in `openspec/specs/supervised-contract-tuning/spec.md`.
- No model, dataset, dependency, output-directory, clean-evaluation, or training-budget behavior changes.
- No generic chat fine-tuning, skill routing, GUI action policy learning, first-phase GRPO, public release of the full local corpus, released checkpoint claim, or live-browser benchmark claim.
