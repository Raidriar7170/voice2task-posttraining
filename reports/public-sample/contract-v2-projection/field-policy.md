# Contract V2 Projection Field Policy

Status: blocked before metric execution.

## Core Model Fields

The proposed V2 Core model target is limited to task, route, safety,
confirmation, and slots. These are the fields that determine whether a browser
task contract is semantically executable under the current deterministic
evaluation policy.

## Derived / Envelope Fields

`language` and `contract_version` are derived envelope fields. They should be
fixed by a deterministic postprocessor in a future implementation phase, not
predicted by the model during this projection experiment.

## Display / Diagnostic Field

`normalized_command` is treated as a display / diagnostic field for this
experiment. It must not participate in V2 Core exact match. A deterministic
renderer may produce it only from task type, route, and slots when a bounded
template supports the specific pattern.

## Non-Expansion Boundary

This phase does not add `allowed_actions`, `success_criteria`, `policy_tags`,
`runtime_hints`, or other fields not present in the current V1 schema.

## Blocked Execution

The field policy could not be evaluated on current step-matched raw contracts
because those raw current prediction/gold artifacts are not committed.
