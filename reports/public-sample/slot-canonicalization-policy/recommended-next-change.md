# Recommended Next OpenSpec Change

- proposed change id: `materialize-canonical-slot-boundary-candidates`

## Rationale

Current evidence shows stable schema shape and strong slot-key metrics, but weak strict slot values and many `normalized_command` mismatches. The next bounded phase should materialize reviewed public-safe canonical slot-boundary candidates from this policy before any formal data merge, postprocessor implementation, or training retry.

## Scope

- Create reviewed candidate examples for slot key aliases and slot value boundaries.
- Keep candidate artifacts standalone until explicitly reviewed.
- Preserve strict evaluator semantics.
- Keep `normalized_command` diagnostic/display-only unless a later spec changes it.
- Produce public-safe evidence and leak-scan results.

## Acceptance Criteria

- Candidate examples are traceable to this policy and current public residual families.
- Non-equivalence examples remain excluded from merge/normalization.
- No formal public sample data is mutated.
- No SFT/DPO rows are added.
- Strict exact and layered metric definitions remain unchanged.
- Public artifacts pass leak scan.

## Non-Goals

- No training.
- No prediction run.
- No A100 job.
- No formal public sample merge.
- No split change.
- No deterministic postprocessor implementation.
- No evaluator relaxation.
- No semantic-equivalence scoring or LLM judge.
- No prediction repair.

## Metrics To Watch Later

- `contract_exact_match_strict`
- `slot_key_f1`
- `slot_value_exact_f1`
- `slot_value_normalized_f1`
- `executable_contract_pass_rate`
- `normalized_command_mismatch`
- `extra_slot`
- `missing_slot`

## Claims Not To Overstate

- Do not claim model improvement.
- Do not claim held-out recovery.
- Do not claim production readiness.
- Do not claim safety readiness.
- Do not claim live-browser benchmark improvement.
- Do not treat normalized slot metrics as recovery evidence.
