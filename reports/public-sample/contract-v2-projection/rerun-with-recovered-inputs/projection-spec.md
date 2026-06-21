# Contract V2 Projection Rerun Spec

- L0: V1 full strict exact, unchanged.
- L1: V1 without `normalized_command` exact.
- L2: V2 Core strict exact.
- L3: V2 envelope build and renderer evaluation.
- Projection reads parsed `prediction_contract`, not `raw_model_output`.
- V2 Core fields: `task_type`, `route`, `safety`, `confirmation_required`, `slots`.
- Forbidden fields: `allowed_actions`, `success_criteria`, `policy_tags`, `runtime_hints`.
