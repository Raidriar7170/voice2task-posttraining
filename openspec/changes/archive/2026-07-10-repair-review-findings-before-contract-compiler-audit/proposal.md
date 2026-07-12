## Why

Three review findings currently weaken the repository's evidence boundary before a Contract Compiler V2 audit can begin: strict contract equality follows Python numeric coercion for untyped slot values, the public evidence index still presents a completed lockbox phase as blocked, and the formal public dev/test splits have no committed contamination audit despite known cross-split reuse. These defects must be repaired without rewriting historical metrics or silently presenting spent development splits as blind evaluation.

## What Changes

- Make `contract_exact_match` compare parsed contracts with type-preserving JSON structural equality, while continuing to ignore key order and serialization whitespace.
- Reconcile the machine-readable and Markdown evidence indexes with the completed lockbox final evaluation, preserving the earlier blocked phase as superseded history.
- Add a deterministic public-split contamination audit and a fail-closed gate for future independently claimed split boundaries.
- Publish the current formal public dev/test boundary as development-only/spent evidence; do not mutate the committed 696-row SFT dataset or re-score historical prediction artifacts.
- Produce a concise Chinese Human Brief and archive this bounded repair before opening the Contract Compiler V2 causal-boundary audit.
- Non-goals: no generic chat fine-tuning, skill routing, GUI action policy learning, GRPO, full private-corpus release, data resplit, training, prediction, A100 execution, checkpoint/adapter release, live-browser benchmark claim, or model-quality claim.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `contract-evaluation`: define type-preserving JSON structural equality for strict full-contract exact match and require current/superseded lockbox evidence navigation to remain synchronized.
- `voice2task-dataset-preparation`: require deterministic split-contamination reporting, development-only labeling for the current spent dev/test boundary, and a fail-closed clean-split gate before any future independent-held-out claim.

## Impact

- Evaluator implementation and exact-match regression tests.
- Public evidence index JSON/Markdown, current truth-surface validation, and project documentation.
- Dataset validation/audit code, CLI surface, committed public-safe audit artifacts, and focused tests.
- OpenSpec delta specifications and a Chinese Human Brief. Historical datasets, predictions, aggregate metrics, and model artifacts remain unchanged.
