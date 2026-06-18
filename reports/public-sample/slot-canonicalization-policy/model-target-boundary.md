# Model Target Boundary

The goal is to reduce avoidable output-space drift by separating model-target fields from deterministic postprocessor-derived fields. This is a design boundary only.

## Model-Target Fields

These fields remain model-target candidates because they express intent, safety, confirmation, or slots that cannot be derived without understanding the user command:

- `task_type`
- `route`
- `safety.allow`
- `safety.reason`
- `confirmation_required`
- `slots`

## Derived-Field Classification

These are derived-field or validated-field candidates for a later deterministic postprocessor:

| field | classification | reason |
| --- | --- | --- |
| `allowed_actions` | derived-field | Can be derived from `route`, `task_type`, safety, and confirmation policy. |
| `success_criteria` | derived-field | Can be templated from the executable contract. |
| `display_normalized_command` | derived-field | Can be generated from deterministic display templates. |
| `policy_tags` | derived-field | Can be assigned from route/safety policy. |
| `confirmation_defaults` | derived-field | Can be validated against `confirmation_required` and task risk. |
| `runtime_hints` | derived-field | Should be runtime-side metadata, not a model-predicted slot. |
| `language` | validated-field | Current schema requires `zh-CN`. |
| `contract_version` | validated-field | Current schema requires `v1`. |

## Why This Matters

Freely generating derivable fields such as `allowed_actions`, `success_criteria`, display `normalized_command`, policy tags, confirmation defaults, or runtime hints enlarges the model output space. That can lower strict exact or executable-contract pass rates without adding real task-understanding value.

## Boundary

No deterministic postprocessor is implemented in this phase. A later change must define its own inputs, outputs, tests, validation, and metric interpretation.

