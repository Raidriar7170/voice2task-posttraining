# Normalized Command Policy

`normalized_command` currently contributes many strict residuals: `91` on dev and `103` on test in residual diagnosis, for `194` combined normalized-command mismatches in remediation target selection.

## Positioning

The recommended position is diagnostic/display-oriented. A later bounded change should decide whether `normalized_command` remains a free model target or is generated from deterministic templates from `task_type`, `route`, `slots`, safety, and confirmation decisions.

## Examples

- `搜索厦门轮渡时刻表` vs `搜索厦门轮渡时间` should remain a visible diagnostic mismatch.
- `搜索南京今天空气质量` vs `搜索南京今日空气质量` may be reviewed as a display-template candidate, but this phase does not declare equivalence.
- `拒绝代替用户付款` vs `拒绝代替用户下单付款` should remain safety-review visible until a later policy explicitly defines the display phrase.

## Metric Impact

This policy has no strict exact impact. It does not normalize, repair, replace, or re-score predictions. `normalized_command` should remain outside the core executable-contract pass condition unless a later OpenSpec change explicitly changes that contract.

## Non-Goals

- No evaluator relaxation.
- No LLM judge.
- No semantic-equivalence scoring.
- No prediction repair.
- No model improvement claim.
- No training or prediction rerun.

