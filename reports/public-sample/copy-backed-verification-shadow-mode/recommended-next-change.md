# Recommended Next Change

Decision: `SHADOW_MODE_READY_FOR_REVIEW`.

Next change: `review-copy-backed-shadow-mode-before-runtime-wiring`.

Scope: Review the shadow-mode evidence before any narrower runtime-wiring proposal; no enforcement is approved by this phase.

Reason: Shadow sidecars attach deterministically to every current prediction contract while preserving V1 evaluator behavior.

Boundary: source-backed provenance is not correctness, and shadow mode is not enforcement.

Non-goals: runtime enforcement, action enablement, training, evaluator changes, prediction repair, model-quality claims, production readiness, and live-browser claims.
