# supervised-contract-tuning Specification

## Purpose
Define how supervised LoRA tuning teaches Qwen-family small instruction models to emit canonical browser task contracts from Chinese spoken commands or ASR transcripts.
## Requirements
### Requirement: Train supervised contract adapters
The system SHALL run LoRA SFT experiments that train a Qwen-family small instruction model to emit browser task contracts from Chinese spoken commands or ASR transcripts.

#### Scenario: Run SFT training
- **WHEN** a developer launches SFT training with a valid config and train/dev dataset paths
- **THEN** the system trains a LoRA adapter, writes checkpoints to a configured output directory, and records the model, dataset manifest, hyperparameters, and training command

### Requirement: Keep SFT outputs contract-focused
The system SHALL format supervised targets as browser task contracts rather than free-form assistant responses.

#### Scenario: Prepare SFT examples
- **WHEN** the training data formatter converts dataset rows into model messages
- **THEN** the target assistant content is the canonical browser task contract JSON and not explanatory prose

### Requirement: Provide prompt-only and rule baselines
The system SHALL support baseline evaluation for a rule normalizer and a prompt-only model before comparing SFT outputs.

#### Scenario: Compare SFT against baselines
- **WHEN** the SFT report is generated
- **THEN** it includes baseline metrics for at least rule normalization and prompt-only generation when the required providers or fixtures are available

### Requirement: Export adapter metadata
The system SHALL export SFT adapter metadata without implying a public checkpoint release unless an explicit release artifact exists.

#### Scenario: Export SFT adapter summary
- **WHEN** SFT training completes
- **THEN** the system writes an adapter summary containing base model, adapter path, dataset manifest ID, metrics path, and release status

### Requirement: Run A100 public-sample SFT smoke
The system SHALL provide a bounded, opt-in A100 SFT smoke workflow that trains the existing Qwen-family LoRA SFT path on the committed public sample and writes all remote outputs under the approved private A100 project root.

#### Scenario: Launch smoke with explicit opt-in
- **WHEN** a developer launches the A100 SFT smoke with `--run-training` and a config whose `allow_heavy_training` is `true`
- **THEN** the system uses the configured public-sample manifest, writes adapter/checkpoint outputs under the configured A100 project directory, and records the base model, dataset manifest ID, hyperparameters, package versions, output paths, and training command in adapter metadata

#### Scenario: Reject accidental heavy training
- **WHEN** a developer launches the A100 SFT smoke without `--run-training` or with `allow_heavy_training` unset or false
- **THEN** the system does not download models or start training and instead emits dry-run metadata that clearly states no heavy training occurred

#### Scenario: Keep remote evidence private by default
- **WHEN** the A100 smoke run completes
- **THEN** raw checkpoints, adapters, caches, and logs remain out of git unless a later explicit release change approves a sanitized artifact

### Requirement: Export A100 trained-path public-sample predictions
The system SHALL provide a bounded prediction export workflow for the A100 public-sample SFT adapter path that emits only sanitized public-sample prediction rows for contract evaluation.

#### Scenario: Launch trained-path prediction with explicit opt-in
- **WHEN** a developer launches trained-path public-sample prediction with an explicit prediction opt-in and a configured private adapter path
- **THEN** the system loads the configured adapter path, generates prediction rows for the committed public sample, and writes a sanitized prediction JSONL artifact without copying checkpoints, adapters, raw logs, caches, or private remote paths into git

#### Scenario: Reject accidental private prediction
- **WHEN** a developer launches prediction without the explicit prediction opt-in or without a configured adapter path
- **THEN** the system does not load private model artifacts and instead emits a dry-run or fixture-mode result that clearly states no private adapter prediction occurred

#### Scenario: Record prediction provenance safely
- **WHEN** trained-path prediction output is prepared for public evidence
- **THEN** the system records the base model ID, model source label, dataset manifest ID, adapter release status, prediction source kind, and command summary using public-safe placeholders rather than private filesystem paths or host details

### Requirement: Use consistent contract-only SFT chat formatting
The system SHALL serialize real SFT training examples and trained-adapter prediction prompts with a consistent contract-only chat format that uses tokenizer chat templates when available and a deterministic fallback when unavailable.

#### Scenario: Serialize real SFT training examples
- **WHEN** the real SFT training path builds text examples from public-sample or private SFT rows
- **THEN** each example contains the contract-only system instruction, the user command or ASR transcript, and the canonical Browser Task Contract JSON assistant target using the same chat serialization policy used by prediction

#### Scenario: Serialize trained-adapter prediction prompts
- **WHEN** trained-adapter prediction builds a prompt for a public-sample row
- **THEN** the prompt contains the contract-only system instruction, the user command or ASR transcript, and a generation prompt for a Browser Task Contract JSON object without explanatory prose, Markdown, or GUI actions

#### Scenario: Fall back without heavy dependencies
- **WHEN** a tokenizer does not expose a chat template or local validation does not load a tokenizer
- **THEN** the system uses a deterministic plain-text fallback that preserves the same roles, contract-only instruction, and assistant generation boundary

### Requirement: Keep recovery predictions honest
The system SHALL keep trained-adapter output recovery focused on model prompt/training format and shall not replace invalid private-adapter outputs with rule-baseline, fixture-mode, or gold-contract predictions.

#### Scenario: Preserve invalid model output
- **WHEN** a private adapter emits invalid JSON or a non-contract JSON object
- **THEN** the prediction artifact preserves the sanitized model output as a schema failure candidate rather than substituting a valid fixture or rule-normalized contract

#### Scenario: Record recovery run provenance
- **WHEN** a recovery SFT or prediction run is prepared for public evidence
- **THEN** the metadata records the formatting policy, base model public ID, dataset manifest ID, prediction source kind, adapter release status, and command summary using public-safe placeholders

### Requirement: Run A100 post-recovery public-sample SFT rerun
The system SHALL support a bounded A100 post-recovery public-sample SFT rerun that uses the recovered contract-only chat formatting policy and keeps all remote model artifacts private.

#### Scenario: Launch post-recovery SFT rerun with recovered formatting
- **WHEN** a developer launches the post-recovery A100 SFT rerun with an explicit training opt-in and a private config rooted under the approved A100 project directory
- **THEN** the system trains on the committed public-sample SFT rows using the shared contract-only SFT training text policy and records formatting policy, model source, dataset manifest ID, package versions, GPU selection policy, command summary, and release status using public-safe placeholders

#### Scenario: Rerun private adapter prediction after recovery
- **WHEN** the post-recovery SFT adapter is used for private-adapter public-sample prediction
- **THEN** the system generates sanitized public-sample prediction rows with the shared contract-only prediction prompt policy and records `prediction_source_kind=private_a100_adapter` without copying adapters, checkpoints, raw logs, remote caches, host details, SSH details, secrets, or private paths into git

#### Scenario: Preserve rerun failures honestly
- **WHEN** the post-recovery private adapter emits invalid JSON, non-contract JSON, or malformed text
- **THEN** the prediction artifact preserves the sanitized model output as a schema-failure candidate rather than substituting fixture-mode, rule-baseline, or gold-contract predictions

### Requirement: Expose contract value constraints in SFT prompts
The system SHALL make the model-visible SFT training and prediction prompt explicitly state the legal Browser Task Contract task type and route values, route non-path semantics, and object-shaped slots requirement.

#### Scenario: Serialize constrained SFT training examples
- **WHEN** the formatter converts an SFT dataset row into training text
- **THEN** the system prompt in the rendered text MUST include the allowed `task_type` values, allowed `route` values, a statement that `route` is not a URL or path, and a statement that `slots` must be a JSON object rather than an array

#### Scenario: Serialize constrained prediction prompts
- **WHEN** the formatter builds a trained-adapter prediction prompt
- **THEN** the prompt MUST include the same contract value constraints and MUST NOT include the gold target contract

### Requirement: Record decoding policy for trained-adapter prediction
The system SHALL record public-safe decoding policy metadata for trained-adapter prediction exports without implying that decoding constraints repair model output.

#### Scenario: Export prediction metadata with decoding policy
- **WHEN** trained-adapter prediction metadata is produced
- **THEN** it MUST record greedy decoding status, configured `max_new_tokens`, raw decoded sidecar availability, and schema repair status using public-safe values

#### Scenario: Preserve raw model-output status
- **WHEN** a private adapter prediction is generated or metadata is written
- **THEN** the metadata MUST state that schema repair is not applied and MUST NOT claim that invalid predictions were converted into valid Browser Task Contracts

### Requirement: Prepare train-split overfit diagnostic prediction exports
The system SHALL provide a public-safe preparation path for train-split overfit diagnostic prediction exports without launching private A100 execution from the local preparation phase.

#### Scenario: Configure train-split diagnostic prediction
- **WHEN** a developer prepares the diagnostic prediction config
- **THEN** the committed template MUST use `prediction_split=train`, mark `overfit_diagnostic=true`, keep private paths as placeholders, and require a private override before remote execution

#### Scenario: Record prompt and decoding sidecars
- **WHEN** trained-adapter prediction rows are generated for the diagnostic path
- **THEN** the system MUST be able to write public-safe prompt snapshot, sanitized raw decoded summary, and generation trace artifacts without changing the prediction values used for schema metrics

#### Scenario: Preserve raw failure evidence
- **WHEN** model output is schema-invalid, truncated, non-JSON, or contract-like but wrong
- **THEN** the prediction artifact and sidecars MUST preserve sanitized failure evidence without replacing it with fixture, rule-baseline, or gold contracts

### Requirement: Inspect SFT objective masking before overfit claims
The system SHALL expose an objective-inspection result for the SFT data path before train-split overfit results are interpreted as evidence that assistant contract targets were learned, and SHALL fail closed when real label evidence is unavailable.

#### Scenario: Report objective mask status
- **WHEN** objective inspection runs on a public-sample SFT row
- **THEN** the output MUST report prompt/system/user mask status and assistant contract loss status only when labels from the actual inspected training path are available, otherwise it MUST set those fields to null and report `dependency_unavailable`, `tokenizer_unavailable`, or `labels_unavailable`

#### Scenario: Bound objective interpretation
- **WHEN** objective inspection cannot prove assistant-only or completion-only loss
- **THEN** the overfit diagnostic MUST report that loss improvement alone is not proof of Browser Task Contract learning

### Requirement: Run A100 train-split overfit diagnostic
The system SHALL support a bounded, explicitly authorized A100 train-split overfit diagnostic that uses the prepared diagnostic prediction contract and keeps all private runtime artifacts outside git.

#### Scenario: Launch real train-split diagnostic
- **WHEN** a developer launches the train-split diagnostic with an explicit prediction opt-in, a repo-external private override, and an idle A100 GPU under the approved private project root
- **THEN** the system MUST use `prediction_split=train`, `overfit_diagnostic=true`, `generalization_claim=false`, and generate train-split diagnostic predictions plus prompt snapshot, sanitized raw decoded summary, generation trace, and prediction metadata sidecars

#### Scenario: Reject unresolved or accidental diagnostic execution
- **WHEN** the diagnostic command is launched without explicit prediction opt-in, with unresolved template paths, or without a configured private adapter path
- **THEN** the system MUST NOT load private model artifacts or start remote prediction and MUST report that no private adapter diagnostic occurred

#### Scenario: Keep private A100 artifacts private
- **WHEN** the real diagnostic completes or fails
- **THEN** raw logs, checkpoints, adapters, caches, private overrides, host details, SSH details, private paths, tokens, and private corpus rows MUST remain outside committed artifacts

#### Scenario: Preserve diagnostic model output
- **WHEN** the private adapter emits schema-invalid, truncated, non-JSON, or contract-like but wrong output
- **THEN** the prediction artifact and sidecars MUST preserve sanitized failure evidence without replacing it with fixture-mode, rule-baseline, or gold contracts

### Requirement: Diagnose SFT target and template alignment
The system SHALL provide a public-safe local diagnostic for SFT target rendering, assistant target span evidence, label-mask evidence boundaries, chat-template policy, and adapter/base metadata alignment before another private A100 rerun is interpreted.

#### Scenario: Compare training and prediction rendering
- **WHEN** the diagnostic runs on committed public-sample SFT rows with SFT and prediction configs
- **THEN** it MUST render SFT training text and prediction prompt text for matching rows, record whether they share the same system/user prefix, record whether the prediction prompt excludes the gold target contract, and record whether the assistant target contract appears only in the training text

#### Scenario: Report assistant target and label-mask evidence separately
- **WHEN** the diagnostic can identify the assistant contract target span in rendered training text
- **THEN** it MUST report structural target-span evidence separately from true label-mask evidence and MUST mark true label-mask evidence as unavailable unless labels from the inspected training path are available

#### Scenario: Record chat-template policy evidence
- **WHEN** tokenizer chat-template rendering is unavailable or intentionally not loaded for local validation
- **THEN** the diagnostic MUST record deterministic fallback rendering, the shared formatting policy, and tokenizer-template absence as an evidence gap rather than inferring tokenizer-specific training behavior

#### Scenario: Compare adapter and base metadata safely
- **WHEN** prior prediction metadata and public config templates are provided
- **THEN** the diagnostic MUST compare public-safe base model placeholder status, model source, stack, prediction split, adapter gate status, and formatting-policy fields without exposing private adapter paths, private base-model paths, host details, or raw logs

### Requirement: Bound SFT alignment interpretation
The system SHALL prevent SFT alignment diagnostics from being interpreted as a model-quality, release, or rerun-success claim.

#### Scenario: Describe diagnostic result
- **WHEN** SFT target/template alignment evidence is reported
- **THEN** the report MUST state that the diagnostic does not run private prediction, does not retrain, does not repair outputs, and does not prove checkpoint release, adapter release, dev/test generalization, production readiness, or live-browser benchmark improvement

### Requirement: Inspect SFT label provenance from training path
The system SHALL expose a public-safe SFT label provenance inspection result that distinguishes tokenizer/template evidence, collator evidence, true label tensor provenance, and assistant-target loss-mask evidence before SFT objective claims are interpreted.

#### Scenario: Report unavailable labels without inference
- **WHEN** objective inspection runs without an inspectable tokenizer/collator label source
- **THEN** the output MUST set true label evidence fields to unavailable values, record why labels were unavailable, and state that loss improvement alone does not prove Browser Task Contract learning

#### Scenario: Report inspectable collator labels
- **WHEN** objective inspection receives labels produced by the inspected training-tokenizer/collator path
- **THEN** the output MUST record the row id, label source, tokenizer/template status, collator status, prompt token count, assistant token count, prompt mask status, assistant-target loss status, and loss-interpretation boundary without writing raw rendered training text

#### Scenario: Preserve non-real fixture evidence boundary
- **WHEN** local validation uses fixture tokenizer/collator labels instead of the real training runtime
- **THEN** the output MUST label the evidence source as fixture or simulated and MUST NOT treat it as a real A100/private-adapter training proof

### Requirement: Keep label provenance inspection opt-in and non-heavy by default
The system SHALL keep label provenance inspection from downloading models, loading private adapters, or starting A100 execution unless a later explicitly scoped runtime phase authorizes it.

#### Scenario: Run default local inspection
- **WHEN** a developer runs the local objective or label provenance inspection command against the public-sample manifest without explicit runtime opt-ins
- **THEN** the command MUST inspect committed public-sample rows only, avoid private adapter loads and heavy training, and emit structured unavailable states for missing tokenizer/collator dependencies

#### Scenario: Bound runtime interpretation
- **WHEN** the inspection result is missing real tokenizer/collator label provenance
- **THEN** any report or metadata that references it MUST state that the result does not prove checkpoint release, adapter release, held-out generalization, production readiness, or live-browser improvement

### Requirement: Prepare runtime SFT label provenance checks
The system SHALL provide a public-safe preparation path for real tokenizer/collator SFT label provenance checks without launching private runtime execution by default.

#### Scenario: Prepare runtime check template
- **WHEN** a developer prepares the runtime label provenance check configuration
- **THEN** the committed template MUST keep private paths unresolved, require a repo-external private override, record approved output-root policy, and state that no A100/private adapter execution occurs from the public template

#### Scenario: Reject unresolved runtime execution
- **WHEN** runtime label provenance inspection is requested without a private override, with unresolved template paths, or without explicit runtime opt-in
- **THEN** the command MUST NOT download models, load private adapters, connect to A100 infrastructure, or inspect private labels, and MUST emit a structured blocked/skipped status

#### Scenario: Record runtime readiness metadata
- **WHEN** the runtime preparation command evaluates config and manifest inputs
- **THEN** the output MUST record runtime check status, private override requirement status, output-root policy status, dependency policy, label provenance intent, prior evidence links, and claim boundaries without exposing private paths or host details

### Requirement: Preserve runtime label evidence boundary
The system SHALL keep runtime readiness separate from true label-mask evidence until labels from the real tokenizer/collator training path are inspected.

#### Scenario: Report prepared but not inspected
- **WHEN** a runtime label provenance check is prepared but not executed
- **THEN** the result MUST keep true label-mask fields unavailable, set `label_tensor_available=false`, and state that runtime readiness does not prove Browser Task Contract learning

#### Scenario: Bound later runtime execution
- **WHEN** a later authorized runtime phase performs real tokenizer/collator label inspection
- **THEN** it MUST write only sanitized public-safe summaries to git and keep private overrides, raw logs, checkpoints, adapters, caches, host details, tokens, and private corpus rows outside committed artifacts
