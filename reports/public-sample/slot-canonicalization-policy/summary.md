# Slot Canonicalization Policy Summary

- Manifest: `public-sample-20260617T152259Z`
- Status: design-only policy evidence.
- Evidence base: `CONTEXT.md`, layered evaluation, residual diagnosis, remediation target selection, schema/evaluator source, and evaluation docs.

## Conclusion

The current public evidence points to a contract consistency bottleneck, not a reason to train immediately. Slot keys are comparatively stable (`slot_key_f1` dev `0.9872`, test `0.9769`), while slot values and `normalized_command` dominate strict residuals.

## Current Evidence

| surface | dev | test |
| --- | ---: | ---: |
| strict exact | `0.2464` | `0.2029` |
| executable contract pass | `0.2705` | `0.2512` |
| slot value exact F1 | `0.2821` | `0.2390` |
| slot value normalized F1 | `0.2821` | `0.2390` |
| slot key F1 | `0.9872` | `0.9769` |

Dominant residual families from target selection:

- `slot_value_mismatch=336`
- `normalized_command_mismatch=194`
- `extra_slot=16`
- `missing_slot=13`
- `route_mismatch=13`
- `task_type_mismatch=13`

## Boundary

This phase does not train, predict, launch A100, mutate public sample data, change splits, add SFT/DPO rows, change evaluator definitions, relax strict exact, use an LLM judge, run semantic-equivalence scoring, repair predictions, or claim model improvement.

Strict `contract_exact_match` and strict slot metrics remain the authority. All canonicalization described here is policy/design guidance for a later bounded phase.

## Required Policy Files

- `slot-key-policy.md`
- `slot-value-policy.md`
- `normalized-command-policy.md`
- `model-target-boundary.md`
- `recommended-next-change.md`

