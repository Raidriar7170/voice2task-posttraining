# Recommended Next Change

Decision: `COPY_SLICE_READY_FOR_SHADOW_INTEGRATION`.

Next change: `integrate-copy-backed-slot-verification-shadow-mode`.

Scope: Integrate the verifier in shadow mode only, with sidecar comparison and no runtime enforcement unless separately approved.

Reason: The offline slice proves deterministic source-span provenance for enabled query/field/target scopes without mutating V1 predictions or evaluator behavior.

Boundary: source-backed provenance is not correctness; any shadow integration must remain sidecar-only until separately specified and validated.

Non-goals: training, prediction repair, evaluator relaxation, action enablement, runtime enforcement, production claims, and model-quality claims.
