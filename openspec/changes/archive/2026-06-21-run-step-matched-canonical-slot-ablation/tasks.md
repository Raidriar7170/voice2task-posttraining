## 1. OpenSpec and Planning

- [x] Create `run-step-matched-canonical-slot-ablation` OpenSpec proposal.
- [x] Add design notes, spec deltas, and implementation task list.
- [x] Validate the OpenSpec change in strict mode before implementation.

## 2. Local Implementation

- [x] Add step-matched control/treatment SFT config templates with explicit
  equal `max_steps` and identical paired invariants.
- [x] Add or update prediction/evaluation config templates for the frozen
  dev/test comparisons without changing prompt, decoding, evaluator, LoRA, or
  base model policy.
- [x] Add training-budget metadata capture for fresh SFT runs so observed
  optimizer steps and target-token exposure can be summarized safely.
- [x] Add public-safe reporting helper(s) for boundary verification,
  training-budget provenance, paired row deltas, family deltas, bootstrap
  diagnostics, comparison, and bounded decision output.
- [x] Add focused training-budget metadata test.

## 3. Runtime Execution

- [x] Inspect A100 connectivity before launching work.
- [x] Inspect GPU occupancy before launching work.
- [x] Recover the previous control run's optimizer-step budget from actual or
  reconstructed training evidence; block if it cannot be recovered honestly.
- [x] Verify control/treatment dev/test boundary by row ids, order, inputs, and
  gold contract hashes; block if the held-out boundary is not comparable.
- [x] Train fresh control and treatment adapters using the same explicit
  `max_steps`, batch, gradient accumulation, scheduler steps, seed, prompt,
  tokenizer, LoRA policy, and base model.
- [x] Generate sanitized dev/test predictions for both arms on the same frozen
  dev/test rows.
- [x] Evaluate primary and guardrail metrics with the existing evaluator.

## 4. Evidence and Validation

- [x] Write observed comparison artifacts under
  `reports/public-sample/step-matched-canonical-slot-ablation/`.
- [x] Write `docs/human-briefs/2026-06-20-run-step-matched-canonical-slot-ablation.html`.
- [x] Run focused tests, strict OpenSpec validation, leak/public-safety checks,
  and whitespace checks.
- [x] Run a read-only reviewer pass over the diff and fix Must Fix findings
  within scope.
- [x] Report changed files, validation results, decision label, and remaining
  risks.
