# Voice2Task Post-Training

Voice2Task Post-Training is a companion project for training and evaluating small language models that turn Chinese spoken browser commands into safe, schema-valid browser task contracts.

## Current Status Contract

As of 2026-06-17, the first project phase is closed as an evidence-backed
post-training and evaluation baseline, not as a production-ready model release.
The public-facing truth surface has five current layers:

1. the current-retry confirmation-preservation candidate design under
   `reports/public-sample/current-retry-confirmation-preservation-candidate-design/`;
2. the current-train-split SFT retry trade-off diagnosis under
   `reports/public-sample/current-train-split-sft-retry-tradeoff-diagnosis/`;
3. the current-train-split SFT retry under
   `reports/public-sample/a100-current-train-split-sft-retry/`;
4. the current-manifest SFT v3 prediction-only baseline under
   `reports/public-sample/a100-current-manifest-sft-v3-prediction-baseline/`;
5. the bounded SFT v3 retry after SSH recovery, now a prior-manifest model
   source, under
   `reports/public-sample/a100-form-fill-remediation-sft-v3-retry-after-ssh-recovery/`.

Current formal public sample data boundary:

| item | value |
| --- | --- |
| manifest | `public-sample-20260616T165835Z` |
| public sample | 100 seeds / 256 SFT rows / 864 DPO pairs |
| split counts | train 118 / dev 69 / test 69 |
| latest evaluated manifest | `public-sample-20260616T165835Z` |
| latest model run type | private SFT retry on current 118-row train split, then dev/test strict eval |
| latest model interpretation | `current_train_split_sft_retry_partial_signal` |
| latest diagnosis interpretation | `current_sft_retry_tradeoff_diagnosis_confirmation_regression_after_safety_recovery` |
| latest diagnosis evidence | `reports/public-sample/current-train-split-sft-retry-tradeoff-diagnosis/` |
| latest candidate-design evidence | `reports/public-sample/current-retry-confirmation-preservation-candidate-design/` |
| prior SFT v3 retry manifest | `public-sample-20260616T074315Z` |
| prior SFT v3 retry interpretation | `form_fill_sft_v3_partial_improvement_with_safety_regression_risk` |

The metric table below is the current model evidence bound to
`public-sample-20260616T165835Z`. It trained one private adapter on the current
118-row train split, including the merged form-fill and blocked-payment repair
rows, then performed dev/test prediction-only strict evaluation with the
existing evaluator. It did not mutate data, repair predictions, normalize slots,
change prompts, relax metrics, or publish a checkpoint/adapter.

Current-train-split SFT retry formal held-out metrics:

| split | contract_exact_match | strict slot_f1 | slot_f1_soft | route_accuracy | safety_recall | json_valid_rate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| dev | 0.4348 | 0.5797 | 0.8671 | 0.9130 | 1.0000 | 1.0000 |
| test | 0.4058 | 0.5386 | 0.7682 | 0.8986 | 1.0000 | 1.0000 |

Strict `contract_exact_match` and strict `slot_f1` remain the public headline
metrics. `slot_f1_soft` is diagnostic only and must not be used as recovery,
semantic-equivalence, or production-readiness evidence. `json_valid_rate=1.0`
means the output shape is stable; it is not enough to claim contract recovery.

Claim boundaries:

- The latest current-manifest model evidence includes one private SFT retry on
  the current 118-row train split plus dev/test prediction-only strict eval.
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

The residual-family diagnosis, target-selection refresh, and `form_fill` SFT v3
readiness check are now complete for the current manifest. The selected bounded
target remains `form_fill` residuals, especially the `normalized_command` /
confirmation-marker cluster; `clarify` route confusion and `blocked_payment`
safety recall remain secondary risks. The readiness report selects the current
public train split (`114` rows, including `21` merged form-fill remediation /
confirmation-marker rows) and recommends a separate
`run-a100-form-fill-remediation-sft-v3` phase.

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
`safety.reason="public_readonly"`, and `confirmation_required=false`. The next
bounded phase may materialize these reviewed candidate sketches into
candidate-only public-safe rows, but no model-quality claim is allowed until a
later strict held-out evaluation exists.

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
