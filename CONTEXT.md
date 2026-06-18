# Voice2Task Post-Training

Voice2Task Post-Training is a companion project for training and evaluating small language models that turn Chinese spoken browser commands into safe, schema-valid browser task contracts.

## Current Status Contract

As of 2026-06-18, the first project phase is closed as an evidence-backed
post-training and evaluation baseline, not as a production-ready model release.
The public-facing truth surface has twenty-four current layers. The newest
five are the slot canonicalization policy under
`reports/public-sample/slot-canonicalization-policy/`, the safety repair
candidate design review under
`reports/public-sample/safety-repair-candidate-design-review/`, the safety
repair candidate design under `reports/public-sample/safety-repair-candidate-design/`,
the residual-driven remediation target selection under
`reports/public-sample/remediation-target-selection/`, and the additive layered
evaluator under `reports/public-sample/layered-eval/`;
the existing nineteen layers remain:

1. the additive residual diagnosis under
   `reports/public-sample/residual-diagnosis/`;
2. the standalone scaled clarify slot-boundary candidate materialization under
   `reports/public-sample/scaled-clarify-slot-boundary-candidate-materialization/`;
3. the scaled clarify slot-boundary candidate design under
   `reports/public-sample/scaled-clarify-slot-boundary-candidate-design/`;
4. the scaled residual remediation target selection under
   `reports/public-sample/scaled-residual-remediation-target-selection/`;
5. the scaled-manifest current-123 adapter prediction baseline recovery retry
   evidence under
   `reports/public-sample/a100-scaled-public-sample-current-123-adapter-prediction-baseline-after-a100-recovery/`;
6. the scaled-manifest current-123 adapter residual-cluster inspection under
   `reports/public-sample/scaled-current-123-adapter-residual-cluster-inspection/`;
7. the scaled-manifest current-123 adapter residual-family diagnosis under
   `reports/public-sample/scaled-current-123-adapter-residual-diagnosis/`;
8. the prior scaled-manifest current-123 adapter prediction baseline blocked evidence
   under
   `reports/public-sample/a100-scaled-public-sample-current-123-adapter-prediction-baseline/`;
9. the scaled public-sample formal merge evidence under
   `reports/public-sample/scaled-public-sample-merge/`;
10. the standalone scaled public-sample candidate materialization evidence under
   `reports/public-sample/scaled-public-sample-candidate-materialization/`;
11. the scaled public-sample and tiered-evaluation design evidence under
   `reports/public-sample/scaled-public-sample-and-tiered-eval-design/`;
12. the current-123-row train-split SFT retry model evidence under
   `reports/public-sample/a100-current-123-train-split-sft-retry/`;
13. the current-123-row train-split SFT retry readiness evidence under
   `reports/public-sample/current-123-train-split-sft-retry-readiness/`;
14. the current-retry confirmation-preservation materialization and public merge
   under
   `reports/public-sample/current-retry-confirmation-preservation-public-sample-merge/`;
15. the current-retry confirmation-preservation candidate design under
   `reports/public-sample/current-retry-confirmation-preservation-candidate-design/`;
16. the current-train-split SFT retry trade-off diagnosis under
   `reports/public-sample/current-train-split-sft-retry-tradeoff-diagnosis/`;
17. the prior current-train-split SFT retry under
   `reports/public-sample/a100-current-train-split-sft-retry/`;
18. the current-manifest SFT v3 prediction-only baseline under
   `reports/public-sample/a100-current-manifest-sft-v3-prediction-baseline/`;
19. the bounded SFT v3 retry after SSH recovery, now a prior-manifest model
   source, under
   `reports/public-sample/a100-form-fill-remediation-sft-v3-retry-after-ssh-recovery/`.

Current formal public sample data boundary:

| item | value |
| --- | --- |
| manifest | `public-sample-20260617T152259Z` |
| public sample | 240 seeds / 675 SFT rows / 2046 DPO pairs |
| split counts | train 261 / dev 207 / test 207 |
| latest evaluated manifest | `public-sample-20260617T152259Z` |
| latest model run type | prediction-only retry on the scaled dev/test split using the existing `a100-current-train-split-sft-retry` private adapter |
| latest model interpretation | `formal_public_heldout_partial_signal` |
| latest model evidence | `reports/public-sample/a100-scaled-public-sample-current-123-adapter-prediction-baseline-after-a100-recovery/` |
| latest slot canonicalization policy evidence | `reports/public-sample/slot-canonicalization-policy/` |
| latest slot canonicalization policy result | design-only policy evidence: slot keys are comparatively stable, while slot values and `normalized_command` dominate current strict residuals; no data/training/evaluator change |
| latest slot canonicalization recommended next step | `materialize-canonical-slot-boundary-candidates` before formal merge, postprocessor implementation, or training retry |
| latest safety repair candidate-design review evidence | `reports/public-sample/safety-repair-candidate-design-review/` |
| latest safety repair candidate-design review result | 1 row-backed theme ready for later bounded materialization proposal, 1 policy-scoped theme, 1 broad unsafe-action theme deferred to policy design; review-only, not data approval |
| latest safety repair candidate-design review recommended next step | `propose_clarify_confirmation_safety_repair_materialization_after_review` |
| latest safety repair candidate-design evidence | `reports/public-sample/safety-repair-candidate-design/` |
| latest safety repair candidate-design result | 3 public-safe design themes anchored by 1 current unsafe false negative; design-only, no seed materialization/data/training/evaluator change |
| latest safety repair candidate-design recommended next step | `review_safety_repair_candidates_before_materialization`, now completed as review-only evidence |
| latest residual-driven remediation target selection evidence | `reports/public-sample/remediation-target-selection/` |
| latest residual-driven remediation target selection | selected `safety-repair-unsafe-false-negative` first and `slot-value-canonicalization-policy` second; recommendation source only, no training/data/evaluator change |
| latest residual-driven recommended next change | `design-safety-repair-candidates`, now completed as design-only evidence |
| latest layered evaluation evidence | `reports/public-sample/layered-eval/` |
| latest residual diagnosis evidence | `reports/public-sample/residual-diagnosis/` |
| latest scaled-manifest prediction baseline | observed after A100 recovery; strict exact remains partial and lower than the prior-boundary adapter evidence |
| latest scaled-manifest baseline evidence | `reports/public-sample/a100-scaled-public-sample-current-123-adapter-prediction-baseline-after-a100-recovery/` |
| latest scaled-manifest residual cluster interpretation | `scaled_current_123_residual_clusters_clarify_slots_top_cluster` |
| latest scaled-manifest residual cluster evidence | `reports/public-sample/scaled-current-123-adapter-residual-cluster-inspection/` |
| latest scaled remediation target selection evidence | `reports/public-sample/scaled-residual-remediation-target-selection/` |
| latest scaled remediation target selection | `clarify/slots`, 78 residual rows / 78 residual fields, from `clarify|clarify|ambiguous_request|confirm:true|slots:ambiguity` |
| latest scaled clarify materialization evidence | `reports/public-sample/scaled-clarify-slot-boundary-candidate-materialization/` |
| latest scaled clarify materialization result | 9 standalone candidate seeds / 27 candidate SFT rows / no DPO pairs; standalone-only, no formal merge or model-quality claim |
| latest scaled clarify candidate-design evidence | `reports/public-sample/scaled-clarify-slot-boundary-candidate-design/` |
| latest scaled clarify candidate-design result | 3 public-safe candidate themes covering 28 source families / 78 source-family incidence; design-only source for the standalone materialization |
| latest scaled-manifest residual diagnosis interpretation | `scaled_current_123_residuals_slot_and_normalized_command_dominant` |
| latest scaled-manifest residual diagnosis evidence | `reports/public-sample/scaled-current-123-adapter-residual-diagnosis/` |
| prior scaled-manifest blocked baseline evidence | `reports/public-sample/a100-scaled-public-sample-current-123-adapter-prediction-baseline/` |
| latest scaled merge evidence | `reports/public-sample/scaled-public-sample-merge/` |
| latest standalone scaled candidate evidence | `reports/public-sample/scaled-public-sample-candidate-materialization/` |
| latest standalone scaled candidate data | 138 candidate seeds / 414 candidate SFT rows / no DPO pairs |
| latest strategic-design evidence | `reports/public-sample/scaled-public-sample-and-tiered-eval-design/` |
| latest strategic-design interpretation | `scale_data_and_diagnose_by_tier_before_another_training_retry` |
| latest prior-manifest diagnosis interpretation | `current_sft_retry_tradeoff_diagnosis_confirmation_regression_after_safety_recovery` |
| latest prior-manifest diagnosis evidence | `reports/public-sample/current-train-split-sft-retry-tradeoff-diagnosis/` |
| latest candidate-design evidence | `reports/public-sample/current-retry-confirmation-preservation-candidate-design/` |
| latest data-materialization evidence | `reports/public-sample/current-retry-confirmation-preservation-public-sample-merge/` |
| latest readiness evidence | `reports/public-sample/current-123-train-split-sft-retry-readiness/` |
| prior SFT v3 retry manifest | `public-sample-20260616T074315Z` |
| prior SFT v3 retry interpretation | `form_fill_sft_v3_partial_improvement_with_safety_regression_risk` |

The metric table below is the latest observed model evidence, bound to
`public-sample-20260617T152259Z`. It is a prediction-only A100 recovery retry
using the existing private `a100-current-train-split-sft-retry` adapter trained
on `public-sample-20260617T045941Z`. It did not train, repair predictions,
normalize slots, change prompts, relax metrics, or publish a checkpoint/adapter.
Because the source adapter and target evaluation manifest differ, this is a
new-boundary baseline and not a clean improvement/regression comparison against
the prior current-123 metrics.

Scaled-manifest current-123 adapter prediction-only metrics:

| split | contract_exact_match | strict slot_f1 | slot_f1_soft | route_accuracy | safety_recall | json_valid_rate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| dev | 0.2464 | 0.2874 | 0.6372 | 0.9614 | 1.0000 | 1.0000 |
| test | 0.2029 | 0.2593 | 0.6108 | 0.9758 | 1.0000 | 1.0000 |

Strict `contract_exact_match` and strict `slot_f1` remain canonical diagnostic
metrics, but they are no longer sufficient as the only success surface for the
next phase. `slot_f1_soft` is diagnostic only and must not be used as recovery,
semantic-equivalence, or production-readiness evidence. `json_valid_rate=1.0`
means the output shape is stable; it is not enough to claim contract recovery.
The next evaluator phase should report both strict metrics and deterministic
layered metrics so reviewers can separate executable contract quality from
canonical full-string consistency.

That layered evaluator and residual diagnosis phase is now complete under
`reports/public-sample/layered-eval/` and
`reports/public-sample/residual-diagnosis/`. It is additive evaluation evidence
only: no clarify candidate merge, data expansion, A100 training, prediction
rerun, DPO/GRPO run, LoRA parameter change, evaluator relaxation, slot repair,
checkpoint/adapter release, held-out recovery claim, production-readiness
claim, safety-readiness claim, or live-browser benchmark claim was performed.
`contract_exact_match_strict` preserves the original strict evaluator output:
dev/test remain `0.2464` / `0.2029`. The new executable-contract pass rates
are `0.2705` / `0.2512`, schema validity remains `1.0000` / `1.0000`, and
bounded deterministic slot-value normalization does not improve the current
slot-value F1 (`0.2821` / `0.2390`, equal to exact slot-value F1). Residual
diagnosis still points to strict slot values and normalized commands as the
dominant residual surfaces: dev has `slot_value=160` and
`normalized_command=91`; test has `slot_value=176` and
`normalized_command=103`.

The residual-driven remediation target selection is now complete under
`reports/public-sample/remediation-target-selection/`. It reads the committed
layered-eval and residual-diagnosis artifacts only, ranks dev/test failure
families, maps them to remediation strategies, and selects at most two next
targets. The top failure families are `slot_value_mismatch=336`,
`normalized_command_mismatch=194`, `extra_slot=16`, `missing_slot=13`, and
`route_mismatch=13` (with `task_type_mismatch=13` at the same count). Because
the test split contains one unsafe false negative, the first recommended target
is `safety-repair-unsafe-false-negative` with proposed change
`design-safety-repair-candidates`; the second is
`slot-value-canonicalization-policy` with proposed change
`design-slot-canonicalization-policy`. This phase is target-selection only: no
training, prediction rerun, data mutation, split change, evaluator metric
change, evaluator relaxation, LLM judge, semantic-equivalence scoring,
prediction repair, checkpoint/adapter release, held-out recovery claim,
production-readiness claim, safety-readiness claim, or live-browser benchmark
claim was performed.

The safety repair candidate design is now complete under
`reports/public-sample/safety-repair-candidate-design/`. It is design-only and
reads the committed residual-driven target selection, layered-eval, residual
diagnosis, and current public gold/prediction boundary evidence. It records one
current unsafe false negative, `family-clarify-test-1-aug-1`, where a
`clarify/clarify` contract with `confirmation_required=true` was downgraded to
`search/search_web` with `confirmation_required=false`. The report defines
three public-safe candidate themes: `clarify_confirmation_preservation`,
`confirmation_required_boundary`, and `unsafe_action_denial_boundary`. It
does not materialize seed rows, mutate the formal public sample, change splits,
train, rerun predictions, run DPO/GRPO, change prompts, alter evaluator
metrics, relax the evaluator, use an LLM judge, run semantic-equivalence
scoring, repair predictions, release adapters/checkpoints, or claim held-out
recovery, production readiness, safety readiness, safety improvement, or
live-browser benchmark improvement. The recommended next step is
`review_safety_repair_candidates_before_materialization`.

The safety repair candidate design review is now complete under
`reports/public-sample/safety-repair-candidate-design-review/`. It is
review-only evidence, not materialization approval. It reviews the three
safety repair themes and keeps `approved_for_materialization=false` for all of
them. `clarify_confirmation_preservation` is directly row-backed by
`family-clarify-test-1-aug-1` and is ready only for a later bounded
materialization proposal. `confirmation_required_boundary` is partially
supported and should remain policy-scoped if proposed later. The broader
`unsafe_action_denial_boundary` theme is deferred to a separate safety-policy
design before any materialization. This phase does not generate seed rows,
mutate the formal public sample, change splits, train, rerun predictions, run
DPO/GRPO, change prompts, alter evaluator metrics, relax the evaluator, use an
LLM judge, run semantic-equivalence scoring, repair predictions, release
adapters/checkpoints, or claim held-out recovery, production readiness, safety
readiness, safety improvement, or live-browser benchmark improvement.

The slot canonicalization policy is now complete under
`reports/public-sample/slot-canonicalization-policy/`. It is design-only policy
evidence, not data approval and not model-quality evidence. It records that
slot keys are comparatively stable (`slot_key_f1` dev/test `0.9872` / `0.9769`),
while strict slot values and `normalized_command` dominate current strict
residuals (`slot_value_mismatch=336`, `normalized_command_mismatch=194`). The
policy defines canonical slot-key aliases, non-equivalence boundaries,
conservative slot-value normalization guidance, diagnostic/display positioning
for `normalized_command`, and the model-target vs deterministic-postprocessor
boundary. It does not mutate the formal public sample, add SFT/DPO rows, change
splits, train, rerun predictions, run on A100, change prompts, alter evaluator
metrics, relax strict exact, use an LLM judge, run semantic-equivalence scoring,
repair predictions, release adapters/checkpoints, or claim held-out recovery,
model improvement, production readiness, safety readiness, or live-browser
benchmark improvement. The recommended next bounded step is
`materialize-canonical-slot-boundary-candidates`.

The latest strategic design is now complete under
`reports/public-sample/scaled-public-sample-and-tiered-eval-design/`. It is a
design-only pivot after the current-123 retry: it records the current 102-seed /
261-SFT / 881-DPO boundary, the current 123 train rows, a review target of 240
seeds, family-balance guidance, augmentation-depth guidance, and a diagnostic
tiered-evaluation ladder. It does not materialize seeds, rebuild SFT/DPO rows,
train, predict, change prompts, normalize slots, repair predictions, relax
evaluator metrics, or claim model recovery. The recommended next bounded phase,
if the project continues, is reviewed materialization of scaled public-sample
candidates, not another blind SFT retry.

The standalone scaled public-sample candidate materialization is now complete
under `reports/public-sample/scaled-public-sample-candidate-materialization/`.
It materializes `138` public-safe candidate seeds and `414` derived SFT
candidate rows: `118` core-family candidates (`search=20`, `navigation=17`,
`form_fill=3`, `extract=25`, `clarify=33`, `blocked_payment=20`) plus `20`
confirmation-boundary overlay candidates. This phase does not merge the formal
public sample, rebuild formal SFT/DPO artifacts, generate DPO pairs, train,
predict, change prompts, change evaluator metrics, normalize slots, repair
predictions, release checkpoints/adapters, or claim model recovery.

The scaled public-sample formal merge is now complete under
`reports/public-sample/scaled-public-sample-merge/`. It promoted those `138`
reviewed candidate seeds into the formal public sample, preserved their
train/dev/test split labels, and rebuilt seed/SFT/DPO/manifest artifacts. This
phase still did not train, predict, run on A100, change prompts, change
evaluator metrics, normalize slots, repair predictions, release
checkpoints/adapters, or claim model recovery. Its main effect is a new formal
manifest boundary; model evidence must be regenerated in a later explicit phase
before any quality claim is made.

The first scaled-manifest prediction-only baseline attempt remains as historical
blocked evidence under
`reports/public-sample/a100-scaled-public-sample-current-123-adapter-prediction-baseline/`.
It targeted `public-sample-20260617T152259Z` with the existing private
`a100-current-train-split-sft-retry` adapter whose source training boundary was
`public-sample-20260617T045941Z`, but stopped before private prediction because
the configured A100 SSH alias timed out. No private override was created, no GPU
job was launched, no dev/test predictions were written, and no strict metrics
were generated from that blocked attempt.

After A100 connectivity recovered, the bounded recovery retry completed under
`reports/public-sample/a100-scaled-public-sample-current-123-adapter-prediction-baseline-after-a100-recovery/`.
It generated dev/test predictions and strict metrics on the scaled 207-row
held-out splits without training. The result is `formal_public_heldout_partial_signal`,
not strict recovery: dev/test exact are `0.2464` / `0.2029`, strict slot F1 are
`0.2874` / `0.2593`, and JSON validity remains `1.0000`. The sharp exact/slot
drop indicates that the prior adapter does not transfer cleanly to the scaled
boundary; the next bounded phase should diagnose residual families on this
manifest before any paired SFT retry.

That scaled-manifest residual-family diagnosis is now complete under
`reports/public-sample/scaled-current-123-adapter-residual-diagnosis/`. It is
diagnosis-only: no A100 job, training, prediction rerun, data mutation, prompt
change, evaluator relaxation, slot normalization, prediction repair, checkpoint
release, adapter release, production-readiness claim, or live-browser benchmark
claim was performed. The diagnosis found `321` strict residual rows (`156` dev /
`165` test). Residual fields are dominated by `slots=304` and
`normalized_command=194`, while task/route mismatches are much smaller
(`task_type=13`, `route=13`), safety field mismatches are `10`, and
confirmation mismatches are `6`. The tiered interpretation is therefore:
schema validity, route, safety recall, and confirmation are comparatively
strong; strict slot and full-contract exact remain weak. The next bounded phase,
if the project continues, should inspect scaled residual clusters before data
design or paired SFT retry.

That scaled-manifest residual-cluster inspection is now complete under
`reports/public-sample/scaled-current-123-adapter-residual-cluster-inspection/`.
It is analysis-only: no A100 job, training, prediction rerun, data mutation,
prompt change, evaluator relaxation, semantic-equivalence scoring, slot
normalization, prediction repair, checkpoint release, adapter release,
production-readiness claim, or live-browser benchmark claim was performed. The
inspection found `29` residual clusters and verified source-count consistency
for `321` residual rows / `540` residual fields. The top clusters are
`clarify/slots=78`, `blocked/slots=51`, `search/slots=51`,
`form_fill/slots=50`, and `blocked/normalized_command=47`. The next bounded
phase should select or design a remediation target from these ranked clusters;
it should not jump directly to training or evaluator changes.

The scaled residual remediation target selection is now complete under
`reports/public-sample/scaled-residual-remediation-target-selection/`. It is
target-selection only: no A100 job, training, prediction rerun, data mutation,
prompt change, evaluator relaxation, semantic-equivalence scoring, slot
normalization, prediction repair, checkpoint release, adapter release, or model
recovery claim was performed. It selected the largest non-safety strict residual
target, `clarify|clarify|ambiguous_request|confirm:true|slots:ambiguity` /
`slots`, with `78` residual rows / `78` residual fields across dev/test. The
`blocked/slots` cluster remains explicitly deferred to a dedicated safety
boundary phase. The recommended next bounded phase was public-safe clarify
slot-boundary candidate design.

The scaled clarify slot-boundary candidate design is now complete under
`reports/public-sample/scaled-clarify-slot-boundary-candidate-design/`. It is
design-only: no public seed rows, SFT rows, DPO pairs, manifest rebuild,
training, prediction, prompt change, evaluator change, slot normalization,
prediction repair, adapter/checkpoint release, production-readiness claim,
held-out recovery claim, or live-browser claim was performed. It defines `3`
candidate themes: `clarify_search_or_extract_ambiguity`,
`clarify_navigation_or_form_fill_ambiguity`, and
`clarify_pronoun_or_context_missing`. Together they cover all `28` source
families and all `78` source-family incidence from the selected clarify cluster.
Accepted sketches preserve `task_type=clarify`, `route=clarify`,
`safety.allow=true`, `safety.reason=ambiguous_request`,
`confirmation_required=true`, and non-empty `slots.ambiguity`; rejected drift
sketches cover incorrect `search/search_web`, `navigate/open_url`,
`form_fill/fill_form`, and `blocked/deny` outputs. The next bounded phase, if
the loop continues after standalone materialization, should merge reviewed
clarify boundary candidates into a new formal public-sample manifest before any
paired SFT retry.

The standalone scaled clarify slot-boundary candidate materialization is now
complete under
`reports/public-sample/scaled-clarify-slot-boundary-candidate-materialization/`.
It materializes `9` public-safe candidate seeds and `27` derived SFT candidate
rows from the committed design: one train/dev/test seed per theme for
`clarify_search_or_extract_ambiguity`,
`clarify_navigation_or_form_fill_ambiguity`, and
`clarify_pronoun_or_context_missing`. Every candidate preserves
`task_type=clarify`, `route=clarify`, `safety.allow=true`,
`safety.reason=ambiguous_request`, `confirmation_required=true`, and non-empty
`slots.ambiguity`. This phase does not merge the formal public sample, rebuild
formal SFT/DPO artifacts, generate DPO pairs, train, predict, run on A100,
change prompts, change evaluator metrics, normalize slots, repair predictions,
release checkpoints/adapters, or claim model recovery. The previous
`merge-scaled-clarify-slot-boundary-candidates` continuation remains a
reviewed data option, but it is no longer the default next step. The current
residual-driven target-selection recommendation has now been executed as the
design-only `design-safety-repair-candidates` phase.

Recommended next bounded step:

- Status: review-only evidence is complete; any materialization still requires
  a separate bounded OpenSpec proposal.
- Inputs:
  `reports/public-sample/safety-repair-candidate-design-review/safety_repair_candidate_design_review.json`,
  `reports/public-sample/safety-repair-candidate-design-review/safety_repair_candidate_design_review.md`,
  and `reports/public-sample/safety-repair-candidate-design-review/manifest.json`.
- Recommended operation:
  `propose_clarify_confirmation_safety_repair_materialization_after_review`.
- Boundary: if continued, open a new bounded proposal only for the row-backed
  clarify confirmation theme or a separate safety-policy design phase for
  broader unsafe-action denial. Do not silently continue
  `merge-scaled-clarify-slot-boundary-candidates`, merge data, train, rerun
  prediction, run DPO/GRPO, adjust LoRA parameters, relax evaluators, repair
  predictions, repair slots, or overwrite historical scaled evidence.

Claim boundaries:

- The latest current-manifest model evidence includes one private SFT retry on
  the `public-sample-20260617T045941Z` 123-row train split plus dev/test
  prediction-only strict eval.
- The prior bounded SFT v3 retry did train a private A100 adapter on the
  previous public train split (`114` rows, including `21` form-fill remediation /
  confirmation-marker rows), but it is not released.
- No evaluator relaxation, prediction repair, slot normalization, or data
  mutation happened in the current retry evidence.
- No checkpoint, adapter, full private corpus, or live-browser benchmark is
  released from this repository.
- The project proves a repeatable post-training/evaluation path and a
  public-safe evidence surface; it does not prove production reliability,
  held-out recovery, or safety readiness.

Earlier residual-family diagnosis, target-selection refresh, and `form_fill`
SFT v3 readiness checks were completed for the prior form-fill remediation
manifest boundary, before blocked-payment and current-retry materialization
advanced the public sample again. That phase selected `form_fill` residuals,
especially the `normalized_command` / confirmation-marker cluster, and selected
the then-current public train split (`114` rows, including `21` merged
form-fill remediation / confirmation-marker rows) for a separate
`run-a100-form-fill-remediation-sft-v3` phase. It is historical setup evidence
now, not evidence that the current `public-sample-20260617T045941Z` boundary has
already been trained or evaluated.

An initial `run-a100-form-fill-remediation-sft-v3` execution attempt was opened
on 2026-06-16 but blocked before GPU inspection because the configured A100 SSH
alias timed out. After connectivity recovered, a separate retry performed fresh
GPU preflight, trained the private SFT v3 adapter, and generated dev/test
strict metrics. The retry is useful but incomplete: dev exact and strict
slot_f1 improved substantially, test exact improved modestly, but dev
`safety_recall` regressed from `0.6667` to `0.5556`.

The safety regression diagnosis is now complete under
`reports/public-sample/sft-v3-safety-regression-diagnosis/`. It compared the
prediction-only baseline and SFT v3 retry without training, generating
predictions, changing data, or relaxing the evaluator. The diagnosis found `21`
gold-stop rows across dev/test, `18` of them in `blocked_payment`. The SFT v3
retry introduced `1` dev `blocked_payment` regression and retained `3`
persistent dev `blocked_payment` misses; test recovered `1` prior
`blocked_payment` miss. The recommended next bounded phase is therefore to
design `blocked_payment` safety repair candidates before any data
materialization or training, not DPO, evaluator changes, public
checkpoint/adapter release, production-readiness claims, or live-browser
benchmark claims.

The `blocked_payment` repair-candidate design is now complete under
`reports/public-sample/blocked-payment-safety-repair-candidate-design/`. It is a
design-only artifact: `formal_public_sample_modified=false`,
`candidate_seed_rows_materialized=false`, and `dpo_pairs_generated=false`. It
defines `2` repair families covering `4` source rows: refund confirmation /
direct refund processing, and subscription charge confirmation. Both preserve
the accepted target shape as `blocked/deny` with `safety.reason="unsafe_payment"`
and document rejected drift shapes toward `clarify/clarify` and
`form_fill/fill_form`. The recommended next bounded phase is materializing these
reviewed repair candidates into public-safe seed rows and derived artifacts,
still without claiming model improvement until a later strict held-out
evaluation exists.

The bounded `blocked_payment` repair materialization is now complete. It added
2 formal train seed rows and rebuilt the public sample to
`public-sample-20260616T165835Z` with 100 seeds / 256 SFT rows / 864 DPO pairs.
The evidence lives under
`reports/public-sample/blocked-payment-safety-repair-public-sample-merge/` and
records `candidate_seed_rows=2`, `candidate_sft_rows=4`, and
`candidate_dpo_pairs=14`. This is data evidence only: no training, prediction,
evaluator change, safety improvement claim, model-quality claim, checkpoint or
adapter release, production-readiness claim, or live-browser benchmark claim.
The recommended next bounded phase is a current-manifest prediction-only
baseline or training-readiness check before any SFT retry.

The current-manifest SFT v3 prediction-only baseline is now complete under
`reports/public-sample/a100-current-manifest-sft-v3-prediction-baseline/`. It
uses the existing private SFT v3 adapter, records
`source_adapter_runtime=a100-form-fill-remediation-sft-v3`, and binds dev/test
strict metrics to `public-sample-20260616T165835Z`. It is not a training run and
does not prove the new blocked-payment repair rows have improved safety. The
remaining model-quality risk is unchanged: dev `safety_recall=0.5556`,
dev/test strict exact remain partial (`0.4638` / `0.3478`), and strict slot F1
remains partial (`0.5652` / `0.4976`). If the project continues, the next
bounded phase should be a training-readiness or retry-design step for the
current 118-row train split, with special attention to blocked-payment safety
false negatives.

The current-train-split SFT retry readiness step is now complete under
`reports/public-sample/current-train-split-sft-retry-readiness/`. It is
readiness-only evidence: no A100 training, prediction generation, dataset
mutation, prompt change, evaluator change, adapter/checkpoint release, safety
improvement claim, or model recovery claim. The dry-run selected all `118`
train rows and confirmed that the current train split includes `21` form-fill
repair rows plus `4` blocked-payment repair rows. It also creates a distinct
future retry runtime, `a100-current-train-split-sft-retry`, so a later training
attempt does not overwrite or blur the prior `a100-form-fill-remediation-sft-v3`
adapter evidence.

The bounded current-train-split SFT retry is now complete under
`reports/public-sample/a100-current-train-split-sft-retry/`. It trained a
private A100 adapter on all `118` train rows and evaluated dev/test with the
strict contract ladder. The result is a mixed partial signal: dev
`safety_recall` recovered from `0.5556` to `1.0000`, dev/test strict slot F1
improved, and test exact improved from `0.3478` to `0.4058`; however dev exact
regressed from `0.4638` to `0.4348`, dev confirmation accuracy dropped from
`0.9710` to `0.8986`, and test route/confirmation also slipped.

The current-train-split SFT retry trade-off diagnosis is now complete under
`reports/public-sample/current-train-split-sft-retry-tradeoff-diagnosis/`. It
is diagnosis-only evidence: no training, prediction generation, dataset
mutation, prompt change, evaluator change, adapter/checkpoint release, safety
improvement claim, model recovery claim, or production-readiness claim. The
diagnosis compared the current-manifest prediction-only baseline with the retry
row by row on the same `public-sample-20260616T165835Z` dev/test boundary. It
found that dev safety recovered `4` rows with `0` safety regressions, while
confirmation regressed `5` dev rows and `2` test rows. Exact-match movement is
mixed: dev has `2` exact recoveries and `4` exact regressions, while test has
`7` exact recoveries and `3` exact regressions. The dominant trade-off is
`confirmation_regression_after_safety_recovery`; the next bounded phase should
design `current-retry` confirmation-preservation candidates before any
additional training, DPO, evaluator change, public release, or production
claim.

The current-retry confirmation-preservation candidate design is now complete
under
`reports/public-sample/current-retry-confirmation-preservation-candidate-design/`.
It is design-only evidence: no seed rows, SFT rows, DPO pairs, manifest files,
local/private corpora, prompts, evaluator metrics, predictions, checkpoints,
or adapters were modified. It defines `2` candidate families covering `7`
source rows: `unsafe_payment_confirmation_preservation` covers `5` dev
`blocked_payment` rows where the accepted target remains `blocked/deny`,
`safety.reason="unsafe_payment"`, and `confirmation_required=true`;
`public_navigation_non_confirmation_preservation` covers `2` test navigation
rows where the accepted target remains `navigate/open_url`,
`safety.reason="public_readonly"`, and `confirmation_required=false`. This
design was later materialized by the bounded materialization phase below; by
itself it remains design-only evidence and no model-quality claim is allowed
until a later strict held-out evaluation exists.

The bounded current-retry confirmation-preservation materialization is now
complete. It added `2` formal train seed rows and rebuilt the public sample to
`public-sample-20260617T045941Z` with 102 seeds / 261 SFT rows / 881 DPO pairs.
The evidence lives under
`reports/public-sample/current-retry-confirmation-preservation-public-sample-merge/`
and records `candidate_seed_rows=2`, `candidate_sft_rows=5`, and
`candidate_dpo_pairs=17`. The two formal families preserve the reviewed target
shapes: `unsafe_payment_confirmation_preservation` keeps `blocked/deny`,
`safety.reason="unsafe_payment"`, and `confirmation_required=true`;
`public_navigation_non_confirmation_preservation` keeps `navigate/open_url`,
`safety.reason="public_readonly"`, and `confirmation_required=false`. This is
data evidence only: no training, prediction, evaluator change, slot
normalization, safety improvement claim, model-quality claim, checkpoint or
adapter release, production-readiness claim, or live-browser benchmark claim.

The current-123-row train-split SFT retry readiness step is now complete under
`reports/public-sample/current-123-train-split-sft-retry-readiness/`. It is
readiness-only evidence: no A100 training, prediction generation, dataset
mutation, DPO, prompt change, evaluator change, checkpoint/adapter release,
safety improvement claim, model-quality claim, production-readiness claim, or
live-browser benchmark claim. The dry-run selected all `123` train rows and
confirmed that the current train split includes `21` form-fill repair rows, `4`
blocked-payment repair rows, and `5` current-retry confirmation-preservation
rows. It also records that the current-train-split prediction configs require a
paired adapter trained for `public-sample-20260617T045941Z` before prediction
results can be interpreted as current-manifest model evidence.

The current-123-row train-split A100 SFT retry is now complete under
`reports/public-sample/a100-current-123-train-split-sft-retry/`. It trained a
private adapter on all `123` train rows and evaluated dev/test with the strict
contract ladder. The result is not strict exact recovery: dev/test exact are
`0.4348` / `0.3768`, strict slot F1 are `0.5580` / `0.5459`, and safety recall
is `1.0000` on both splits. This is current-manifest paired-adapter evidence,
but it does not release an adapter/checkpoint and does not claim production,
private-corpus, held-out recovery, or live-browser improvement. If the project
continues, the next bounded phase should diagnose current-123 residual families
and trade-offs before any additional data design or training.

The scaled-manifest residual-family diagnosis and residual-cluster inspection
are now complete for `public-sample-20260617T152259Z`. The scaled current-123
adapter evidence remains partial: dev/test `contract_exact_match` are `0.2464`
/ `0.2029`, strict slot F1 are `0.2874` / `0.2593`, and `slot_f1_soft` remains
diagnostic-only. The cluster inspection grouped `321` residual rows / `540`
residual fields into `29` clusters; the largest cluster is
`clarify|clarify|ambiguous_request|confirm:true|slots:ambiguity` on `slots`
with `78` residual rows.

The latest scaled bounded target-selection evidence is
`reports/public-sample/scaled-residual-remediation-target-selection/`. It
selects `clarify/slots` as the first remediation target and explicitly defers
`blocked/slots` to a dedicated safety-boundary phase. This is target-selection
evidence only: it does not run A100, train, predict, materialize data, change
prompts, relax evaluators, normalize slots, repair predictions, or claim model
recovery. That target-selection chain already produced clarify candidate design
and standalone materialization evidence. If the project continues from the
current review boundary, the newer residual-driven target-selection evidence
under `reports/public-sample/remediation-target-selection/` supersedes this as
the default next decision source. It should not default back to broad data
expansion, candidate merge, evaluator relaxation, or training.

**Residual-Driven Remediation Target Selection**:
A target-selection report that reads committed layered-eval and residual
diagnosis artifacts, ranks failure families, maps each family to a remediation
strategy, and selects at most two next bounded targets. It is not data
materialization, evaluator relaxation, prediction repair, model training, or
model-quality evidence.
_Avoid_: training plan, model improvement proof, safety readiness proof

## Language

**Voice2Task Post-Training**:
The training and evaluation context for converting Chinese spoken browser commands or ASR transcripts into browser task contracts. It is a separate project from the agent runtime that consumes those contracts.
_Avoid_: generic chat fine-tuning, voice assistant fine-tuning

**Post-Training Companion Project**:
A separate repository that trains, evaluates, and packages model adapters for another product without owning that product's runtime. In this project, the companion target is Voice-to-Browser Agent.
_Avoid_: submodule, plugin, runtime feature

**Voice-to-Browser Agent**:
The downstream agent system that executes validated browser task contracts from spoken commands. It provides source traces and an execution validation target, but does not own this project's training loop.
_Avoid_: voice assistant, browser-use-vision

**Browser Task Contract**:
A structured JSON object that represents a browser task request, route decision, safety decision, and confirmation behavior derived from a spoken command.
_Avoid_: prompt output, action script, raw command

**Speech-to-Contract Normalization**:
The first-phase model capability: mapping a Chinese spoken command or ASR transcript into a browser task contract. It does not select arbitrary skills or predict low-level GUI actions.
_Avoid_: skill routing, GUI action policy, general instruction following

**Seed Trace Corpus**:
The sanitized traces, fixtures, and adaptation evaluation artifacts imported from Voice-to-Browser Agent to bootstrap training and evaluation data. It is a source corpus, not the final train/dev/test dataset.
_Avoid_: raw user logs, production recordings, public benchmark

**Schema-Preserving Augmentation**:
Controlled expansion of seed trace examples that changes spoken phrasing while preserving the intended browser task contract and safety label.
_Avoid_: arbitrary synthetic data, paraphrase-only dataset

**Hard Negative Pair**:
A chosen/rejected training pair where the rejected contract is plausible but wrong, unsafe, underspecified, or routed incorrectly.
_Avoid_: random negative, invalid JSON only

**Public Sample Dataset**:
A small sanitized dataset committed to the repository so reviewers can inspect the task format and run smoke tests.
_Avoid_: full training set, private corpus

**Local Private Corpus**:
The complete training and evaluation corpus built on the developer's machine from sanitized local artifacts and optional private augmentation inputs. It is reproducible by script but not committed in full.
_Avoid_: hidden benchmark, public dataset

**Supervised Contract Tuning**:
The SFT stage that teaches a small language model to emit schema-valid browser task contracts from Chinese spoken commands or ASR transcripts.
_Avoid_: chat SFT, instruction tuning without schema targets

**Preference Contract Tuning**:
The DPO stage that teaches the model to prefer safer, more executable, and less ambiguous browser task contracts over plausible rejected contracts.
_Avoid_: reward hacking, generic RLHF, GUI action preference

**Rule Reward Stage**:
A later optional stage that may use rule-based rewards such as JSON validity, route correctness, safety correctness, and confirmation correctness. It is not part of the first-phase commitment.
_Avoid_: first-phase GRPO requirement, leaderboard claim

**Reference Model Family**:
The small Qwen instruction model family used as the first target for LoRA-based post-training. Exact checkpoints may change by experiment, but the first-phase model should be small enough for repeatable SFT/DPO runs and large enough to handle Chinese structured output.
_Avoid_: one-off closed model, chat-only baseline

**Primary Post-Training Stack**:
The Hugging Face Transformers, PEFT, and TRL path used for the first transparent SFT/DPO implementation. It is the default stack for readable experiments and public reproducibility.
_Avoid_: framework-locked training only, opaque training script

**Engineering Training Stack**:
An optional ms-swift-based route for larger or more operational training runs, especially on the A100 development machine. It must not replace the primary transparent stack in the first phase.
_Avoid_: first-phase dependency, hidden implementation

**Contract Evaluation Ladder**:
The first-phase success framework that evaluates model outputs at multiple layers: schema validity, task type, route decision, safety decision, confirmation behavior, slot extraction, and execution smoke.
_Avoid_: loss-only evaluation, live browser success only

**Layered Evaluator**:
A deterministic evaluation surface that reports executable browser task
contract quality alongside strict canonical metrics. It preserves strict
`contract_exact_match` unchanged and adds field-level, slot-level, safety, and
executable-contract metrics without LLM judging, semantic relaxation,
prediction repair, or metric substitution.
_Avoid_: soft exact replacement, LLM-as-judge scoring, production success rate

**Deterministic Slot Normalization**:
Bounded normalization rules used only for diagnostic or layered slot-value
metrics, such as conservative whitespace, punctuation, full-width/half-width,
case, verb-alias, and slot-key-alias handling. It must not change strict exact
metrics and must not equate materially different values.
_Avoid_: semantic equivalence, prediction repair, relaxed strict exact

**Execution Smoke**:
A lightweight downstream check that verifies generated browser task contracts can be consumed by Voice-to-Browser Agent fixtures or controlled validation paths. It is not the same as a full live-browser success benchmark.
_Avoid_: production success rate, live benchmark

## Example Dialogue

Developer: "Should we add SFT scripts to the Voice-to-Browser Agent repo?"

Domain expert: "No. Voice2Task Post-Training is a post-training companion project. It may import schemas and traces from Voice-to-Browser Agent, but it owns the training data, model adapters, and evaluation reports."

Developer: "Is the first model supposed to route Hermes skills or choose GUI clicks?"

Domain expert: "No. The first phase is speech-to-contract normalization: it turns Chinese spoken browser commands into browser task contracts."

Developer: "Can we publish all imported traces as the dataset?"

Domain expert: "No. The seed trace corpus comes from sanitized Voice-to-Browser Agent artifacts. The public repo should publish safe samples, dataset builders, manifests, and aggregate reports rather than raw private logs."

Developer: "Can we claim the whole training corpus is open?"

Domain expert: "No. The repository exposes a public sample dataset and reproducible builders. The full local private corpus is summarized by manifests and reports, not committed wholesale."

Developer: "Are we promising GRPO in the first release?"

Domain expert: "No. The first phase includes supervised contract tuning and preference contract tuning. A rule reward stage is future work unless a later change explicitly scopes it."

Developer: "Should the first implementation depend only on ms-swift?"

Domain expert: "No. The primary post-training stack is Transformers, PEFT, and TRL for transparent SFT/DPO experiments. ms-swift can be an engineering training stack for larger runs."

Developer: "Can we call the project successful if the loss goes down?"

Domain expert: "No. The project needs a contract evaluation ladder: schema, route, safety, confirmation, slots, and execution smoke. Loss is training telemetry, not the product metric."
