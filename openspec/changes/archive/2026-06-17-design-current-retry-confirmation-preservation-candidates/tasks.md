## 1. Evidence Inputs

- [x] 1.1 Verify the current retry trade-off diagnosis evidence exists and is bound to `public-sample-20260616T165835Z`.
- [x] 1.2 Load the source diagnosis rows and isolate confirmation regressions by split, family, and target shape.
- [x] 1.3 Confirm the phase does not require public sample mutation, training, prediction generation, prompt changes, evaluator changes, or adapter/checkpoint release.

## 2. Candidate Design Output

- [x] 2.1 Generate a public-safe JSON/Markdown candidate design report with stable candidate ids, source row ids, support counts, accepted target sketches, rejected drift sketches, and suggested public-safe utterance templates.
- [x] 2.2 Cover unsafe-payment confirmation preservation and public navigation non-confirmation preservation as separate candidate families.
- [x] 2.3 Record explicit design-only flags: no seed materialization, no SFT/DPO rows, no manifest rebuild, no training, no prediction, no evaluator change, and no model-quality claim.
- [x] 2.4 Recommend at most one later bounded materialization phase after candidate coverage is explicit.

## 3. Status Surfaces

- [x] 3.1 Refresh `CONTEXT.md` with the candidate-design result and strict claim boundaries.
- [x] 3.2 Refresh `reports/final_status.md` with the candidate-design result and next-stage recommendation.
- [x] 3.3 Generate a concise Chinese Human Brief under `docs/human-briefs/`.

## 4. Validation And Archive

- [x] 4.1 Add or update focused tests for the candidate design report shape and committed evidence.
- [x] 4.2 Run full tests, ruff, OpenSpec strict validation, leak scan, candidate-count checks, and `git diff --check`.
- [x] 4.3 Review the diff for overclaiming, private-path leakage, and unrelated changes.
- [x] 4.4 Archive the OpenSpec change, then stage/commit/push under the guarded auto-integration policy.
