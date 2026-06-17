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
The system SHALL expose an objective-inspection result for the SFT data path before train-split overfit results are interpreted as evidence that assistant contract targets were learned, and SHALL fail closed when real label evidence is unavailable or prompt/system/user labels are not masked.

#### Scenario: Report objective mask status
- **WHEN** objective inspection runs on a public-sample SFT row
- **THEN** the output MUST report prompt/system/user mask status and assistant contract loss status only when labels from the actual inspected training path are available, otherwise it MUST set those fields to null and report `dependency_unavailable`, `tokenizer_unavailable`, or `labels_unavailable`

#### Scenario: Bound objective interpretation
- **WHEN** objective inspection cannot prove assistant-only or completion-only loss, or reports that prompt/system/user tokens are not masked
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

### Requirement: Run authorized A100 runtime SFT label provenance check
The system SHALL support a bounded, explicitly authorized A100 runtime label provenance check that inspects labels produced by the tokenizer/collator SFT data path while keeping private runtime artifacts outside committed files.

#### Scenario: Launch real runtime label provenance check
- **WHEN** a developer launches the runtime label provenance check with explicit runtime opt-in, a repo-external private override, and an idle A100 GPU under the approved private project root
- **THEN** the system MUST inspect labels from the configured tokenizer/collator SFT path, record real label tensor availability, label source kind, tokenizer/template status, collator status, prompt mask status, assistant-target loss status, package/runtime policy, and output-root policy without committing private paths or host details

#### Scenario: Reject unresolved or accidental runtime inspection
- **WHEN** the runtime check is launched without explicit runtime opt-in, with unresolved template paths, without a repo-external private override, or outside the approved A100 project-root policy
- **THEN** the system MUST NOT download models, load private adapters, connect to private infrastructure, inspect private labels, or write runtime evidence as successful, and MUST emit a structured blocked/skipped status

#### Scenario: Keep private runtime artifacts private
- **WHEN** the runtime label provenance check completes or fails
- **THEN** raw logs, checkpoints, adapters, caches, model snapshots, private overrides, host details, SSH details, private paths, tokens, and private corpus rows MUST remain outside committed artifacts

#### Scenario: Bound objective interpretation
- **WHEN** real runtime label provenance evidence is available
- **THEN** the system MUST state whether prompt/system/user tokens were masked and assistant contract tokens carried loss, and MUST NOT claim checkpoint release, adapter release, held-out generalization, production readiness, public full-corpus release, or live-browser benchmark improvement

### Requirement: Run authorized A100 assistant-only train-split rerun
The system SHALL support a bounded, explicitly authorized A100 train-split rerun that trains through the current assistant-only SFT label path and keeps all private runtime artifacts outside committed files.

#### Scenario: Launch assistant-only rerun training
- **WHEN** a developer launches the rerun with explicit heavy-training opt-in, a repo-external private override, and an idle A100 GPU under the approved private project root
- **THEN** the system MUST train only the public-sample train split through the primary Transformers, PEFT, and TRL SFT path with pretokenized assistant-only labels, record loss-mask policy metadata, and keep checkpoints, adapters, caches, raw logs, private paths, host details, SSH details, tokens, and private corpus rows out of committed artifacts

#### Scenario: Inspect current runtime objective path
- **WHEN** the rerun evidence is interpreted
- **THEN** the system MUST include objective/runtime label evidence from the current tokenizer/collator SFT path that states whether prompt/system/user tokens were masked and assistant Browser Task Contract tokens carried loss

#### Scenario: Reject unresolved or accidental rerun execution
- **WHEN** rerun training or prediction is launched without explicit opt-in, with unresolved template paths, without a repo-external private override, without an approved output root, or without a configured private adapter path
- **THEN** the system MUST NOT load private model artifacts, download models through an unintended path, start heavy training, start private prediction, or write successful rerun evidence

#### Scenario: Preserve private artifact boundary after rerun
- **WHEN** the rerun completes or fails
- **THEN** raw logs, checkpoints, adapters, model caches, private overrides, host details, private paths, tokens, and private corpus rows MUST remain outside committed artifacts
#### Scenario: Keep rerun scope train-internal
- **WHEN** the rerun prediction step emits public-safe evidence
- **THEN** the system MUST use `prediction_split=train`, `overfit_diagnostic=true`, `generalization_claim=false`, and preserve schema-invalid, truncated, non-JSON, or wrong-contract outputs without fixture, rule-baseline, or gold-contract replacement

### Requirement: Run authorized A100 required-field repair train-split rerun
The system SHALL support a bounded, explicitly authorized A100 train-split rerun after required-field prompt and schema guard repair while keeping all private runtime artifacts outside committed files.

#### Scenario: Launch required-field repair rerun
- **WHEN** a developer launches the rerun with explicit heavy-training opt-in, a repo-external private override, and an idle A100 GPU under the approved private project root
- **THEN** the system MUST train only the public-sample train split through the current assistant-only SFT label path and required-field prompt skeleton

#### Scenario: Predict with schema guard and bounded retry
- **WHEN** the rerun adapter is used for train-split prediction
- **THEN** the system MUST use `prediction_split=train`, `overfit_diagnostic=true`, `generalization_claim=false`, and the current schema guard/retry prediction path

#### Scenario: Preserve raw and retry evidence
- **WHEN** a prediction attempt is generated
- **THEN** the system MUST preserve raw attempt schema validity, retry attempt schema validity, validated output source, and final prediction status without replacing raw failures with fixture-mode, rule-baseline, or gold-contract predictions

#### Scenario: Reject unresolved or accidental execution
- **WHEN** rerun training or prediction is launched without explicit opt-in, with unresolved template paths, without a repo-external private override, without an approved output root, or without a configured private adapter path
- **THEN** the system MUST NOT load private model artifacts, download models through an unintended path, start heavy training, start private prediction, or write successful rerun evidence

#### Scenario: Keep private runtime artifacts private
- **WHEN** the rerun completes or fails
- **THEN** raw logs, checkpoints, adapters, model caches, private overrides, host details, SSH details, private paths, tokens, and private corpus rows MUST remain outside committed artifacts

### Requirement: Constrain contract decoding without coercive repair
The system SHALL make trained-adapter prediction retry prompts canonical, JSON-only, and explicit about legal Browser Task Contract values while preserving invalid model outputs as failures.

#### Scenario: Build canonical retry prompt
- **WHEN** schema guard retry is triggered after a schema-invalid prediction
- **THEN** the retry prompt MUST include a complete canonical Browser Task Contract JSON object skeleton, legal `task_type` and `route` enum values, required `safety.allow` boolean shape, and instructions forbidding Markdown, explanatory prose, code fences, path-like routes, and legacy enum aliases

#### Scenario: Preserve invalid retry output
- **WHEN** the retry attempt still emits Markdown, explanatory prose, illegal enum values, path-like routes, missing required fields, or otherwise schema-invalid output
- **THEN** the prediction artifact MUST preserve the raw and retry attempts as observed evidence, set `validated_output_schema_valid=false`, and MUST NOT substitute fixture-mode, rule-baseline, gold-contract, or locally coerced output

#### Scenario: Accept only schema-valid model output
- **WHEN** raw or retry model output parses to a Browser Task Contract that passes `BrowserTaskContract.from_dict()`
- **THEN** the prediction artifact MAY use that model output as the validated output source and record whether it came from the raw or retry attempt

### Requirement: Run authorized A100 strict-retry train-split prediction rerun
The system SHALL support a bounded, explicitly authorized A100 prediction-only train-split rerun after constrained decoding repair while keeping all private runtime artifacts outside committed files.

#### Scenario: Launch strict-retry prediction rerun
- **WHEN** a developer launches the rerun with explicit private-prediction opt-in, a repo-external private override, an existing private adapter path, and an idle A100 GPU under the approved private project root
- **THEN** the system MUST run only public-sample train-split prediction through the current strict retry/canonical Browser Task Contract prediction path

#### Scenario: Predict with strict retry and schema guard
- **WHEN** the private adapter is used for train-split prediction
- **THEN** the system MUST use `prediction_split=train`, `overfit_diagnostic=true`, `generalization_claim=false`, `schema_retry_enabled=true`, and the current strict whole-string retry JSON parser

#### Scenario: Preserve observed failures
- **WHEN** raw or retry prediction attempts are generated
- **THEN** the system MUST preserve raw attempt schema validity, retry attempt schema validity, validated output source, final prediction status, and invalid outputs without replacing them with fixture-mode, rule-baseline, gold-contract, or locally coerced predictions

#### Scenario: Keep private adapter artifacts private
- **WHEN** the prediction rerun completes or fails
- **THEN** raw logs, checkpoints, adapters, model caches, private overrides, host details, SSH details, private paths, tokens, and private corpus rows MUST remain outside committed artifacts

### Requirement: Constrain first-pass contract output emission
The system SHALL make trained-adapter first-pass prediction prompts expose a valid canonical Browser Task Contract one-shot and strict whole-object output boundaries without including row gold targets.

#### Scenario: Build first-pass constrained prediction prompt
- **WHEN** the formatter builds a trained-adapter prediction prompt for an SFT row
- **THEN** the prompt MUST include a valid canonical Browser Task Contract JSON one-shot, legal `task_type` and `route` enum values, required `safety.allow` boolean shape, and instructions that the first non-empty character must be `{`, the last non-empty character must be `}`, and Markdown/prose/code fences are forbidden

#### Scenario: Exclude gold contract from prediction prompt
- **WHEN** a prediction prompt is rendered for a row with a target Browser Task Contract
- **THEN** the prompt MUST NOT include target-only slot values, target-only normalized command text, or the full gold target contract

#### Scenario: Preserve fail-closed schema guard behavior
- **WHEN** raw or retry model output is non-JSON, JSON-fragment wrapped in Markdown/prose, schema-invalid, or uses illegal enum values
- **THEN** the prediction artifact MUST preserve the observed failure and MUST NOT replace it with fixture-mode, rule-baseline, gold-contract, alias-normalized, or locally coerced output

#### Scenario: Accept only schema-valid whole-object output
- **WHEN** first-pass raw model output parses as a whole JSON object and passes `BrowserTaskContract.from_dict()`
- **THEN** the prediction artifact MAY mark `validated_output_source=raw_attempt` and count the prediction as schema-valid

### Requirement: Run authorized A100 constrained-output train-split prediction rerun
The system SHALL support a bounded, explicitly authorized A100 prediction-only train-split rerun after constrained-output repair while keeping all private runtime artifacts outside committed files.

#### Scenario: Launch constrained-output prediction rerun
- **WHEN** a developer launches the rerun with explicit private-prediction opt-in, a repo-external private override, an existing private adapter path, and an idle A100 GPU under the approved private project root
- **THEN** the system MUST use `prediction_split=train`, `overfit_diagnostic=true`, `generalization_claim=false`, `schema_retry_enabled=true`, the current constrained-output shared prompt, and the current whole-string raw and retry JSON parsers

#### Scenario: Reuse existing private adapter without retraining
- **WHEN** this constrained-output rerun is executed
- **THEN** the system MUST NOT run SFT, DPO, GRPO, or any adapter-training command and MUST NOT create or commit a new adapter/checkpoint

#### Scenario: Block unresolved or unsafe private configuration
- **WHEN** prediction is launched without explicit opt-in, with unresolved template paths, without a repo-external private override, without an approved output root, or without a configured private adapter path
- **THEN** prediction MUST fail closed or remain blocked without producing misleading fixture-mode evidence

#### Scenario: Keep private A100 artifacts private
- **WHEN** the constrained-output prediction rerun completes or fails
- **THEN** raw logs, checkpoints, adapters, model caches, private overrides, host details, SSH details, private paths, tokens, and private corpus rows MUST remain outside committed artifacts

### Requirement: Expose route ontology constraints in SFT prompts
The system SHALL make SFT training and trained-adapter prediction prompts explicitly distinguish Browser Task Contract `route` execution-channel enum values from domains, topics, intents, URLs, or paths.

#### Scenario: Serialize training prompt with route ontology
- **WHEN** the formatter converts an SFT dataset row into training text
- **THEN** the system prompt in the rendered text MUST state that `route` is an execution channel from the allowed enum and MUST state that weather, shopping, email, media, URL hosts, and other domain/topic values belong in `task_type`, `slots`, or `normalized_command` rather than `route`

#### Scenario: Serialize prediction prompt with route ontology
- **WHEN** the formatter builds a trained-adapter prediction prompt
- **THEN** the prompt MUST include the same route ontology constraints and MUST NOT include the row-specific gold target contract

#### Scenario: Represent weather requests without inventing routes
- **WHEN** route ontology examples are visible in SFT or prediction prompts
- **THEN** they MUST show that a weather-style information request uses `task_type="search"` and `route="search_web"` rather than `route="weather"`

### Requirement: Run authorized A100 route-ontology train-split prediction rerun
The system SHALL support a bounded, explicitly authorized A100 prediction-only train-split rerun after route ontology prompt repair while keeping all private runtime artifacts outside committed files.

#### Scenario: Launch route-ontology prediction rerun
- **WHEN** a developer launches the rerun with explicit private-prediction opt-in, a repo-external private override, an existing private adapter path, and an idle A100 GPU under the approved private project root
- **THEN** the system MUST use `prediction_split=train`, `overfit_diagnostic=true`, `generalization_claim=false`, `schema_retry_enabled=true`, the current route ontology shared prompt, and the current whole-string raw and retry JSON parsers

#### Scenario: Reuse existing private adapter without retraining
- **WHEN** this route-ontology rerun is executed
- **THEN** the system MUST NOT run SFT, DPO, GRPO, or any adapter-training command and MUST NOT create or commit a new adapter/checkpoint

#### Scenario: Block unresolved or unsafe private configuration
- **WHEN** prediction is launched without explicit opt-in, with unresolved template paths, without a repo-external private override, without an approved output root, or without a configured private adapter path
- **THEN** prediction MUST fail closed or remain blocked without producing misleading fixture-mode evidence

#### Scenario: Keep private A100 artifacts private
- **WHEN** the route-ontology prediction rerun completes or fails
- **THEN** raw logs, checkpoints, adapters, model caches, private overrides, host details, SSH details, private paths, tokens, and private corpus rows MUST remain outside committed artifacts

### Requirement: Expose confirmation-required in SFT prompts
The system SHALL make `confirmation_required` visible as a required boolean Browser Task Contract field in shared SFT training text and trained-adapter prediction prompts.

#### Scenario: Serialize confirmation-aware SFT examples
- **WHEN** the formatter converts an SFT dataset row into training text
- **THEN** the rendered text MUST include `confirmation_required` in the required-field guidance or contract skeleton and MUST preserve the assistant target as canonical Browser Task Contract JSON rather than explanatory prose

#### Scenario: Serialize confirmation-aware prediction prompts
- **WHEN** the formatter builds a trained-adapter prediction prompt
- **THEN** the prompt MUST include `confirmation_required` as a required boolean field and MUST NOT include the gold target contract

#### Scenario: Show confirmation false in low-risk search example
- **WHEN** the shared prompt or canonical one-shot example demonstrates a low-risk weather/search command
- **THEN** the example MUST include `"confirmation_required": false` together with the legal `search_web` route and `search` task type

### Requirement: Run authorized A100 confirmation-required train-split rerun
The system SHALL support a bounded, explicitly authorized A100 train-split prediction rerun after local confirmation-required prompt repair while keeping all private runtime artifacts outside committed files.

#### Scenario: Launch confirmation-required rerun with explicit authorization
- **WHEN** a developer launches the rerun with explicit prediction opt-in, a repo-external private override, and an idle A100 GPU under the approved private project root
- **THEN** the system MUST use `prediction_split=train`, `overfit_diagnostic=true`, `generalization_claim=false`, `schema_retry_enabled=true`, and the current shared confirmation-required prompt without starting SFT, DPO, or GRPO training

#### Scenario: Reuse existing private adapter for prediction only
- **WHEN** the confirmation-required rerun is executed
- **THEN** it MUST use the existing private train-split adapter and MUST NOT create, publish, or commit checkpoints, adapters, raw logs, caches, private overrides, host details, SSH details, tokens, or private paths

#### Scenario: Preserve invalid model output
- **WHEN** raw or retry attempts omit `confirmation_required`, include Markdown/prose wrappers, or otherwise fail strict Browser Task Contract validation
- **THEN** the prediction artifact and sidecars MUST preserve sanitized failure evidence without filling `confirmation_required`, replacing outputs with fixtures, accepting JSON fragments as valid, or using gold-contract repair

#### Scenario: Reject unresolved or unsafe private configuration
- **WHEN** prediction is launched without explicit opt-in, with unresolved template paths, without a repo-external private override, without an approved output root, or without a configured private adapter path
- **THEN** prediction MUST fail closed or remain blocked without producing misleading fixture-mode evidence

### Requirement: Expose normalized-command canonicalization policy in SFT prompts
The system SHALL make SFT training text and trained-adapter prediction prompts expose a conservative `normalized_command` target-writing policy without including row-specific gold targets in prediction prompts.

#### Scenario: Serialize policy in SFT training text
- **WHEN** the formatter converts an SFT dataset row into training text
- **THEN** the rendered system prompt MUST state that `normalized_command` should be a concise canonical Chinese intent phrase rather than a verbatim transcript or ASR text

#### Scenario: Serialize policy in prediction prompts without gold leakage
- **WHEN** the formatter builds a trained-adapter prediction prompt
- **THEN** the prompt MUST include the same canonicalization guidance and MUST NOT include the row-specific gold target contract or static examples equal to the current row's public-sample gold `normalized_command`

#### Scenario: Show non-row-specific canonical examples without metric relaxation
- **WHEN** the shared prompt describes `normalized_command` examples
- **THEN** it MUST show non-row-specific category examples such as search/weather, navigation, confirmation-required form fill, and unsafe payment denial while stating that exact-match evaluation remains strict and predictions are not repaired or semantically re-scored

#### Scenario: Bound canonicalization-prompt claims
- **WHEN** public documentation or Human Briefs describe this prompt policy
- **THEN** they MUST NOT claim A100 execution, training or prediction rerun, evaluator metric change, semantic-equivalence scoring, checkpoint release, adapter release, held-out generalization, production readiness, public full-corpus release, model-quality improvement, or live-browser benchmark improvement

### Requirement: Run A100 normalized-command policy train-split rerun
The system SHALL support a bounded, explicitly authorized A100 prediction-only train-split rerun after normalized-command canonicalization prompt policy is visible, while keeping all private runtime artifacts outside git.

#### Scenario: Launch normalized-command policy rerun
- **WHEN** a developer launches the rerun with explicit A100 approval, a repo-external private override, an idle A100 GPU, and an approved private output root represented in public artifacts as `<a100_project_root>`
- **THEN** the system MUST use `prediction_split=train`, `overfit_diagnostic=true`, `generalization_claim=false`, `schema_repair_applied=false`, and generate private-adapter predictions plus public-safe prompt snapshot, raw decoded summary, generation trace, and prediction metadata sidecars

#### Scenario: Record normalized-command prompt policy visibility
- **WHEN** prediction metadata is generated for the rerun
- **THEN** it MUST record that the normalized-command canonical policy is visible, that prompt examples are non-row-specific, and that prediction prompts do not include row-specific gold target contracts except strings already present in the user input

#### Scenario: Reject unresolved or accidental execution
- **WHEN** the rerun command is launched without explicit prediction opt-in, with unresolved template paths, without a configured private adapter path, or outside the approved output root
- **THEN** the system MUST NOT load private model artifacts or start remote prediction and MUST report that no private adapter rerun occurred

#### Scenario: Keep private A100 artifacts private
- **WHEN** the real rerun completes or fails
- **THEN** raw logs, checkpoints, adapters, caches, private overrides, host details, SSH details, private paths, tokens, and private corpus rows MUST remain outside committed artifacts
#### Scenario: Preserve diagnostic model output
- **WHEN** the private adapter emits schema-invalid, truncated, non-JSON, contract-like but wrong, or strict-string-mismatched output
- **THEN** the prediction artifact and sidecars MUST preserve sanitized model evidence without replacing it with fixture-mode, rule-baseline, gold-contract predictions, semantic-equivalence labels, or repaired normalized-command strings

### Requirement: Expose public-readonly search contract policy in SFT prompts
The system SHALL make the shared SFT training and trained-adapter prediction prompt explicitly state the Browser Task Contract field policy for low-risk public-readonly search/weather requests.

#### Scenario: Serialize training prompt with public-readonly search policy
- **WHEN** SFT training text is rendered for a public-readonly weather or public information lookup row
- **THEN** the model-visible system prompt MUST state that public-readonly information lookup uses `task_type="search"`, `route="search_web"`, `safety.allow=true`, `safety.reason="public_readonly"`, `confirmation_required=false`, and object-shaped `slots.query`
- **AND** it MUST state that `task_type` remains one of the legal task enum values and MUST NOT reuse route enum values such as `search_web`

#### Scenario: Serialize prediction prompt without row-specific gold contract
- **WHEN** a trained-adapter prediction prompt is rendered
- **THEN** the prompt MUST include the public-readonly search policy
- **AND** it MUST NOT include the row-specific gold target contract or row-specific gold-only tokens beyond text already present in the user input

#### Scenario: Surface prompt constraint metadata
- **WHEN** prompt constraint metadata is recorded in prediction metadata, prompt snapshots, manifests, reports, or evidence packs
- **THEN** it MUST include explicit booleans for public-readonly search policy visibility, `public_readonly` safety reason visibility, search query slot guidance visibility, and task-type-not-route-enum guidance visibility

### Requirement: Run A100 public-readonly search policy train-split rerun
The system SHALL support a bounded, explicitly authorized A100 prediction-only train-split rerun after public-readonly search contract prompt policy is visible, while keeping all private runtime artifacts outside git.

#### Scenario: Launch public-readonly search policy rerun
- **WHEN** a developer launches the rerun with explicit A100 approval, a repo-external private override, an idle A100 GPU, and an approved private output root represented in public artifacts as `<a100_project_root>`
- **THEN** the system MUST use `prediction_split=train`, `overfit_diagnostic=true`, `generalization_claim=false`, `schema_repair_applied=false`, and generate private-adapter predictions plus public-safe prompt snapshot, raw decoded summary, generation trace, and prediction metadata sidecars

#### Scenario: Record public-readonly search prompt policy visibility
- **WHEN** prediction metadata is generated for the rerun
- **THEN** it MUST record that public-readonly search policy, `safety.reason=public_readonly`, `slots.query` guidance, and the `task_type`-is-not-`route` rule are visible, and that prediction prompts do not include row-specific gold target contracts except strings already present in the user input

#### Scenario: Reject unresolved or accidental execution
- **WHEN** the rerun command is launched without explicit prediction opt-in, with unresolved template paths, without a configured private adapter path, or outside the approved output root
- **THEN** the system MUST NOT load private model artifacts or start remote prediction and MUST report that no private adapter rerun occurred

#### Scenario: Keep private A100 artifacts private
- **WHEN** the real rerun completes or fails
- **THEN** raw logs, checkpoints, adapters, caches, private overrides, host details, SSH details, private paths, tokens, and private corpus rows MUST remain outside committed artifacts

#### Scenario: Preserve diagnostic model output
- **WHEN** the private adapter emits schema-invalid, truncated, non-JSON, contract-like but wrong, or strict-string-mismatched output
- **THEN** the prediction artifact and sidecars MUST preserve sanitized model evidence without replacing it with fixture-mode, rule-baseline, gold-contract predictions, semantic-equivalence labels, slot-normalized fields, or repaired strings

### Requirement: Repair public-readonly output-boundary and retry policy
The system SHALL make public-readonly search contract generation and retry prompts explicitly preserve a single-root Browser Task Contract JSON object without prose, Markdown, route-alias task types, or fields outside the root object.

#### Scenario: Serialize single-root public-readonly prompts
- **WHEN** the formatter builds SFT training text or prediction prompts
- **THEN** the system prompt MUST state that the output is exactly one JSON object, all eight top-level fields stay inside the same root object, no extra closing brace may appear before `normalized_command`, and no Markdown/prose wrapper is allowed

#### Scenario: Preserve public-readonly task type guidance
- **WHEN** the formatter builds a public-readonly search prompt
- **THEN** it MUST state that public-readonly search uses `task_type="search"` and `route="search_web"`, and MUST state that `search_web` is never a valid `task_type`

#### Scenario: Retry with strict JSON-only contract shape
- **WHEN** schema retry is triggered after an invalid prediction
- **THEN** the retry prompt MUST ask for exactly one minified Browser Task Contract JSON object, preserve all eight required fields inside the root object, prohibit prose/Markdown/code fences, and repeat the `task_type="search"` not `search_web` guidance

#### Scenario: Keep prompt repair local and bounded
- **WHEN** this repair is validated locally
- **THEN** it MUST NOT change strict parser semantics, repair historical predictions, normalize slots or strings, rerun private prediction, run A100, train a model, release checkpoints/adapters, or claim model recovery

### Requirement: Run A100 output-boundary retry-policy train-split rerun
The system SHALL support a bounded, explicitly authorized A100 prediction-only train-split rerun after output-boundary and retry-prompt policy repair, while keeping all private runtime artifacts outside git.

#### Scenario: Launch output-boundary retry-policy rerun
- **WHEN** a developer launches the rerun with A100 authorization, a repo-external private override, an idle A100 GPU, and an approved private output root represented in public artifacts as `<a100_project_root>`
- **THEN** the system MUST use `prediction_split=train`, `overfit_diagnostic=true`, `generalization_claim=false`, `schema_repair_applied=false`, `schema_retry_enabled=true`, and generate private-adapter predictions plus public-safe prompt snapshot, raw decoded summary, generation trace, and prediction metadata sidecars

#### Scenario: Record output-boundary and retry-prompt policy visibility
- **WHEN** prediction metadata or prompt snapshots are generated for the rerun
- **THEN** they MUST record that single-root JSON object guidance, no-premature-root-close guidance, whole-object boundary guidance, public-readonly `task_type="search"` not `search_web` guidance, and retry JSON-only guidance are visible

#### Scenario: Reject unresolved or accidental execution
- **WHEN** the rerun command is launched without explicit prediction opt-in, with unresolved template paths, without a configured private adapter path, outside the approved output root, or without explicit GPU placement
- **THEN** the system MUST NOT load private model artifacts or start remote prediction and MUST report that no private adapter rerun occurred

#### Scenario: Keep private A100 artifacts private
- **WHEN** the real rerun completes or fails
- **THEN** raw logs, checkpoints, adapters, caches, private overrides, host details, SSH details, private paths, tokens, and private corpus rows MUST remain outside committed artifacts

#### Scenario: Preserve diagnostic model output
- **WHEN** the private adapter emits schema-invalid, truncated, non-JSON, JSON-fragment, prose-wrapped, contract-like but wrong, or strict-string-mismatched output
- **THEN** the prediction artifact and sidecars MUST preserve sanitized model evidence without replacing it with fixture-mode, rule-baseline, gold-contract predictions, semantic-equivalence labels, slot-normalized fields, parser-relaxed outputs, or repaired strings

### Requirement: Repair schema retry wrapper boundary
The system SHALL make schema retry prompts explicitly reject prose, Markdown, and any text outside a single Browser Task Contract JSON root while preserving strict parser semantics.

#### Scenario: Build no-wrapper retry prompt
- **WHEN** schema retry is triggered after a schema-invalid prediction
- **THEN** the retry prompt MUST state that the response contains exactly one JSON object, the first non-whitespace character is `{`, the last non-whitespace character is `}`, and there is no text before or after that object

#### Scenario: Prohibit wrapper failure modes
- **WHEN** schema retry is triggered after a prose-wrapped, Markdown-wrapped, or fragment-like failure
- **THEN** the retry prompt MUST explicitly prohibit Markdown fences, headings, explanatory prose, natural-language prefaces, trailing analysis, and second JSON objects

#### Scenario: Preserve strict retry rejection
- **WHEN** a retry attempt still emits Markdown, explanatory prose, JSON fragments, missing required fields, illegal enum values, or otherwise schema-invalid output
- **THEN** the prediction artifact MUST preserve the invalid retry attempt, set `validated_output_schema_valid=false`, and MUST NOT extract, coerce, replace, normalize, or re-score the fragment

#### Scenario: Keep retry boundary repair local
- **WHEN** this repair is validated locally
- **THEN** it MUST NOT run A100, run training, rerun private prediction, change parser semantics, change evaluator metrics, repair historical predictions, normalize slots or strings, release checkpoints/adapters, or claim model recovery

### Requirement: Run A100 schema retry wrapper-boundary rerun
The system SHALL support a bounded, explicitly authorized A100 prediction-only train-split rerun after schema retry wrapper-boundary prompt hardening while keeping all private runtime artifacts outside git.

#### Scenario: Launch retry wrapper-boundary rerun
- **WHEN** a developer launches the rerun with A100 authorization, a repo-external private override, an idle A100 GPU, and an approved private output root represented in public artifacts as `<a100_project_root>`
- **THEN** the system MUST use `prediction_split=train`, `overfit_diagnostic=true`, `generalization_claim=false`, `schema_repair_applied=false`, `schema_retry_enabled=true`, and generate private-adapter predictions plus public-safe prompt snapshot, raw decoded summary, generation trace, and prediction metadata sidecars

#### Scenario: Record retry wrapper-boundary prompt visibility
- **WHEN** prediction metadata or prompt snapshots are generated for the rerun
- **THEN** they MUST record that retry no-prefix/no-suffix, no `Here is`, no trailing analysis, no second JSON object, first/last brace, and strict-parser rejection warning constraints are visible

#### Scenario: Keep private A100 artifacts private
- **WHEN** the real rerun completes or fails
- **THEN** raw logs, checkpoints, adapters, caches, private overrides, host details, SSH details, private paths, tokens, and private corpus rows MUST remain outside committed artifacts

#### Scenario: Preserve diagnostic model output
- **WHEN** the private adapter emits schema-invalid, missing-field, JSON-fragment, prose-wrapped, Markdown-wrapped, or otherwise invalid output
- **THEN** the prediction artifact and sidecars MUST preserve sanitized model evidence without replacing it with fixture-mode, rule-baseline, gold-contract predictions, parser-relaxed outputs, normalized fields, semantic-equivalence labels, or repaired strings

### Requirement: Preserve retry stop-boundary diagnostic boundary
The system SHALL preserve retry decoding stop-boundary diagnosis as a local evidence step before any future behavior-changing decoding or instrumentation work.

#### Scenario: Diagnose before changing decoding behavior
- **WHEN** A100 retry output remains prose-wrapped or Markdown-wrapped after prompt boundary hardening
- **THEN** the system MUST first document observed retry symptoms and missing retry generation trace evidence before changing decoding parameters, parser behavior, or prediction postprocessing

#### Scenario: Keep model output unchanged
- **WHEN** local diagnosis evidence is generated
- **THEN** the system MUST preserve existing predictions, raw decoded summaries, generation traces, metrics, schema guard summaries, and manifests as source evidence without extracting, coercing, replacing, normalizing, repairing, or re-scoring outputs

### Requirement: Instrument retry generation trace attempts
The system SHALL record attempt-level generation trace rows for trained-adapter prediction exports whenever schema retry is attempted.

#### Scenario: Record raw and retry trace rows
- **WHEN** a real trained-adapter prediction export runs with generation trace sidecars enabled and a schema-invalid raw attempt triggers schema retry
- **THEN** `generation_trace.jsonl` MUST include one `attempt=raw_attempt` row and one `attempt=retry_attempt` row for that input id, using the same token count, EOS visibility, max-token limit, strategy, and finish-state fields for each attempt

#### Scenario: Preserve retry behavior
- **WHEN** retry generation trace instrumentation is added
- **THEN** the system MUST NOT change retry prompt text, decoding parameters, strict parser semantics, schema guard source selection, final predictions, evaluator metrics, output repair behavior, or prediction re-scoring

#### Scenario: Keep historical evidence bounded
- **WHEN** public documentation or evidence describes retry generation trace instrumentation
- **THEN** it MUST state that historical A100 traces are not retroactively instrumented and that a future A100/private-adapter rerun is required to observe real retry stop-boundary behavior

### Requirement: Run A100 retry generation trace rerun
The system SHALL support a bounded, explicitly authorized A100 prediction-only train-split rerun after retry generation trace instrumentation while keeping all private runtime artifacts outside git.

#### Scenario: Launch retry trace rerun
- **WHEN** a developer launches the rerun with A100 authorization, a repo-external private override, an existing private adapter path, an idle A100 GPU, and an approved private output root represented in public artifacts as `<a100_project_root>`
- **THEN** the system MUST use `prediction_split=train`, `overfit_diagnostic=true`, `generalization_claim=false`, `schema_retry_enabled=true`, `schema_repair_applied=false`, and generate private-adapter predictions plus public-safe prompt snapshot, raw decoded summary, generation trace, and prediction metadata sidecars

#### Scenario: Record retry trace sidecars
- **WHEN** schema retry is attempted during the rerun
- **THEN** `generation_trace.jsonl` MUST preserve attempt-level trace rows with `attempt=raw_attempt` and `attempt=retry_attempt` for the affected row id, including generated token count, max token limit, EOS visibility, strategy, and finish state

#### Scenario: Keep private A100 artifacts private
- **WHEN** the real rerun completes or fails
- **THEN** raw logs, checkpoints, adapters, caches, private overrides, host details, SSH details, private paths, tokens, and private corpus rows MUST remain outside committed artifacts

#### Scenario: Preserve diagnostic model output
- **WHEN** the private adapter emits schema-invalid, missing-field, JSON-fragment, prose-wrapped, Markdown-wrapped, or otherwise invalid output
- **THEN** the prediction artifact and sidecars MUST preserve sanitized model evidence without replacing it with fixture-mode, rule-baseline, gold-contract predictions, parser-relaxed outputs, normalized fields, semantic-equivalence labels, or repaired strings

### Requirement: Instrument generation stop-boundary evidence
The system SHALL record public-safe stop-boundary evidence fields in trained-adapter generation trace rows without changing decoding, retry, parser, metric, or prediction output behavior.

#### Scenario: Record stop-boundary evidence fields
- **WHEN** a trained-adapter prediction export writes `generation_trace.jsonl`
- **THEN** each generation trace row MUST preserve the existing id, attempt, prediction source kind, strategy, sampling, max-token limit, generated token count, EOS visibility, and finish-state fields and MUST also include max-token-hit status, finish-state basis, stop-boundary evidence, and whether an actual model/generation stop reason was recorded

#### Scenario: Preserve prediction behavior
- **WHEN** stop-boundary evidence instrumentation is added
- **THEN** the system MUST NOT change decoding parameters, retry prompt text, strict parser semantics, schema guard source selection, final predictions, evaluator metrics, output repair behavior, prediction re-scoring, semantic-equivalence scoring, slot normalization, or training behavior

#### Scenario: Keep stop-reason claims conservative
- **WHEN** a trace row has `finish_state=no_eos_observed`
- **THEN** the row MUST make clear that the finish state is based on tokenizer EOS membership and MUST NOT claim an actual model/generation stop reason unless such a reason is explicitly recorded

### Requirement: Run A100 generation stop-boundary rerun
The system SHALL support a bounded A100 prediction-only train-split rerun after generation stop-boundary trace instrumentation while keeping all private runtime artifacts outside git.

#### Scenario: Launch stop-boundary rerun
- **WHEN** a developer launches the rerun with A100 authorization, a repo-external private override, an existing private adapter path, an idle A100 GPU, and an approved private output root represented in public artifacts as `<a100_project_root>`
- **THEN** the system MUST use `prediction_split=train`, `overfit_diagnostic=true`, `generalization_claim=false`, `schema_retry_enabled=true`, `schema_repair_applied=false`, and generate private-adapter predictions plus public-safe prompt snapshot, raw decoded summary, generation trace, prediction metadata, and leak-scan sidecars

#### Scenario: Record stop-boundary trace fields
- **WHEN** raw or retry generation trace rows are written during the rerun
- **THEN** each row MUST include generated token count, max-token limit, EOS visibility, finish state, max-token-hit status, finish-state basis, stop-boundary evidence, actual-stop-reason-recorded status, actual stop reason, strategy, sampling mode, prediction source kind, and attempt label when available

#### Scenario: Keep private A100 artifacts private
- **WHEN** the real rerun completes or fails
- **THEN** raw logs, checkpoints, adapters, caches, private overrides, host details, SSH details, private paths, tokens, and private corpus rows MUST remain outside committed artifacts

#### Scenario: Preserve diagnostic model output
- **WHEN** the private adapter emits schema-invalid, missing-field, JSON-fragment, prose-wrapped, Markdown-wrapped, or otherwise invalid output
- **THEN** the prediction artifact and sidecars MUST preserve sanitized model evidence without replacing it with fixture-mode, rule-baseline, gold-contract predictions, parser-relaxed outputs, normalized fields, semantic-equivalence labels, or repaired strings

### Requirement: Tighten schema-retry JSON-only output boundary
The system SHALL strengthen the local schema-retry prompt/output-boundary policy without changing strict parser, evaluator, training, or prediction repair behavior.

#### Scenario: Publish stricter retry prompt clauses
- **WHEN** the schema-retry prompt is generated for a schema-invalid raw attempt
- **THEN** the prompt MUST explicitly require the retry response to be exactly one JSON object, start with `{`, end with `}`, contain no Markdown/code fences/prose/prefix/suffix/trailing analysis, avoid second JSON objects, and avoid natural-language introductions such as Chinese "this/following" prefixes or "Here is"

#### Scenario: Report retry prompt boundary visibility
- **WHEN** retry prompt constraints are summarized in prediction metadata or prompt snapshots
- **THEN** the summary MUST expose machine-readable booleans for the stricter JSON-only boundary clauses, including exact-only output, no Markdown/code fences, no natural-language preface, no suffix/trailing analysis, no second object, and strict-parser rejection visibility

#### Scenario: Preserve strict retry parsing
- **WHEN** a retry response contains a valid Browser Task Contract embedded inside Markdown, prose, or other wrapper text
- **THEN** the strict parser MUST continue to reject it as a non-whole JSON-object retry attempt rather than extracting, repairing, coercing, normalizing, or re-scoring the embedded fragment

#### Scenario: Keep local phase private-runtime free
- **WHEN** this local retry boundary hardening phase is implemented
- **THEN** it MUST NOT run A100 prediction, train a model, release an adapter/checkpoint, change decoding parameters, change evaluator metrics, or rewrite prior A100 artifacts

### Requirement: Run A100 retry JSON-only boundary rerun
The system SHALL support a bounded A100 prediction-only train-split rerun after local retry JSON-only boundary hardening while keeping private runtime artifacts outside git.

#### Scenario: Launch retry-boundary rerun
- **WHEN** a developer launches the rerun with A100 authorization, a repo-external private override, an existing private adapter path, an idle A100 GPU, and an approved private output root represented in public artifacts as `<a100_project_root>`
- **THEN** the system MUST use `prediction_split=train`, `overfit_diagnostic=true`, `generalization_claim=false`, `schema_retry_enabled=true`, `schema_repair_applied=false`, the stricter retry JSON-only prompt policy, and generate private-adapter predictions plus public-safe prompt snapshot, raw decoded summary, generation trace, prediction metadata, and leak-scan sidecars

#### Scenario: Preserve strict retry semantics
- **WHEN** the private adapter emits retry output that is Markdown-wrapped, prose-wrapped, fragmentary, schema-invalid, or otherwise invalid
- **THEN** the prediction artifact and sidecars MUST preserve sanitized model evidence without extracting embedded contracts, repairing predictions, relaxing parser semantics, normalizing fields, re-scoring outputs, or replacing outputs with fixture or gold contracts

#### Scenario: Keep private A100 artifacts private
- **WHEN** the real rerun completes or fails
- **THEN** raw logs, checkpoints, adapters, caches, private overrides, host details, SSH details, private paths, tokens, and private corpus rows MUST remain outside committed artifacts

### Requirement: Harden schema-retry template decoding boundary
The system SHALL expose a machine-only schema-retry template boundary for retry prompts without changing strict parser, evaluator, training, or prediction repair behavior.

#### Scenario: Build machine-only retry template
- **WHEN** the schema-retry prompt is generated for a schema-invalid raw attempt
- **THEN** the prompt MUST identify the retry as a machine-only contract regeneration step, require exactly one root Browser Task Contract JSON object, prohibit explanatory dialogue/wrapper text, and preserve the existing strict JSON-only field and enum requirements

#### Scenario: Report retry template boundary visibility
- **WHEN** prediction metadata or prompt snapshots summarize retry behavior
- **THEN** they MUST expose machine-readable booleans for retry template mode, machine-only output boundary, no conversational answer mode, strict whole-object parser boundary, and whether chat-template wrapping is explicitly documented for the retry prompt

#### Scenario: Preserve strict parser behavior
- **WHEN** a retry response contains a valid Browser Task Contract embedded inside Markdown, prose, wrapper text, or explanatory text
- **THEN** the strict retry parser MUST continue to reject it as a non-whole JSON-object retry attempt rather than extracting, repairing, coercing, normalizing, re-scoring, or replacing the embedded fragment

#### Scenario: Keep phase local
- **WHEN** retry template boundary hardening is implemented
- **THEN** the phase MUST NOT run A100 prediction, train a model, release an adapter/checkpoint, change evaluator metrics, relax parsing, repair predictions, rewrite prior A100 artifacts, or claim model-quality improvement

### Requirement: Run A100 retry template boundary rerun
The system SHALL support a bounded A100 prediction-only train-split rerun after local retry template boundary hardening while keeping private runtime artifacts outside git.

#### Scenario: Launch retry template boundary rerun
- **WHEN** a developer launches the rerun with A100 authorization, a repo-external private override, an existing private adapter path, an idle A100 GPU, and an approved private output root represented in public artifacts as `<a100_project_root>`
- **THEN** the system MUST use `prediction_split=train`, `overfit_diagnostic=true`, `generalization_claim=false`, `schema_retry_enabled=true`, `schema_repair_applied=false`, the machine-only retry template boundary, strict parser semantics, and generate private-adapter predictions plus public-safe prompt snapshot, raw decoded summary, generation trace, prediction metadata, and leak-scan sidecars

#### Scenario: Preserve strict retry semantics
- **WHEN** the private adapter emits retry output that is Markdown-wrapped, prose-wrapped, fragmentary, schema-invalid, or otherwise invalid
- **THEN** the prediction artifact and sidecars MUST preserve sanitized model evidence without extracting embedded contracts, repairing predictions, relaxing parser semantics, normalizing fields, re-scoring outputs, or replacing outputs with fixture or gold contracts

#### Scenario: Keep private A100 artifacts private
- **WHEN** the real rerun completes, fails, or is blocked by GPU/runtime safety
- **THEN** raw logs, checkpoints, adapters, caches, private overrides, host details, SSH details, private paths, tokens, and private corpus rows MUST remain outside committed artifacts

#### Scenario: Enforce A100 placement safety
- **WHEN** the rerun is launched on A100 hardware
- **THEN** GPU and process occupancy MUST be inspected first, an idle GPU MUST be selected when available, `CUDA_VISIBLE_DEVICES` MUST be set explicitly, and other users' processes MUST NOT be killed, signaled, paused, reniced, or otherwise interrupted

### Requirement: Expose canonical search query slot target policy
The system SHALL make the shared SFT training and trained-adapter prediction prompt explicitly state the canonical slot target policy for public-readonly search/weather contracts without changing parser or evaluator semantics.

#### Scenario: Serialize prompt with compact query slot policy
- **WHEN** SFT training text or trained-adapter prediction prompt is rendered for public-readonly information lookup or weather search
- **THEN** the model-visible system prompt MUST state that search contracts use object-shaped `slots.query`
- **AND** it MUST state that the model MUST NOT split the same search query into ad hoc `city`, `date`, `topic`, or similar keys
- **AND** it MUST state that ordinary Chinese search query strings should be compact phrases such as `北京明天天气`, not artificial token-spaced strings such as `北京 明天 天气`
- **AND** it MUST state that this is target formatting guidance, not evaluator normalization, semantic-equivalence scoring, prediction repair, or re-score

#### Scenario: Surface search query slot policy metadata
- **WHEN** prompt constraint metadata is recorded in prediction metadata, prompt snapshots, manifests, reports, or evidence packs
- **THEN** it MUST include booleans for compact search query slot policy visibility and no-`city/date` search slot splitting visibility

### Requirement: Run compact search query policy prediction-only A100 rerun
The system SHALL support a bounded A100 prediction-only train-split rerun that exercises the current compact public-readonly search query slot target policy against an existing private adapter without training or releasing model artifacts.

#### Scenario: Execute train-split prediction-only rerun
- **WHEN** the rerun is launched on the A100 machine
- **THEN** it MUST use `prediction_split=train`, `overfit_diagnostic=true`, `generalization_claim=false`, `schema_retry_enabled=true`, greedy decoding, and the current public sample manifest
- **AND** it MUST use a repo-external private override with adapter/model/cache/output paths under the approved A100 project root
- **AND** it MUST inspect GPU occupancy, select a safe GPU, and set `CUDA_VISIBLE_DEVICES` explicitly
- **AND** it MUST NOT perform training, fine-tuning, DPO, GRPO, checkpoint release, adapter release, parser relaxation, evaluator metric change, slot normalization, semantic-equivalence scoring, prediction repair, prediction replacement, or re-score

#### Scenario: Preserve private runtime boundaries
- **WHEN** artifacts are copied back into the repository
- **THEN** only sanitized public sample evidence MAY be committed
- **AND** private overrides, raw logs, private paths, host details, SSH details, tokens, secrets, caches, checkpoints, adapters, and private corpus rows MUST remain outside git

### Requirement: Preserve wrapper-boundary diagnosis before behavior changes
The system SHALL preserve the A100 search-query slot wrapper-boundary diagnosis as a local evidence step before any future decoding, instrumentation, or output-postprocessing change.

#### Scenario: Diagnose before changing output behavior
- **WHEN** compact query content still appears inside Markdown-wrapped predictions
- **THEN** the system MUST first document the observed wrapper symptoms and evidence gaps before changing decoding parameters, output parsing, retry policy, or any postprocessing step

#### Scenario: Keep source evidence untouched
- **WHEN** local diagnosis evidence is generated
- **THEN** the system MUST preserve existing predictions, raw decoded summaries, generation traces, metrics, schema guard summaries, and manifests as source evidence without extracting, coercing, replacing, normalizing, repairing, or re-scoring outputs

### Requirement: Harden first-pass prediction output boundary
The system SHALL expose a machine-only first-pass prediction output boundary for trained-adapter prediction prompts without changing strict parser, evaluator, training, retry, or prediction repair behavior.

#### Scenario: Build machine-only first-pass prediction prompt
- **WHEN** the formatter builds a trained-adapter prediction prompt
- **THEN** the prompt MUST require exactly one root Browser Task Contract JSON object, require the first non-empty character to be `{`, require the last non-empty character to be `}`, prohibit Markdown/code fences/prose/prefix/suffix/trailing analysis, prohibit second JSON objects, and state that wrapped fragments remain invalid under the strict whole-object parser

#### Scenario: Report first-pass output-boundary visibility
- **WHEN** prediction metadata or prompt snapshots summarize first-pass prediction behavior
- **THEN** they MUST expose machine-readable booleans for exact JSON-only output, no Markdown/code-fence/prose wrapper, no preamble/suffix/trailing analysis, no second JSON object, first/last brace requirements, and strict whole-object parser rejection visibility

#### Scenario: Preserve strict first-pass parsing
- **WHEN** a first-pass prediction contains a valid Browser Task Contract embedded inside Markdown, prose, wrapper text, or explanatory text
- **THEN** the strict parser MUST continue to reject it as a non-whole JSON-object prediction rather than extracting, repairing, coercing, normalizing, re-scoring, or replacing the embedded fragment

#### Scenario: Keep behavior-change phase local
- **WHEN** first-pass output-boundary hardening is implemented
- **THEN** the phase MUST NOT run A100 prediction, train a model, release an adapter/checkpoint, change evaluator metrics, relax parsing, rewrite prior A100 artifacts, or claim model-quality improvement

### Requirement: Run first-pass output-boundary A100 prediction-only rerun
The system SHALL support a bounded A100 prediction-only train-split rerun that exercises the current first-pass output-boundary prompt/instrumentation against an existing private adapter without training or releasing model artifacts.

#### Scenario: Execute train-split prediction-only rerun
- **WHEN** the authorized A100 rerun is launched
- **THEN** it MUST use `prediction_split=train`, `overfit_diagnostic=true`, `generalization_claim=false`, `schema_retry_enabled=true`, greedy decoding, and the current public sample manifest
- **AND** it MUST use a repo-external private override with adapter/model/cache/output paths under the approved A100 project root
- **AND** it MUST inspect GPU occupancy, select a safe idle GPU, and set `CUDA_VISIBLE_DEVICES` explicitly
- **AND** it MUST NOT perform training, fine-tuning, DPO, GRPO, checkpoint release, adapter release, parser relaxation, evaluator metric change, slot normalization, semantic-equivalence scoring, prediction repair, prediction replacement, or re-score

#### Scenario: Preserve private runtime boundaries
- **WHEN** artifacts are copied back into the repository
- **THEN** only sanitized public sample evidence MAY be committed
- **AND** private overrides, raw logs, private paths, host details, SSH details, tokens, secrets, caches, checkpoints, adapters, and private corpus rows MUST remain outside git

#### Scenario: Record first-pass boundary metadata
- **WHEN** prediction metadata and prompt snapshots are produced
- **THEN** they MUST include `prediction_output_boundary` booleans proving whether the new first-pass boundary was visible in the A100 runtime prompt context

### Requirement: Suppress first-pass Markdown fence generation
The system SHALL configure trained-adapter prediction generation to suppress Markdown code-fence token sequences when the active tokenizer can provide non-empty token ids, while preserving strict parser and prediction provenance behavior.

#### Scenario: Build generation kwargs with fence suppression
- **WHEN** trained-adapter prediction calls model generation with a tokenizer that can encode Markdown fence strings
- **THEN** the generation kwargs MUST include `bad_words_ids` for non-empty tokenizer-derived Markdown fence token sequences
- **AND** the call MUST keep greedy decoding, configured `max_new_tokens`, and the existing pad token policy

#### Scenario: Preserve strict parser behavior for fenced output
- **WHEN** a model still emits a valid Browser Task Contract wrapped in Markdown fences
- **THEN** the strict parser MUST continue to reject it as a non-whole JSON-object prediction rather than extracting, repairing, coercing, normalizing, re-scoring, or replacing the embedded fragment

#### Scenario: Report suppression policy in prediction metadata
- **WHEN** prediction metadata or prompt snapshots summarize trained-adapter prediction behavior
- **THEN** they MUST expose machine-readable Markdown fence suppression policy fields separate from parser, retry, and output-boundary prompt metadata

#### Scenario: Keep local behavior phase bounded
- **WHEN** Markdown fence suppression is implemented locally
- **THEN** the phase MUST NOT run A100 prediction, train a model, release an adapter/checkpoint, rewrite prior A100 artifacts, change evaluator metrics, relax parsing, or claim model-quality improvement

### Requirement: Run A100 first-pass fence-suppression rerun
The system SHALL support a bounded, explicitly authorized A100 prediction-only train-split rerun after first-pass Markdown fence suppression while keeping all private runtime artifacts outside git.

#### Scenario: Launch prediction-only rerun with approved private runtime
- **WHEN** a developer launches the rerun with A100 authorization, a repo-external private override, an existing private adapter path, an approved private output root represented in public artifacts as `<a100_project_root>`, and a safe idle GPU selected without interrupting other users
- **THEN** the system MUST use `prediction_split=train`, `overfit_diagnostic=true`, `generalization_claim=false`, current first-pass Markdown fence suppression decoding policy, strict raw/retry parsing, and public-sample train rows
- **AND** it MUST write remote outputs only under the approved private project root

#### Scenario: Preserve strict prediction behavior
- **WHEN** model outputs contain Markdown fences, prose wrappers, malformed JSON, or contract-like fragments
- **THEN** the prediction artifact and sidecars MUST preserve sanitized failure evidence without stripping fences, extracting embedded JSON, replacing predictions with fixtures/gold/rule outputs, or changing schema guard semantics

#### Scenario: Keep private A100 artifacts private
- **WHEN** the rerun completes or fails
- **THEN** raw logs, checkpoints, adapters, caches, private overrides, host details, SSH details, private paths, tokens, and private corpus rows MUST remain outside committed artifacts

### Requirement: Reinforce compact query slot preservation in prompts
The shared SFT training and trained-adapter prediction prompt SHALL make the rejected decomposed search-slot shape visible without including row-specific gold target contracts in prediction prompts.

#### Scenario: Serialize prompt with decomposed slot rejection
- **WHEN** SFT training text or trained-adapter prediction prompt is rendered
- **THEN** the model-visible system prompt MUST state that public-readonly search/weather contracts preserve compact `slots.query`
- **AND** it MUST state that decomposed `city/date/topic` slot objects are rejected for the same search query
- **AND** it MUST state that this is target-formatting guidance, not evaluator normalization, semantic-equivalence scoring, prediction repair, or re-score

#### Scenario: Preserve prediction prompt gold exclusion
- **WHEN** a trained-adapter prediction prompt is rendered for a row with a target-only slot value
- **THEN** the prompt MUST include the generic compact-query/decomposed-slot policy
- **AND** it MUST NOT include the row-specific gold target contract or target-only slot value

### Requirement: Run A100 compact query slot preservation rerun
The system SHALL support a bounded A100 prediction-only train-split rerun after compact query slot preservation repair while keeping private runtime artifacts outside git.

#### Scenario: Launch compact query slot preservation rerun
- **WHEN** a developer launches the rerun with A100 authorization, a repo-external private override, an existing private adapter path, an idle A100 GPU, and an approved private output root represented in public artifacts as `<a100_project_root>`
- **THEN** the rerun MUST use `prediction_split=train`, `overfit_diagnostic=true`, `generalization_claim=false`, the current public-sample manifest, and the current trained-adapter prediction prompt policy
- **AND** it MUST write sanitized predictions plus prompt snapshot, raw decoded summary, generation trace, prediction metadata, schema guard summary, metrics, and diagnosis artifacts suitable for public evidence

#### Scenario: Keep private A100 artifacts private
- **WHEN** the compact query slot preservation rerun completes or fails
- **THEN** raw logs, checkpoints, adapters, caches, private overrides, host details, SSH details, private paths, tokens, and private corpus rows MUST remain outside committed artifacts

#### Scenario: Preserve rerun outputs honestly
- **WHEN** the private adapter emits decomposed slots, invalid JSON, wrapper text, non-contract JSON, or any strict mismatch
- **THEN** the prediction artifact and sidecars MUST preserve sanitized model output and strict failure status without replacing it with fixture-mode, rule-baseline, normalized, repaired, or gold contracts

### Requirement: Harden compact-query exact-match prompt policy
The system SHALL make the shared SFT training and trained-adapter prediction prompt explicitly align public-readonly search/weather `normalized_command` and `slots.query` target formatting without changing parser or evaluator semantics.

#### Scenario: Serialize compact-query exact-match policy
- **WHEN** SFT training text or a trained-adapter prediction prompt is rendered for a Browser Task Contract
- **THEN** the model-visible system prompt MUST state that public-readonly search/weather contracts use `normalized_command="搜索" + <compact query phrase>` and `slots.query=<same compact query phrase>`
- **AND** it MUST state that compact query phrases do not insert extra particles such as `的` when the canonical target phrase omits them
- **AND** it MUST state that the model MUST NOT split the same search query into ad hoc `city`, `date`, `topic`, or similar keys
- **AND** it MUST state that this is target-formatting guidance, not evaluator normalization, semantic-equivalence scoring, prediction repair, prediction replacement, or re-score

#### Scenario: Show non-row-specific accepted and rejected examples
- **WHEN** the prompt demonstrates compact-query exact-match formatting
- **THEN** it MUST include non-row-specific examples showing an accepted compact `slots.query` contract shape and a rejected decomposed `city/date/topic` shape
- **AND** the examples MUST NOT include row-specific gold target strings for the current prediction row unless those strings are already present in the user input

#### Scenario: Surface compact-query exact-match policy metadata
- **WHEN** prompt constraint metadata is recorded in prediction metadata, prompt snapshots, manifests, reports, or evidence packs
- **THEN** it MUST include booleans for compact-query exact-match policy visibility, same-query-phrase alignment visibility, extra-particle avoidance visibility, and decomposed-slot rejection visibility

#### Scenario: Bound local prompt-hardening interpretation
- **WHEN** public documentation, reports, Human Briefs, or OpenSpec artifacts describe this prompt hardening
- **THEN** they MUST state that the phase performs no A100 execution, training, prediction rerun, parser relaxation, strict evaluator metric replacement or relaxation, semantic-equivalence scoring, slot normalization, `normalized_command` normalization, prediction repair, prediction replacement, or prediction re-score
- **AND** they MUST NOT claim held-out generalization, production readiness, model-quality improvement, model recovery, checkpoint release, adapter release, public full-corpus release, or live-browser benchmark improvement

#### Scenario: Preserve SFT training sequence budget
- **WHEN** SFT training text is rendered for public sample rows
- **THEN** it MUST retain the compact-query exact-match target-formatting policy
- **AND** it MAY omit prediction-only one-shot examples when needed to keep training text within the configured local sequence budget
- **AND** trained-adapter prediction prompts MUST still retain prediction-only one-shot and output-boundary guidance

### Requirement: Expose public extract-price contract policy in SFT prompts
The system SHALL make SFT training and trained-adapter prediction prompts explicitly state the Browser Task Contract policy for current-page public price extraction while preserving gold-target boundaries.

#### Scenario: Serialize extract policy in training text
- **WHEN** the formatter converts an SFT dataset row into training text
- **THEN** the rendered system prompt MUST state that current-page price extraction uses `task_type="extract"`, `route="extract_page"`, `safety.allow=true`, `safety.reason="public_readonly"`, `confirmation_required=false`, object-shaped `slots.target`, and a concise extract normalized command
- **AND** it MUST state that the request MUST NOT be converted into public web search for price-like current-page extraction

#### Scenario: Serialize extract policy in prediction prompts without gold contract
- **WHEN** the formatter builds a trained-adapter prediction prompt
- **THEN** the prompt MUST include the same extract-price policy
- **AND** it MUST NOT include the full row-specific gold target contract or target-only slot values beyond policy text and strings already present in the user input

#### Scenario: Surface extract prompt constraint metadata
- **WHEN** prompt constraint metadata is recorded in prediction metadata, prompt snapshots, manifests, reports, or evidence packs
- **THEN** it MUST include explicit booleans for extract-page policy visibility, extract target-slot guidance visibility, extract search-fallback rejection visibility, and extract query/page-url slot rejection visibility

### Requirement: Run A100 extract-price contract residual train-split rerun
The system SHALL support a bounded, explicitly authorized 7B A100 public-sample train-split rerun after extract-price contract policy repair while keeping all private runtime artifacts outside git.

#### Scenario: Launch extract-price residual rerun
- **WHEN** a developer launches the rerun with explicit A100 approval, a repo-external private override, an idle A100 GPU, and an approved private output root represented in public artifacts as `<a100_project_root>`
- **THEN** the system MUST train on the current committed public-sample train rows with the extract-price prompt/data policy visible
- **AND** prediction MUST use `prediction_split=train`, `overfit_diagnostic=true`, `generalization_claim=false`, and sanitized sidecar exports

#### Scenario: Preserve compact-query behavior during extract repair
- **WHEN** train-split predictions are evaluated for the extract-price residual rerun
- **THEN** compact public-readonly search/weather train rows MUST be reported separately from extract-price train rows
- **AND** the report MUST state whether compact-query strict exact match was preserved, regressed, or could not be evaluated

#### Scenario: Keep private A100 artifacts private
- **WHEN** the rerun completes or fails
- **THEN** raw logs, checkpoints, adapters, model caches, private overrides, host details, SSH details, private paths, tokens, and private corpus rows MUST remain outside committed artifacts

### Requirement: Expose extract-price canonical wording policy in SFT prompts
The system SHALL make SFT training and trained-adapter prediction prompts explicitly state the canonical wording rule for current-page public price extraction while preserving prediction gold-target boundaries.

#### Scenario: Serialize canonical wording policy
- **WHEN** the formatter renders an SFT training text or prediction prompt for a public-safe extract-price row
- **THEN** the system prompt MUST state that user wording such as `多少钱`, `标价`, and `页面上的商品价格` maps to `slots.target="商品价格"` and `normalized_command="提取页面商品价格"`
- **AND** it MUST state that `价格`, `标价`, `页面价格`, and `提取页面上的商品价格` are strict-wrong target variants for this public contract

#### Scenario: Preserve prediction gold boundary
- **WHEN** the formatter builds a prediction prompt for an extract-price row
- **THEN** the prompt MUST NOT include the full row-specific gold contract
- **AND** it MUST NOT include row-specific target-only values except canonical policy text and strings already present in the user input

#### Scenario: Surface canonical wording prompt metadata
- **WHEN** prompt constraint metadata is recorded for prediction metadata, prompt snapshots, manifests, reports, or evidence packs
- **THEN** it MUST include booleans for extract canonical商品价格 target visibility, alias-to-canonical mapping visibility, strict-wrong synonym rejection visibility, and extra-particle rejection visibility

### Requirement: Run A100 extract-price canonical wording train-split rerun
The system SHALL support a bounded, explicitly authorized 7B A100 public-sample train-split rerun after extract-price canonical wording repair while keeping all private runtime artifacts outside git.

#### Scenario: Launch canonical wording rerun
- **WHEN** a developer launches the rerun with explicit A100 approval, a repo-external private override, an idle A100 GPU, and an approved private output root represented in public artifacts as `<a100_project_root>`
- **THEN** the system MUST train on the current public-sample train rows with the canonical extract-price wording policy and hard negatives available
- **AND** prediction MUST use `prediction_split=train`, `overfit_diagnostic=true`, `generalization_claim=false`, and sanitized sidecar exports

#### Scenario: Preserve prior fixed behavior during canonical wording repair
- **WHEN** train-split predictions are evaluated for the canonical wording rerun
- **THEN** compact public-readonly search/weather rows and extract-price task/route shape MUST be reported separately
- **AND** the report MUST state whether compact-query exact match, extract task/route correctness, extract target exact match, and extract normalized-command exact match were recovered, preserved, regressed, or could not be evaluated

#### Scenario: Keep private A100 artifacts private
- **WHEN** the canonical wording rerun completes or fails
- **THEN** raw logs, checkpoints, adapters, model caches, private overrides, host details, SSH details, private paths, tokens, and private corpus rows MUST remain outside committed artifacts

### Requirement: Run A100 public held-out prediction with existing adapter
The system SHALL support bounded A100 public held-out prediction jobs that reuse an existing private 7B SFT adapter without launching new training.

#### Scenario: Configure public dev/test prediction
- **WHEN** a developer prepares public held-out prediction templates
- **THEN** the templates MUST use the committed public-sample manifest, set `prediction_split` to `dev` or `test`, keep private paths as `<a100_project_root>` placeholders, require `allow_private_prediction=true`, and set `generalization_claim=false`

#### Scenario: Launch prediction-only held-out run
- **WHEN** the held-out prediction job runs on A100 with an explicit private override, an approved private project root, and an existing private adapter path
- **THEN** the system MUST generate sanitized public-sample predictions and sidecars for the configured split without training, copying adapters, copying checkpoints, copying raw logs, or writing private runtime paths into public artifacts

#### Scenario: Reject accidental training or unresolved execution
- **WHEN** held-out prediction is attempted with unresolved placeholders, without explicit prediction opt-in, without an adapter path, or as a training command
- **THEN** the system MUST NOT load private model artifacts for prediction and MUST NOT start training

### Requirement: Expose held-out residual repair policy in SFT prompts
The system SHALL make SFT training and trained-adapter prediction prompts explicitly state the public held-out residual repair contract policies without including row-specific gold target contracts in prediction prompts.

#### Scenario: Serialize repair policy
- **WHEN** the formatter renders SFT training text or prediction prompts
- **THEN** the system prompt MUST include policy text for public navigation URL canonicalization, ambiguous clarify routing, confirmation-required form-fill safety, and unsafe payment blocking
- **AND** the policy text MUST state that these rules do not relax evaluator exact-match behavior and are not prediction repair or re-scoring

#### Scenario: Preserve prediction gold boundary
- **WHEN** the formatter builds a prediction prompt for public held-out rows
- **THEN** it MUST NOT include the full row-specific gold target contract
- **AND** it MUST NOT include held-out target-only slot values except generic policy examples and strings already present in the user input

### Requirement: Run A100 public held-out residual repair rerun
The system SHALL support a bounded A100 SFT rerun that trains on the expanded public train split and evaluates public `dev` and `test` splits separately.

#### Scenario: Configure repair SFT rerun
- **WHEN** a developer prepares the repair rerun config
- **THEN** the config MUST use the regenerated public-sample manifest, train on `dataset_split="train"`, keep private output paths as `<a100_project_root>` placeholders, require explicit heavy-training opt-in, and keep `generalization_claim=false`

#### Scenario: Configure split-specific repair predictions
- **WHEN** a developer prepares repair prediction templates
- **THEN** the templates MUST point to the repair rerun adapter placeholder and set `prediction_split` separately for `train`, `dev`, and `test`
- **AND** the templates MUST require explicit private prediction opt-in and keep `generalization_claim=false`

#### Scenario: Keep private A100 artifacts private
- **WHEN** the repair rerun and split-specific predictions complete or fail
- **THEN** raw logs, checkpoints, adapters, model caches, private overrides, host details, SSH details, private paths, tokens, and private corpus rows MUST remain outside committed artifacts

### Requirement: Diagnose public SFT contract learning signal
The system SHALL provide a local, public-safe diagnostic that inspects whether public SFT rows expose assistant contract targets with enough structural learning signal before additional heavy SFT reruns are interpreted.

#### Scenario: Inspect rendered SFT targets
- **WHEN** the learning-signal diagnostic runs against the public sample manifest and SFT JSONL
- **THEN** it MUST report row count, split counts, task-family counts, rendered prompt character counts, assistant target character counts, assistant-target ratio, target field/key counts, and max-sequence risk summaries
- **AND** it MUST identify whether each inspected row has a detectable assistant contract target span

#### Scenario: Separate structural target evidence from runtime label evidence
- **WHEN** the diagnostic has not inspected real tokenizer/collator labels from the runtime training path
- **THEN** it MUST mark true runtime label-mask evidence as unavailable
- **AND** it MUST state that structural target-span evidence does not prove that real training labels were applied to those target tokens

#### Scenario: Link prior negative repair evidence
- **WHEN** prior public held-out residual repair evidence exists
- **THEN** the diagnostic MUST read the public-safe manifest or diagnosis summary and include the observed train/dev/test strict metrics as prior context without changing those artifacts

#### Scenario: Bound execution scope
- **WHEN** the diagnostic is run in its default local mode
- **THEN** it MUST NOT download models, load private adapters, start A100 execution, run training, or run prediction

### Requirement: Recommend the next SFT debugging phase from evidence
The system SHALL convert learning-signal findings into a bounded next-step recommendation without widening scope automatically.

#### Scenario: Recommend runtime label inspection
- **WHEN** assistant target spans are structurally present but true runtime label-mask evidence is unavailable
- **THEN** the diagnostic MUST recommend a bounded runtime label inspection or tiny overfit phase before additional full SFT reruns

#### Scenario: Recommend prompt or data repair
- **WHEN** assistant target spans are missing, target pressure is extreme, or prompt budget risk is high
- **THEN** the diagnostic MUST identify the affected rows or task families and recommend a local prompt/data repair phase before heavy training

### Requirement: Diagnose current-manifest runtime label and tiny-overfit readiness
The system SHALL provide a bounded SFT debugging diagnostic that compares the current public manifest with available runtime-label and tiny-overfit artifacts before recommending any additional full SFT rerun.

#### Scenario: Treat stale runtime label evidence as prior context only
- **WHEN** a runtime-label artifact was generated for a dataset manifest ID that differs from the current public manifest ID
- **THEN** the diagnostic MUST mark the runtime evidence as stale for the current phase
- **AND** it MUST preserve the stale artifact's label-mask fields only as prior context
- **AND** it MUST NOT claim that current public rows have inspected runtime labels

#### Scenario: Preserve fresh runtime label mask fields
- **WHEN** a runtime-label artifact matches the current public manifest ID and reports real training labels
- **THEN** the diagnostic MUST record `true_label_mask_status`, `prompt_tokens_masked`, `assistant_tokens_carry_loss`, prompt token count, assistant token count, label source kind, and evidence gaps
- **AND** it MUST distinguish assistant-token loss participation from an assistant-only loss-mask claim

#### Scenario: Bound tiny-overfit recommendation
- **WHEN** current runtime labels are unavailable or stale after local public-safe inspection
- **THEN** the diagnostic MUST recommend a fresh current-manifest runtime label check before a full SFT rerun
- **AND** it MAY recommend a 1-3 row tiny-overfit probe only as train-internal objective debugging
- **AND** it MUST NOT present tiny-overfit as held-out generalization, model recovery, checkpoint release, adapter release, production readiness, or live-browser benchmark evidence

#### Scenario: Avoid widening into full training
- **WHEN** the bounded diagnostic is run locally
- **THEN** it MUST NOT run full SFT, DPO, GRPO, private adapter prediction, or model release steps
- **AND** it MUST NOT copy checkpoints, adapters, caches, raw logs, private paths, host details, SSH details, or private corpus rows into committed artifacts

### Requirement: Run bounded current-manifest runtime label check
The system SHALL support a bounded runtime label provenance check for the current public SFT manifest without starting training, prediction, adapter loading, or broad model experimentation.

#### Scenario: Execute current-manifest runtime label check
- **WHEN** the current public manifest is selected for runtime label provenance inspection
- **THEN** the runtime check MUST inspect only public train-split SFT rows, use explicit runtime opt-in, require private override resolution under the approved private project root when remote execution is needed, and write only sanitized metadata intended for public evidence

#### Scenario: Avoid training and prediction side effects
- **WHEN** the current-manifest runtime label check runs
- **THEN** it MUST NOT train SFT, run DPO, run GRPO, export predictions, load a private adapter, copy checkpoints or adapters into git, or download public model snapshots into the repository

#### Scenario: Preserve next-step boundary
- **WHEN** the current-manifest runtime label check finishes
- **THEN** the result MUST recommend tiny-overfit only as a separate later phase when labels are fresh, inspectable, and assistant-only; otherwise it MUST recommend fixing the concrete label-path gap first

### Requirement: Run 7B current-manifest tiny-overfit probe
The system SHALL provide a bounded A100 SFT probe that trains the 7B Qwen-family model on a tiny train-only slice from the current public sample manifest and records the run as train-internal evidence only.

#### Scenario: Configure current-manifest tiny-overfit training
- **WHEN** a developer prepares the current-manifest tiny-overfit training config
- **THEN** the committed template MUST use `Qwen/Qwen2.5-7B-Instruct`, `dataset_manifest_id=public-sample-20260613T072200Z`, `dataset_split=train`, `overfit_diagnostic=true`, `generalization_claim=false`, and unresolved `<a100_project_root>` placeholders that require a private override before remote execution

#### Scenario: Bound tiny training rows
- **WHEN** the A100 probe is launched from a private override
- **THEN** the training command MUST use only 1 to 3 train rows from the current public sample manifest and MUST record the selected row IDs in private metadata before any public evidence is prepared

#### Scenario: Keep heavy artifacts private
- **WHEN** the tiny-overfit training run completes or fails
- **THEN** raw logs, checkpoints, adapters, caches, private overrides, host details, SSH details, private paths, tokens, and private corpus rows MUST remain outside committed artifacts

#### Scenario: Preserve blocked execution honestly
- **WHEN** training dependencies, GPU placement, model files, or SSH access are unavailable
- **THEN** the phase MUST record a bounded public-safe blocked status and MUST NOT claim that tiny-overfit training occurred

### Requirement: Run current-manifest tiny adapter held-out prediction
The system SHALL support bounded A100 prediction-only jobs that reuse the
existing private current-manifest tiny-overfit 7B adapter on the current public
manifest's `dev` and `test` splits without launching new training.

#### Scenario: Configure current tiny adapter dev/test prediction
- **WHEN** a developer prepares current tiny-adapter held-out prediction templates
- **THEN** the templates MUST use `dataset_manifest_id=public-sample-20260613T072200Z`
- **AND** they MUST use `prediction_split` values `dev` and `test`
- **AND** they MUST set `allow_private_prediction=true`, `overfit_diagnostic=false`, and `generalization_claim=false`
- **AND** they MUST keep private paths as `<a100_project_root>` placeholders and require a private override before remote execution
- **AND** they MUST NOT include `allow_heavy_training`, `adapter_output_dir`, or `max_prediction_rows`

#### Scenario: Launch prediction-only run with existing tiny adapter
- **WHEN** the current tiny-adapter held-out prediction job runs on A100 with an explicit private override, an approved private project root, and the existing private adapter path
- **THEN** the system MUST generate sanitized public-sample predictions and sidecars for the configured split without training, copying adapters, copying checkpoints, copying raw logs, or writing private runtime paths into public artifacts

#### Scenario: Reject accidental training or unresolved execution
- **WHEN** current tiny-adapter held-out prediction is attempted with unresolved placeholders, without explicit prediction opt-in, without an adapter path, with row-limited train-only config, or as a training command
- **THEN** the system MUST NOT load private model artifacts for prediction and MUST NOT start training

### Requirement: Run targeted family coverage SFT probe
The system SHALL support a bounded A100 SFT probe that trains on explicit public-safe source families matching the current held-out residual train analogs.

#### Scenario: Select train rows by source family
- **WHEN** SFT training is launched with `train_source_ids`
- **THEN** the training path MUST filter the configured training split to rows whose provenance `source_id` is in that list
- **AND** training metadata MUST record selected source IDs, selected row IDs, rows before filtering, and rows after filtering

#### Scenario: Configure targeted family coverage training
- **WHEN** the targeted family coverage probe config is prepared
- **THEN** it MUST use base model `Qwen/Qwen2.5-7B-Instruct`, dataset manifest `public-sample-20260613T072200Z`, `dataset_split=train`, `allow_heavy_training=true`, and explicit train source IDs for `seed-open-help`, `seed-clarify-target`, `seed-form-nickname`, and `seed-block-transfer`
- **AND** it MUST keep `<a100_project_root>` placeholders and require a private override before remote execution

#### Scenario: Predict targeted family coverage splits
- **WHEN** targeted family coverage prediction configs are prepared
- **THEN** the system MUST provide split-specific train, dev, and test templates that point to the targeted probe adapter placeholder and require explicit prediction opt-in
- **AND** train prediction MUST be interpreted as learnability evidence while dev/test remain the primary held-out evidence

#### Scenario: Keep targeted probe private by default
- **WHEN** the targeted family coverage training or prediction run completes
- **THEN** raw logs, checkpoints, adapters, caches, private overrides, host details, SSH details, tokens, private paths, and private corpus rows MUST remain outside committed artifacts

### Requirement: Run slot value candidate SFT probe separately
The system SHALL support a bounded SFT probe over reviewed slot value generalization candidates without merging those candidates into the formal public sample.

#### Scenario: Select only candidate rows for SFT
- **WHEN** a developer runs the candidate SFT probe dry-run or training command
- **THEN** the run metadata MUST load the candidate-only manifest
- **AND** it MUST select exactly the materialized slot value candidate SFT rows
- **AND** it MUST NOT select formal public sample `dev` or `test` rows

#### Scenario: Keep candidate probe non-generalization
- **WHEN** candidate SFT probe metadata, reports, or Human Briefs are generated
- **THEN** they MUST label the run as candidate-only learning-signal or overfit-probe evidence
- **AND** they MUST set `generalization_claim=false`
- **AND** they MUST NOT claim held-out dev/test recovery, model recovery, adapter release, checkpoint release, production readiness, private-corpus generalization, or live-browser benchmark improvement

#### Scenario: Gate real A100 execution
- **WHEN** the candidate probe is prepared for A100 execution
- **THEN** committed configs MUST keep private paths unresolved with `<a100_project_root>` placeholders
- **AND** any real execution evidence MUST record whether train dependencies, private overrides, output-root policy, and idle GPU checks passed
- **AND** if dependencies or safe output placement are unavailable, the evidence MUST record a blocked status instead of implying training ran

### Requirement: Execute slot value candidate SFT probe on A100 safely
The system SHALL support an explicitly bounded A100 execution path for the slot value candidate SFT probe while keeping private runtime artifacts outside git.

#### Scenario: Prepare isolated A100 execution workspace
- **WHEN** the A100 candidate probe phase prepares remote execution
- **THEN** all project snapshots, dependency environments, caches, temporary files, outputs, and evidence staging directories MUST be under the approved private A100 root
- **AND** the phase MUST stop before training if this placement cannot be enforced

#### Scenario: Launch candidate-only SFT when safe
- **WHEN** train dependencies are available, a private override resolves `<a100_project_root>`, and an idle GPU is selected
- **THEN** the SFT command MUST use the candidate-only manifest, `dataset_split=train`, the 7B base model, and explicit `CUDA_VISIBLE_DEVICES`
- **AND** it MUST write adapters, checkpoints, caches, logs, and raw runtime outputs only under the approved private remote workspace

#### Scenario: Preserve training failure or blocked status
- **WHEN** dependency setup, model loading, GPU placement, output-root policy, or training fails
- **THEN** the phase MUST write only sanitized status metadata to git
- **AND** it MUST NOT imply that candidate SFT training completed

#### Scenario: Bound candidate training interpretation
- **WHEN** real candidate training metadata is imported into public evidence
- **THEN** the evidence MUST label it as candidate train-split learnability evidence
- **AND** it MUST NOT claim held-out dev/test generalization, checkpoint release, adapter release, production readiness, private-corpus generalization, or live-browser improvement

### Requirement: Run A100 merged slot value public-sample SFT rerun
The system SHALL support a bounded 7B A100 SFT rerun after the reviewed slot
value candidates are merged into the formal public sample.

#### Scenario: Configure merged-candidate SFT rerun
- **WHEN** the merged-candidate SFT config is prepared
- **THEN** it MUST use `Qwen/Qwen2.5-7B-Instruct`, the regenerated
  `manifest_public_sample.json`, `dataset_split="train"`,
  `allow_heavy_training=true`, and `generalization_claim=false`
- **AND** it MUST keep private output paths as `<a100_project_root>`
  placeholders requiring a private override before remote execution
- **AND** it MUST train on the formal public train split rather than the
  standalone candidate manifest

#### Scenario: Configure split-specific merged-candidate predictions
- **WHEN** prediction configs are prepared for the merged-candidate adapter
- **THEN** the system MUST provide train, dev, and test templates that point to
  the merged-candidate adapter placeholder
- **AND** each prediction template MUST set its own `prediction_split`, require
  `allow_private_prediction=true`, and set `generalization_claim=false`

#### Scenario: Keep A100 runtime artifacts private
- **WHEN** merged-candidate training or prediction completes, fails, or is
  blocked
- **THEN** raw logs, adapters, checkpoints, caches, private overrides, host
  details, SSH details, private paths, tokens, model snapshots, and private
  corpus rows MUST remain outside committed artifacts

#### Scenario: Bound merged-candidate training interpretation
- **WHEN** public reports or Human Briefs describe the merged-candidate SFT run
- **THEN** train-split exact match MUST be described as learnability evidence
- **AND** held-out `dev`/`test` strict exact MUST be described as the primary
  generalization evidence
- **AND** the phase MUST NOT claim checkpoint release, adapter release,
  production readiness, private-corpus generalization, or live-browser
  benchmark improvement

### Requirement: Expose merged residual canonical policy in SFT prompts
The system SHALL make SFT training and trained-adapter prediction prompts expose
the post-merge canonical policy for the remaining ambiguous-clarify and unsafe
payment residual families without inserting row-specific gold target contracts
into prediction prompts.

#### Scenario: Serialize ambiguous clarify canonical phrase policy
- **WHEN** SFT training text or a trained-adapter prediction prompt is rendered
  with the residual repair prompt policy
- **THEN** the prompt MUST state that ambiguous clarify contracts use
  `task_type="clarify"`, `route="clarify"`,
  `safety.reason="ambiguous_request"`, `confirmation_required=true`, and
  `slots.ambiguity="目标不明确，未指定具体网站或页面"`
- **AND** it MUST state that shorter values such as `未指定具体页面` or
  `未指定具体操作` are strict-wrong for this canonical family

#### Scenario: Serialize unsafe payment canonical command policy
- **WHEN** SFT training text or a trained-adapter prediction prompt is rendered
  with the residual repair prompt policy
- **THEN** the prompt MUST state that unsafe payment/account-backed purchase
  requests use `task_type="blocked"`, `route="deny"`,
  `safety.allow=false`, `safety.reason="unsafe_payment"`,
  `confirmation_required=true`, `slots.reason=payment_requires_user_control`,
  and `normalized_command="拒绝代替用户付款"`
- **AND** it MUST state that `normalized_command="拒绝代替用户下单"` is
  strict-wrong for this canonical payment family

#### Scenario: Preserve prediction gold boundary for canonical policy
- **WHEN** the formatter builds a prediction prompt for a row whose gold target
  contains target-only slot values or normalized command text
- **THEN** it MUST NOT include the full row-specific gold target contract
- **AND** it MUST NOT include target-only values beyond shared policy text and
  strings already present in the user input

#### Scenario: Surface canonical policy metadata
- **WHEN** prompt constraint metadata is recorded in prediction metadata,
  prompt snapshots, manifests, reports, or evidence packs
- **THEN** it MUST include explicit booleans for ambiguous-clarify canonical
  phrase visibility and unsafe-payment canonical command visibility

### Requirement: Run prediction-only hardened canonical policy rerun
The system SHALL support a bounded A100 prediction-only rerun that uses the
existing merged slot-value 7B adapter with the current hardened canonical prompt
policy.

#### Scenario: Configure split-specific prediction rerun
- **WHEN** hardened canonical policy rerun configs are committed
- **THEN** each config MUST target one of `train`, `dev`, or `test`
- **AND** each config MUST use the current public-sample manifest ID
- **AND** each config MUST point to the existing merged slot-value adapter via
  a private placeholder
- **AND** each config MUST NOT include training opt-ins such as
  `allow_heavy_training` or `adapter_output_dir`

#### Scenario: Preserve prediction-only boundary
- **WHEN** the rerun is launched on A100
- **THEN** it MUST run `sft-predict` and strict evaluation only
- **AND** it MUST NOT start SFT, DPO, GRPO, adapter continuation training, data
  regeneration, evaluator relaxation, prediction repair, or prediction
  replacement

#### Scenario: Prove hardened prompt policy visibility
- **WHEN** prediction metadata is imported for the rerun
- **THEN** it MUST record `clarify_ambiguity_canonical_phrase_visible=true`
  and `unsafe_payment_canonical_command_visible=true` for each split before
  the run is interpreted as hardened-policy evidence

### Requirement: Restore or regenerate the merged slot-value A100 adapter
The system SHALL support a bounded prerequisite phase that restores or
regenerates the private `a100-merged-slot-value-heldout-eval` adapter needed by
later prediction-only reruns.

#### Scenario: Prefer exact adapter restoration
- **WHEN** an existing adapter is found under the approved A100 project root
- **THEN** the system MAY restore or relink it only if it corresponds to the
  merged slot-value held-out evaluation runtime
- **AND** it MUST verify required LoRA files before treating the adapter as
  available

#### Scenario: Regenerate adapter from approved config
- **WHEN** no reusable adapter exists
- **THEN** the system MAY run the existing merged slot-value SFT config with
  `allow_heavy_training=true`, dataset manifest
  `public-sample-20260615T040231Z`, and train split only
- **AND** it MUST keep all generated adapter, cache, log, and temporary outputs
  under `<approved_remote_root>`

#### Scenario: Preserve prerequisite boundary
- **WHEN** the adapter restore/regeneration phase completes
- **THEN** it MUST NOT claim new prediction metrics, model recovery, release
  readiness, private-corpus generalization, or live-browser benchmark
  improvement

### Requirement: Observe restored-adapter hardened canonical policy rerun
The system SHALL run the hardened canonical policy rerun as prediction-only
after the required merged slot-value adapter is restored.

#### Scenario: Use restored adapter without training
- **WHEN** the observed hardened canonical policy rerun is executed
- **THEN** it MUST reuse the `a100-merged-slot-value-heldout-eval` adapter
- **AND** it MUST NOT run SFT, DPO, GRPO, adapter continuation training, or model
  merge
- **AND** it MUST run train/dev/test prediction-only configs.

#### Scenario: Require hardened prompt metadata
- **WHEN** observed rerun metrics are interpreted
- **THEN** prediction metadata for train/dev/test MUST show hardened canonical
  prompt-policy flags
- **AND** missing flags MUST prevent recovery claims even if exact-match metrics
  improve.

### Requirement: Assess form-fill remediation SFT v3 readiness safely
The system SHALL publish public-safe readiness evidence before a later
`form_fill` remediation SFT v3 run.

#### Scenario: Prepare public-safe SFT v3 templates
- **WHEN** readiness config templates are committed
- **THEN** they MUST target manifest `public-sample-20260616T074315Z`
- **AND** they MUST keep private A100 paths unresolved with
  `<a100_project_root>` placeholders
- **AND** they MUST NOT include private paths, host details, SSH details,
  tokens, raw logs, checkpoints, adapters, or model caches

#### Scenario: Record dry-run row selection
- **WHEN** readiness evidence is generated
- **THEN** it MUST include local SFT dry-run row-selection metadata for the
  current public train split
- **AND** it MUST state that no SFT/DPO/GRPO training was launched

#### Scenario: Bound readiness interpretation
- **WHEN** reports or Human Briefs describe SFT v3 readiness
- **THEN** they MUST state that readiness does not prove model recovery,
  held-out generalization, private-corpus generalization, checkpoint release,
  adapter release, production readiness, public full-corpus release, or
  live-browser benchmark improvement

### Requirement: Run bounded A100 form-fill remediation SFT v3
The system SHALL run the `form_fill` remediation SFT v3 phase only after
readiness evidence exists and only within the approved private A100 project
root.

#### Scenario: Launch SFT v3 with private override
- **WHEN** the SFT v3 training job is launched
- **THEN** it MUST use manifest `public-sample-20260616T074315Z`
- **AND** it MUST use the train split selected by the committed readiness
  dry-run
- **AND** it MUST resolve private paths only through a repo-external private
  override under the approved A100 project root
- **AND** it MUST set an explicit `CUDA_VISIBLE_DEVICES` value selected after
  GPU occupancy preflight

#### Scenario: Keep SFT v3 artifacts private
- **WHEN** the SFT v3 training job completes or fails
- **THEN** raw checkpoints, LoRA adapters, model caches, raw logs, private
  overrides, host details, SSH details, tokens, and private paths MUST remain
  outside committed artifacts
- **AND** committed metadata MUST use public-safe placeholders or sanitized
  summaries

#### Scenario: Preserve SFT v3 scope
- **WHEN** SFT v3 training is launched
- **THEN** the phase MUST NOT start DPO, GRPO, generic chat fine-tuning, skill
  routing, GUI action policy learning, full private corpus training, prompt
  policy changes, evaluator relaxation, or prediction repair

### Requirement: Retry form-fill remediation SFT v3 after SSH recovery
The system SHALL retry the blocked `form_fill` remediation SFT v3 run only
after fresh A100 connectivity and GPU preflight succeed.

#### Scenario: Repeat preflight before retry training
- **WHEN** the retry phase starts after an SSH timeout blocker
- **THEN** it MUST run fresh A100 connectivity and GPU occupancy checks
- **AND** it MUST select a safe GPU explicitly with `CUDA_VISIBLE_DEVICES`
  before training
- **AND** it MUST NOT reuse the previous blocked status as evidence that GPU
  placement is safe

#### Scenario: Keep retry training private
- **WHEN** retry training starts
- **THEN** private overrides, checkpoints, adapters, raw logs, model caches,
  host details, SSH details, tokens, and private paths MUST remain outside git
- **AND** committed evidence MUST use sanitized summaries and public-safe
  placeholders

#### Scenario: Stop safely on retry blockers
- **WHEN** SSH, GPU placement, dependency setup, training, or output-root policy
  cannot be verified safely
- **THEN** the retry phase MUST record blocked or failed evidence without
  launching unsafe work or fabricating adapter metadata

### Requirement: Publish current-train-split SFT retry readiness evidence
The system SHALL publish public-safe readiness-only evidence before launching a new bounded A100 SFT retry after train-only repair rows have been materialized into the current formal public sample.

#### Scenario: Verify current train split retry inputs
- **WHEN** a current-train-split SFT retry readiness report is generated
- **THEN** it MUST record manifest id `public-sample-20260616T165835Z`, 100 seed rows, 256 SFT rows, 864 DPO pairs, split counts of train 118 / dev 69 / test 69, and local dry-run selection of all 118 train rows
- **AND** it MUST record train-split coverage for the merged form-fill remediation / confirmation-marker rows and blocked-payment repair rows

#### Scenario: Preserve readiness-only boundary
- **WHEN** current-train-split SFT retry readiness evidence is prepared for commit
- **THEN** committed artifacts MUST state that no A100 SFT training, DPO training, GRPO training, prediction generation, dataset mutation, prompt change, evaluator relaxation, semantic-equivalence scoring, slot normalization, prediction repair, or prediction replacement was performed
- **AND** committed artifacts MUST NOT claim held-out recovery, model recovery, checkpoint release, adapter release, production readiness, public full-corpus release, private-corpus generalization, safety improvement, or live-browser benchmark improvement

#### Scenario: Require distinct future retry runtime
- **WHEN** public-safe configs are prepared for a future current-train-split SFT retry
- **THEN** they MUST use placeholder private roots, require private overrides, keep outputs private by default, and use a source/runtime label distinct from the previous `a100-form-fill-remediation-sft-v3` adapter
- **AND** they MUST NOT contain raw private paths, host details, SSH details, tokens, checkpoints, adapters, caches, or private corpus rows

#### Scenario: Bind readiness recommendation to current strict metrics
- **WHEN** the readiness report recommends a later bounded A100 SFT retry
- **THEN** it MUST cite the latest current-manifest prediction-only strict metrics as input evidence
- **AND** it MUST keep `contract_exact_match` and strict `slot_f1` as headline metrics while treating `slot_f1_soft` as diagnostic-only
