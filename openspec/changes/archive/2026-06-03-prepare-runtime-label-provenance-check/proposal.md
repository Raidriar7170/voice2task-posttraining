## Why

The previous phase made local SFT label provenance explicit, but the committed evidence still shows `true_label_mask_status=unavailable` because no real tokenizer/collator runtime labels were inspected. This change prepares a safe, reproducible runtime-check path so a later authorized private/A100 run can produce real label provenance evidence without changing public-claim boundaries.

## What Changes

- Add an explicit runtime label provenance preparation path that validates private override requirements before any model/tokenizer/collator runtime check can run.
- Add public-safe config/report templates for runtime label provenance evidence under committed sample artifacts.
- Extend objective-inspection metadata so real runtime checks can record runtime intent, private override status, package/version policy, output placement policy, and fail-closed reasons when runtime execution is not authorized.
- Generate a public-safe preparation evidence pack and Human Brief that state no A100/private adapter execution occurred in this phase.
- Non-goals: generic chat fine-tuning, skill routing, GUI action policy learning, first-phase GRPO, public release of the full local corpus, running private A100 infrastructure, downloading models by default, checkpoint release, adapter release, held-out generalization, production readiness, and live-browser benchmark improvement claims.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `supervised-contract-tuning`: Add a gated runtime label provenance preparation requirement that defines private override validation, output-root boundaries, and non-heavy default behavior before real tokenizer/collator label inspection.
- `contract-evaluation`: Add a public-safe runtime label provenance preparation evidence requirement that records readiness, blocked/skipped states, prior evidence links, leak-scan status, and bounded interpretation.

## Impact

- Affected code: training/objective inspection CLI, report generation CLI, config templates, tests, and evidence pack writers.
- Affected artifacts: a new committed runtime-check config template and public-safe preparation report under `reports/public-sample/`.
- Dependencies: no new mandatory dependency; optional runtime dependencies remain behind explicit opt-ins and private overrides.
- Systems not affected: no A100 connection, no private adapter load, no heavy model download, no downstream Voice-to-Browser Agent runtime change, and no public checkpoint or benchmark claim.
