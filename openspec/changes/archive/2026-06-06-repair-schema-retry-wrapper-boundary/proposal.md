## Why

The archived `run-a100-output-boundary-retry-policy-train-split-rerun` phase narrowed the remaining failure: raw private-adapter outputs became whole JSON objects for `3/3` rows, but all raw objects omitted `task_type`; retry attempts visibly included `task_type="search"` for `3/3` rows but were wrapped in prose/Markdown and rejected by the strict whole-string parser.

The next bounded local step is to harden retry-wrapper boundary language and diagnostics so the repo can prove the retry prompt now explicitly rejects wrapper-style completions before deciding whether another A100 rerun is worth the cost.

## What Changes

- Add stronger retry prompt wording that names wrapper failure modes from the A100 diagnosis: no preface, no explanation, no Markdown fences, no trailing analysis, and no text outside the single JSON root.
- Keep strict parser, schema guard semantics, evaluator metrics, historical predictions, and A100 evidence unchanged.
- Add focused tests and public-safe local evidence proving this phase is local prompt/diagnostic hardening only.
- Generate a concise Chinese Human Brief for the phase.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `supervised-contract-tuning`: strengthen schema retry prompt boundary language for wrapper-free JSON-only retry output.
- `contract-evaluation`: publish local public-safe evidence connecting the retry-wrapper repair to the prior A100 diagnosis without changing metrics or reinterpreting predictions.

## Impact

- Affected code: `src/voice2task/training.py`.
- Affected tests: retry prompt focused tests and local evidence boundary tests.
- Affected evidence: `reports/public-sample/schema-retry-wrapper-boundary-policy/` and `docs/human-briefs/`.
- Non-goals: no A100 execution, no training, no private prediction rerun, no parser relaxation, no evaluator metric change, no prediction repair/re-score, no semantic-equivalence scoring, no slot normalization, no checkpoint or adapter release, no held-out generalization claim, no model-quality claim, and no live-browser benchmark improvement claim.
