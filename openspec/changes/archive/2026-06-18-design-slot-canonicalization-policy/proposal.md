## Why

The current layered evaluator and residual-diagnosis evidence show stable JSON
shape and route/task behavior, but strict exact match, strict slot F1,
executable-contract pass rate, slot-value consistency, and normalized-command
consistency remain weak. Before another data merge, SFT retry, DPO expansion, or
evaluator change, the project needs a public-safe policy phase that defines what
the model should predict, what deterministic code should derive, and what must
remain diagnostic only.

## What Changes

- Add design-only slot canonicalization policy evidence under
  `reports/public-sample/slot-canonicalization-policy/`.
- Define canonical slot keys, alias-to-canonical mappings, disallowed slot keys,
  and task-type-specific required/optional slot boundaries.
- Define conservative slot-value canonicalization rules for later data policy
  and layered diagnostics without changing strict exact-match semantics.
- Reposition `normalized_command` as a diagnostic/display field candidate and
  document whether it should be generated from deterministic templates rather
  than freely predicted by the model.
- Separate model targets from deterministic postprocessor-derived or validated
  fields such as `allowed_actions`, `success_criteria`, policy tags, display
  text, and runtime hints.
- Map residual families to follow-up strategies and write a bounded
  `recommended-next-change.md`.
- Add focused tests for deterministic policy artifacts, non-equivalence
  boundaries, strict-exact preservation, required report files, and leak-scan
  cleanliness.
- Update public documentation to state that this phase is policy/design only
  and does not train, predict, mutate data, relax evaluation, or claim model
  improvement.
- Non-goals: generic chat fine-tuning, skill routing, GUI action policy
  learning, first-phase GRPO, public release of the full local corpus, training,
  prediction reruns, public-sample data mutation, split changes, DPO expansion,
  LoRA/base-model changes, evaluator relaxation, LLM judging,
  semantic-equivalence scoring, prediction repair, checkpoint/adapter release,
  held-out recovery claims, production-readiness claims, safety-readiness
  claims, and live-browser benchmark claims.

## Capabilities

### New Capabilities

- `slot-canonicalization-policy`: publish public-safe slot key, slot value,
  normalized-command, model-target, postprocessor-boundary, remediation-mapping,
  and next-change policy artifacts before later data or training phases.

### Modified Capabilities

- None.

## Impact

- New policy artifacts under
  `reports/public-sample/slot-canonicalization-policy/`.
- New or updated tests under `tests/`.
- Documentation update in `README.md` or `docs/evaluation.md`.
- New OpenSpec phase artifacts and a Chinese Human Brief HTML.
- No training, prediction, evaluator, split, public-sample data, model, adapter,
  checkpoint, or A100 impact.
