# Voice2Task Evaluation Boundaries

Updated: 2026-06-18

This project keeps strict contract evaluation as the primary evidence surface.
`evaluate_predictions()` still owns strict `contract_exact_match` and strict
`slot_f1`; layered evaluation is additive diagnostic evidence only.

## Current Layered Evidence

The bounded `add-layered-evaluator-and-residual-diagnosis` phase reads the
existing scaled prediction-only dev/test artifacts for
`public-sample-20260617T152259Z` from
`reports/public-sample/a100-scaled-public-sample-current-123-adapter-prediction-baseline-after-a100-recovery/`.
It does not train, rerun prediction, merge data, tune LoRA parameters, repair
predictions, repair slots, relax strict metrics, or overwrite historical scaled
evidence.

New evidence:

- `reports/public-sample/layered-eval/`
- `reports/public-sample/residual-diagnosis/`

| split | rows | strict exact | executable pass | schema validity | route accuracy | task type accuracy | slot key F1 | slot value exact F1 | slot value normalized F1 | unsafe FN rate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| dev | 207 | 0.2464 | 0.2705 | 1.0000 | 0.9614 | 0.9614 | 0.9872 | 0.2821 | 0.2821 | 0.0000 |
| test | 207 | 0.2029 | 0.2512 | 1.0000 | 0.9758 | 0.9758 | 0.9769 | 0.2390 | 0.2390 | 0.0083 |

`contract_exact_match_strict` is copied from the existing strict evaluator
result. It is not renamed, re-scored, normalized, or repaired.

## Layered Metrics

Layered reports include:

- `schema_validity`
- `route_accuracy`
- `task_type_accuracy`
- `slot_key_precision`, `slot_key_recall`, `slot_key_f1`
- `slot_value_exact_f1`
- `slot_value_normalized_f1`
- `risk_level_accuracy`
- `requires_confirmation_accuracy`
- `unsafe_false_negative_rate`
- `unsafe_false_positive_rate`
- `refusal_or_clarify_accuracy`
- `executable_contract_pass_rate`
- `contract_exact_match_strict`

Deterministic normalization is limited to diagnostic slot-key/value and
executable-contract checks. It may trim whitespace and punctuation, normalize
full-width/half-width text and casing, and apply conservative aliases such as
`keyword` to `query` or `open` to `打开`. It does not use an LLM judge,
embeddings, broad semantic similarity, prediction repair, slot repair, or
strict metric relaxation. It must not equate materially different entities,
locations, dates, amounts, or user intents.

On the current scaled evidence, normalized slot-value F1 equals exact slot-value
F1. That means the bounded normalization did not recover additional slot-value
matches in this run.

## Executable Pass Rate

`executable_contract_pass_rate` is fail-closed. A prediction can pass only when
it is schema valid, has the correct route and task type, includes required slot
keys, has slot values matching exactly or through bounded deterministic
normalization, preserves risk and confirmation decisions, avoids unsafe
downgrades, and remains runtime-consumable.

Any gold blocked/high-confirmation case predicted as low-risk auto execution
fails executable evaluation and contributes to unsafe false negatives.

## Residual Diagnosis

Residual reports inspect strict exact mismatches only. They attribute residuals
to route, task type, normalized command, slot key, slot value, missing slot,
extra slot, risk level, confirmation, success criteria, allowed actions,
refusal-or-clarify, extra field, missing field, and invalid-output families.

Current residual summary:

| split | strict pass | strict fail | top field | dominant families |
| --- | ---: | ---: | --- | --- |
| dev | 51 | 156 | `normalized_command` | `slot_value=160`, `normalized_command=91` |
| test | 42 | 165 | `normalized_command` | `slot_value=176`, `normalized_command=103` |

Recommendations in these reports are diagnostic-only. They may guide a later
bounded OpenSpec phase, but they do not materialize data, change strict metrics,
alter predictions, or claim model improvement.
