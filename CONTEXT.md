# Voice2Task Post-Training

Voice2Task Post-Training is a companion project for training and evaluating small language models that turn Chinese spoken browser commands into safe, schema-valid browser task contracts.

## Current Status Contract

As of 2026-06-16, the first project phase is closed as an evidence-backed
post-training and evaluation baseline, not as a production-ready model release.
The current public-facing truth surface is the A100 prediction-only formal
public held-out retry under
`reports/public-sample/a100-formal-public-heldout-prediction-after-a100-recovery/`.

Current formal public sample boundary:

| item | value |
| --- | --- |
| manifest | `public-sample-20260616T074315Z` |
| public sample | 98 seeds / 252 SFT rows / 850 DPO pairs |
| split counts | train 114 / dev 69 / test 69 |
| run type | prediction-only held-out evaluation |
| interpretation | `formal_public_heldout_partial_signal` |

Latest formal held-out metrics:

| split | contract_exact_match | strict slot_f1 | slot_f1_soft | route_accuracy | safety_recall | json_valid_rate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| dev | 0.3043 | 0.3913 | 0.7315 | 0.8551 | 0.6667 | 1.0000 |
| test | 0.2899 | 0.5072 | 0.7609 | 0.9130 | 0.9167 | 1.0000 |

Strict `contract_exact_match` and strict `slot_f1` remain the public headline
metrics. `slot_f1_soft` is diagnostic only and must not be used as recovery,
semantic-equivalence, or production-readiness evidence. `json_valid_rate=1.0`
means the output shape is stable; it is not enough to claim contract recovery.

Claim boundaries:

- No training was performed in the latest A100 recovery retry.
- No evaluator relaxation, prediction repair, slot normalization, or data
  mutation happened in that retry.
- No checkpoint, adapter, full private corpus, or live-browser benchmark is
  released from this repository.
- The project proves a repeatable post-training/evaluation path and a
  public-safe evidence surface; it does not prove production reliability.

Recommended next stage, if work continues, is a small residual-family diagnosis
and target selection phase. The current likely targets are `clarify` route
confusion and `blocked_payment` safety recall, but new data, SFT v3, DPO, or
metric changes should only follow after that diagnosis.

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
