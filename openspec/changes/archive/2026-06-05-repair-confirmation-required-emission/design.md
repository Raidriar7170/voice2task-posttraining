## Context

The latest route-ontology A100 rerun produced contract-like train predictions with correct raw `route` and `task_type` values, but strict Browser Task Contract validation still rejected every final prediction because `confirmation_required` was missing. The earlier general required-field phase already added a visible contract skeleton and schema guard metadata, so this phase narrows the repair to the remaining confirmation field emission path.

## Goals / Non-Goals

**Goals:**
- Make `confirmation_required` impossible to miss in the model-visible contract instructions and canonical examples.
- Ensure local tests cover the current weather/search prompt path that previously reached A100 with missing `confirmation_required`.
- Surface missing `confirmation_required` as a separate public-safe diagnostic count when evidence artifacts include observable schema failures.
- Preserve strict evaluation boundaries: invalid outputs remain invalid and no missing field is inserted into model predictions.

**Non-Goals:**
- Do not run A100 training or private-adapter prediction in this phase.
- Do not change gold contracts, Browser Task Contract schema, strict parser acceptance, route ontology semantics, or evaluation success criteria.
- Do not coerce, repair, alias, or fill missing `confirmation_required` in prediction artifacts.
- Do not claim model recovery, held-out generalization, checkpoint release, adapter release, production readiness, public full-corpus release, or live-browser benchmark improvement.

## Decisions

- Treat this as a prompt/example visibility repair, not a schema repair. The schema already requires `confirmation_required`; the remaining local work is to make that field more salient in training/prediction text and evidence.
- Prefer focused tests around the shared formatting surface and diagnostics rather than broad retraining or private runtime execution. This keeps the phase local and separates implementation readiness from later A100 evidence.
- Use `false` in canonical low-risk weather/search examples. This teaches the required boolean field without implying confirmation is unnecessary for destructive, payment, account, privacy, or other sensitive actions.
- Keep diagnostics observational. They may count missing `confirmation_required` in invalid predictions, but they must not convert invalid rows into valid contracts.

## Risks / Trade-offs

- [Risk] Stronger examples can be mistaken for proof that the private adapter will recover. -> Mitigation: Human Brief and loop report label this as local prompt/evidence repair only.
- [Risk] Adding a defaulting rule could be read as post-hoc normalization. -> Mitigation: apply the rule only to model-visible instruction/example text, not prediction artifact mutation.
- [Risk] A later A100 rerun may still fail because the adapter learned another incomplete pattern. -> Mitigation: keep the next A100 rerun as a separate bounded phase with honest train-split-only interpretation.
