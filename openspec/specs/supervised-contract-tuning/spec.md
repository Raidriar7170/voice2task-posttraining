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
