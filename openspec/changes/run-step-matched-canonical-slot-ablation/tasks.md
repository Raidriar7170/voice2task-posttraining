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
- [ ] Add public-safe reporting helper(s) for boundary verification,
  training-budget provenance, paired row deltas, family deltas, bootstrap
  diagnostics, comparison, and bounded decision output. Blocked by A100
  preflight in this run before metrics existed.
- [x] Add focused training-budget metadata test. Report/gate tests remain
  pending because the phase blocked before observed metrics were available.

## 3. Runtime Execution

- [x] Inspect A100 connectivity before launching work.
- [ ] Inspect GPU occupancy before launching work. Blocked because A100 SSH
  preflight did not connect.
- [ ] Recover the previous control run's optimizer-step budget from actual or
  reconstructed training evidence; block if it cannot be recovered honestly.
- [ ] Verify control/treatment dev/test boundary by row ids, order, inputs, and
  gold contract hashes; block if the held-out boundary is not comparable.
- [ ] Train fresh control and treatment adapters using the same explicit
  `max_steps`, batch, gradient accumulation, scheduler steps, seed, prompt,
  tokenizer, LoRA policy, and base model.
- [ ] Generate sanitized dev/test predictions for both arms on the same frozen
  dev/test rows.
- [ ] Evaluate primary and guardrail metrics with the existing evaluator.

## 4. Evidence and Validation

- [x] Write blocked artifact under
  `reports/public-sample/step-matched-canonical-slot-ablation/`.
- [ ] Write `docs/human-briefs/2026-06-20-run-step-matched-canonical-slot-ablation.html`.
- [ ] Run focused tests, strict OpenSpec validation, leak/public-safety checks,
  and whitespace checks.
- [ ] Run a read-only reviewer pass over the diff and fix Must Fix findings
  within scope.
- [ ] Report changed files, validation results, decision label, and remaining
  risks.
