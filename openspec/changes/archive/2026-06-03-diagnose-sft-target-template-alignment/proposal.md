## Why

The real A100 train-split diagnostic preserved private-adapter failures, but the current evidence still cannot explain whether the failure comes from SFT target masking, chat-template drift, prompt/target serialization, or adapter/base metadata alignment. A bounded public-safe diagnostic is needed before another private A100 rerun or retraining step.

## What Changes

- Add a local diagnostic path that compares SFT training text and prediction prompts for the same rows without loading private adapters or running private prediction.
- Report whether assistant contract targets are present, whether the assistant target span can be identified in rendered text, and whether mask/loss evidence is proven, unavailable, or only a structural proxy.
- Record chat-template and fallback policy evidence, including tokenizer-template availability when inspectable and deterministic fallback behavior when not.
- Record public-safe adapter/base alignment metadata from config and prediction metadata using placeholders for private paths.
- Publish a concise evidence report that links the prior failed train-split diagnostic while avoiding checkpoint, adapter, dev/test generalization, production-readiness, or live-browser improvement claims.
- Non-goals: generic chat fine-tuning, skill routing, GUI action policy learning, first-phase GRPO, public release of the full local/private corpus, real A100 retraining, private adapter prediction, checkpoint release, adapter release, production-readiness claims, dev/test generalization claims, and live-browser benchmark improvement claims.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `supervised-contract-tuning`: require public-safe diagnostics for SFT target span, label-mask evidence boundaries, chat-template/fallback policy, and adapter/base metadata alignment before interpreting another train-split overfit rerun.
- `contract-evaluation`: require a public-safe alignment report that connects prior train-split failure evidence to training-target, prompt-template, and adapter/base diagnostic findings without repairing predictions or changing claims.

## Impact

- Affected code: SFT formatting/training diagnostics, report generation, CLI surfaces, and tests.
- Affected artifacts: public-safe reports under `reports/public-sample/`, OpenSpec specs, and a Chinese Human Brief for this phase.
- No raw logs, checkpoints, adapters, remote caches, private overrides, host details, SSH details, tokens, private paths, or private corpus rows may be committed.
