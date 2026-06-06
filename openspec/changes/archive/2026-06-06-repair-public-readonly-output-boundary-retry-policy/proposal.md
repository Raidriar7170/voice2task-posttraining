## Why

The archived `run-a100-public-readonly-search-policy-train-split-rerun` phase proved that public-readonly fields entered the raw private-adapter output, but strict Browser Task Contract validity regressed to `0/3`. The remaining actionable local failure pattern is output-boundary and retry-prompt drift: malformed top-level JSON, retry outputs wrapped in prose/Markdown, and `task_type` still using the route enum value `search_web`.

## What Changes

- Strengthen the shared SFT/prediction prompt with compact output-boundary guidance: exactly one root JSON object, all eight top-level fields inside that single object, no extra braces before `normalized_command`, no prose/Markdown, and public-readonly search must use `task_type="search"`, not `search_web`.
- Strengthen the schema retry prompt with the same compact constraints and a minimal valid public-readonly search skeleton.
- Record local public-safe evidence that this is prompt/retry policy hardening only and does not run training, private prediction, A100 execution, evaluator metric changes, schema coercion, or prediction repair.
- Preserve prior A100 evidence as negative evidence and use it only as the source diagnosis.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `supervised-contract-tuning`: make output-boundary and retry-prompt policy explicit for public-readonly search contract generation.
- `contract-evaluation`: publish local public-safe evidence that connects the policy repair to the prior A100 failure without changing metrics or reinterpreting predictions.

## Impact

- Affected code: prompt serialization and retry prompt text in `src/voice2task/formatting.py` and `src/voice2task/training.py`.
- Affected tests: focused prompt/retry metadata tests and evidence-pack boundary tests.
- Affected evidence: `reports/public-sample/public-readonly-output-boundary-retry-policy/` and Human Briefs under `docs/human-briefs/`.
- Non-goals: no A100 execution, no SFT/DPO/GRPO training, no private prediction rerun, no dev/test evaluation, no evaluator metric change, no prediction repair/re-score, no semantic-equivalence scoring, no slot normalization, no checkpoint or adapter release, no production-readiness claim, no held-out generalization claim, and no live-browser benchmark improvement claim.
