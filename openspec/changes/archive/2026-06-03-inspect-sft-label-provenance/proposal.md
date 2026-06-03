## Why

The latest SFT target-template alignment phase proved local prompt/target structure, but it still could not prove whether the real SFT path masks labels so only the assistant contract target contributes to loss. This change closes that local evidence gap before another private A100 rerun is interpreted as model-learning evidence.

## What Changes

- Add a local, public-safe SFT label provenance inspection path that records tokenizer/chat-template status, collator availability, inspected label tensor status, and assistant-target loss-mask evidence without requiring private adapters or A100 execution.
- Extend the existing objective-inspection/evidence surfaces so unavailable dependencies or labels remain explicit fail-closed states rather than inferred success.
- Publish a sanitized public-sample evidence pack and Human Brief that separates structural target-span evidence from true label provenance evidence.
- Keep prior train-split and target-template diagnostic artifacts linked but unchanged.
- Non-goals: generic chat fine-tuning, skill routing, GUI action policy learning, first-phase GRPO, public release of the full local corpus, checkpoint release, adapter release, live-browser benchmark improvement claims, and private A100 rerun execution.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `supervised-contract-tuning`: Require a real-SFT-path label provenance diagnostic that reports tokenizer/template, collator, label tensor, and assistant-target mask evidence before objective claims.
- `contract-evaluation`: Require a public-safe label provenance evidence pack and bounded interpretation in committed reports.

## Impact

- Affected code: SFT training/objective inspection helpers, train CLI surfaces, report writers, leak scanning coverage, and focused tests.
- Affected artifacts: `reports/public-sample/` evidence files, OpenSpec specs, and a Chinese Human Brief for the phase.
- Dependencies: no new mandatory runtime dependency; optional Transformers/TRL/PEFT/tokenizer availability must be reported explicitly when unavailable.
- Systems not affected: no private A100 execution, no model download by default, no committed checkpoints/adapters, and no downstream Voice-to-Browser Agent runtime changes.
