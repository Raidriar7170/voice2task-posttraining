# contract-evaluation Specification

## Purpose
Define the contract-level evaluation ladder, failure slices, controlled execution smoke, and public-safe reporting boundaries for Voice2Task outputs.
## Requirements
### Requirement: Compute contract evaluation ladder metrics
The system SHALL evaluate generated browser task contracts using schema validity, task type accuracy, route accuracy, safety precision/recall, confirmation accuracy, slot F1, and exact-match style contract checks where applicable.

#### Scenario: Evaluate model predictions
- **WHEN** the evaluator receives predictions and gold contracts for a split
- **THEN** it writes machine-readable metrics and a human-readable summary covering every metric in the contract evaluation ladder

### Requirement: Record failure slices
The system SHALL produce failure slices that identify common contract errors.

#### Scenario: Summarize failures
- **WHEN** predictions fail one or more metric checks
- **THEN** the evaluator groups failures by schema, task type, route, safety, confirmation, slot, and unknown categories with example identifiers

### Requirement: Diagnose contract-like schema mismatches
The system SHALL provide public-safe diagnostics for generated predictions that are JSON or JSON-like but fail the Browser Task Contract schema.

#### Scenario: Contract-like prediction fails required fields and field constraints
- **WHEN** a prediction artifact contains objects with Browser Task Contract-like fields that fail required fields, enum values, field types, or non-empty string constraints
- **THEN** the diagnostic output MUST report the affected row id, field path, issue category, observed value summary, and expected contract constraint without converting the prediction into a valid contract

#### Scenario: Diagnostics preserve bounded evidence claims
- **WHEN** diagnostics are generated for private-adapter public-sample predictions
- **THEN** the report MUST state that invalid predictions remain invalid and MUST NOT claim checkpoint release, adapter release, production readiness, full-private-corpus release, or live-browser benchmark improvement

### Requirement: Diagnose target-prediction alignment mismatches
The system SHALL provide public-safe diagnostics that compare generated prediction fields with their gold Browser Task Contract targets, including when predictions are schema-invalid but contract-like.

#### Scenario: Compare raw prediction fields with gold targets
- **WHEN** the evaluator receives gold public-sample rows and prediction artifacts with matching row ids
- **THEN** the alignment diagnostic output MUST report aggregate mismatch counts by contract field path and row-level mismatches with row id, field path, gold value summary, prediction value summary, and mismatch category without converting invalid predictions into valid contracts

#### Scenario: Preserve invalid prediction status
- **WHEN** a prediction fails Browser Task Contract schema validation but contains comparable contract-like fields
- **THEN** alignment diagnostics MUST NOT repair, normalize, coerce, or count the prediction as schema-valid

#### Scenario: Bound alignment evidence claims
- **WHEN** alignment diagnostics are generated for private-adapter public-sample predictions
- **THEN** the report MUST state that the evidence is field-level public-sample analysis only and MUST NOT claim checkpoint release, adapter release, production readiness, full-private-corpus release, or live-browser benchmark improvement

### Requirement: Run controlled execution smoke
The system SHALL support an optional execution smoke check that verifies generated contracts can be consumed by controlled Voice-to-Browser Agent validation paths.

#### Scenario: Run execution smoke
- **WHEN** execution smoke is enabled and a Voice-to-Browser Agent validation target is configured
- **THEN** the evaluator sends eligible contracts to the controlled validation path and reports smoke pass/fail separately from pure contract metrics

### Requirement: Keep reports public-safe
The system SHALL prevent public reports, committed Human Brief HTML, and loop reports from leaking raw private rows, absolute local paths, private remote paths, secrets, tokens, or unreleased private details.

#### Scenario: Generate public report
- **WHEN** a report or committed Human Brief is written for public or reviewer-facing documentation
- **THEN** it contains aggregate metrics, sanitized examples, manifest references, and explicit claim boundaries without raw local/private corpus rows, local absolute paths, private remote paths, host details, or path-like private infrastructure examples

### Requirement: Publish formal public sample held-out prediction evidence
The system SHALL publish public-safe prediction-only evidence for formal public sample dev/test rows after the formal sample manifest changes.

#### Scenario: Evaluate current formal public sample predictions
- **WHEN** sanitized private-adapter predictions are available for the current formal public sample dev and test splits
- **THEN** the system MUST evaluate them with the existing strict contract ladder, including `json_valid_rate`, `task_type_accuracy`, `route_accuracy`, `safety_precision`, `safety_recall`, `confirmation_accuracy`, `slot_f1`, `slot_f1_soft`, and `contract_exact_match`
- **AND** the evidence MUST record the current manifest id and split row counts used for evaluation

#### Scenario: Preserve prediction-only boundary
- **WHEN** formal public sample held-out prediction evidence is generated
- **THEN** the evidence MUST state that no SFT training, DPO training, dataset mutation, evaluator relaxation, semantic-equivalence scoring, slot normalization, prediction repair, prediction replacement, or prediction re-score was performed
- **AND** it MUST NOT claim held-out recovery, model recovery, checkpoint release, adapter release, production readiness, public full-corpus release, private-corpus generalization, or live-browser benchmark improvement

#### Scenario: Record blocked prediction execution safely
- **WHEN** the current formal public sample prediction run cannot safely execute because the private adapter, remote dependency, or idle GPU state is unavailable
- **THEN** the evidence MUST record a blocked status without writing fabricated predictions or model-quality metrics
- **AND** committed artifacts MUST omit raw logs, host details, SSH details, private paths, checkpoints, adapters, caches, tokens, and private corpus rows
#### Scenario: Validate public evidence boundaries
- **WHEN** formal public sample held-out prediction artifacts are prepared for commit
- **THEN** leak-scan validation MUST reject raw private rows, absolute local paths, private remote paths, host details, SSH details, secrets, tokens, raw logs, checkpoints, adapters, caches, and oversized generated corpora

### Requirement: Retry scaled-manifest A100 prediction baseline after recovery
The system SHALL produce public-safe observed-or-blocked evidence when retrying
the scaled public-sample prediction-only baseline after an A100 connectivity
recovery.

#### Scenario: Observed retry writes strict prediction evidence
- **WHEN** the A100 development machine is reachable, an approved GPU is safe to
  use, the existing private `a100-current-train-split-sft-retry` adapter is
  available, and dev/test predictions are generated for
  `public-sample-20260617T152259Z`
- **THEN** the committed evidence MUST record `run_status="observed"`, the
  target manifest id, dev/test prediction counts, strict contract ladder
  metrics, prediction metadata, and a comparison boundary marking direct
  improvement/regression comparison invalid
- **AND** the evidence MUST state that this was prediction-only and that no
  training, data mutation, evaluator relaxation, slot normalization, prediction
  repair, adapter release, checkpoint release, production-readiness claim, or
  live-browser benchmark claim was performed

#### Scenario: Unsafe retry fails closed
- **WHEN** the A100 development machine, approved GPU placement, remote
  environment, source adapter, or prediction command cannot be verified safely
- **THEN** the committed evidence MUST record a blocked status and blocked
  reason without writing fabricated predictions, fabricated metrics, or a model
  recovery claim
- **AND** the evidence MUST preserve the previous blocked baseline as historical
  evidence rather than overwriting it

#### Scenario: Public artifacts remain sanitized
- **WHEN** retry evidence, status docs, Human Brief HTML, or OpenSpec archive
  artifacts are prepared for commit
- **THEN** validation MUST reject raw logs, host details, SSH details, tokens,
  secrets, absolute local paths, private remote paths, private override configs,
  caches, checkpoints, adapters, and private corpus rows

### Requirement: Inspect scaled-manifest current-123 adapter residual clusters
The system SHALL publish public-safe cluster-inspection evidence for strict
residuals observed when the existing current-123 adapter is evaluated on the
scaled formal public sample manifest.

#### Scenario: Generate cluster inspection from scaled residual diagnosis
- **WHEN** the scaled residual-family diagnosis exists for
  `public-sample-20260617T152259Z`
- **THEN** the cluster inspection MUST group residual fields into actionable
  clusters by task family, source family, field path, residual category, and
  repeated mismatch pattern
- **AND** it MUST record top cluster rows, top cluster fields, source residual
  row/field count consistency, and source diagnosis artifact links

#### Scenario: Preserve strict metric and diagnosis-only boundaries
- **WHEN** scaled residual-cluster evidence is generated
- **THEN** it MUST state that no A100 job, training, prediction rerun, data
  mutation, prompt change, evaluator relaxation, semantic-equivalence scoring,
  slot normalization, prediction repair, DPO/GRPO run, adapter release,
  checkpoint release, production-readiness claim, or live-browser benchmark
  claim was performed
- **AND** `slot_f1_soft` MUST remain diagnostic only and not become the primary
  metric

#### Scenario: Recommend bounded next decision only
- **WHEN** the cluster inspection identifies dominant scaled-manifest residual
  clusters
- **THEN** it MAY recommend a later OpenSpec phase for data design,
  materialization, policy hardening, or training readiness
- **AND** it MUST NOT materialize data, launch training, or change evaluator
  behavior in this phase

#### Scenario: Validate public-safe cluster artifacts
- **WHEN** scaled residual-cluster artifacts, docs, Human Brief HTML, or archive
  files are prepared for commit
- **THEN** validation MUST reject raw private rows, absolute local paths,
  private remote paths, host details, SSH details, raw logs, tokens, secrets,
  private override configs, caches, checkpoints, adapters, and private corpus
  rows

### Requirement: Refresh current formal residual decision evidence
The system SHALL keep the committed formal held-out residual-family diagnosis,
residual-cluster inspection, and formal remediation target-selection artifacts
aligned with the latest formal public held-out prediction evidence boundary.

#### Scenario: Refresh residual-family diagnosis from current evidence
- **WHEN** a newer formal public held-out prediction evidence pack is selected
  as the current public-facing truth surface
- **THEN** the formal residual-family diagnosis artifact MUST record that
  evidence pack's manifest id, strict metrics, split row counts, and diagnosis
  boundary
- **AND** it MUST NOT read from or report an older manifest as current

#### Scenario: Refresh target selection from refreshed diagnosis
- **WHEN** formal remediation target-selection evidence is regenerated
- **THEN** it MUST read the refreshed residual-family diagnosis artifact
- **AND** it MUST carry forward the same source manifest id and strict metrics
- **AND** it MUST preserve the boundary that target selection is not training,
  not data generation, not prediction repair, and not evaluator relaxation

#### Scenario: Refresh residual-cluster inspection from refreshed diagnosis
- **WHEN** formal residual-cluster inspection evidence is regenerated
- **THEN** it MUST read the refreshed residual-family diagnosis artifact
- **AND** it MUST carry forward the same source manifest id, strict metrics,
  residual row counts, and residual field counts
- **AND** it MUST preserve the boundary that cluster inspection does not
  authorize data, training, prompt, prediction, or evaluator changes

#### Scenario: Refresh coverage current-evidence lineage without rewriting legacy provenance
- **WHEN** downstream form-fill confirmation-marker coverage evidence references
  the refreshed residual-cluster inspection as current residual evidence
- **THEN** it MUST record the refreshed formal held-out manifest id for that
  current residual evidence source
- **AND** it MUST preserve legacy policy, coverage-extension, materialized
  candidate, and formal public sample provenance instead of rewriting those
  historical sources to the newer manifest

#### Scenario: Validate refreshed public evidence boundaries
- **WHEN** refreshed residual diagnosis, target-selection reports, or companion
  Human Briefs are prepared for commit
- **THEN** validation MUST reject raw private rows, absolute local paths, private
  remote paths, host details, SSH details, secrets, tokens, raw logs,
  checkpoints, adapters, caches, and oversized generated corpora
- **AND** public summaries MUST keep strict `contract_exact_match` and strict
  `slot_f1` authoritative while labeling `slot_f1_soft` as diagnostic only

### Requirement: Publish merged slot value residual diagnosis evidence
The system SHALL publish public-safe residual diagnosis evidence for the merged slot-value held-out evaluation without changing strict evaluator semantics or model outputs.

#### Scenario: Diagnose residuals from available prediction artifacts
- **WHEN** gold public-sample rows and merged slot-value dev/test prediction artifacts are available
- **THEN** the diagnosis output MUST list each strict residual row by split, row id, task family, mismatch field paths, mismatch categories, and sanitized gold/prediction value summaries
- **AND** it MUST include aggregate residual counts by split, task family, field path, and category

#### Scenario: Separate strict metrics from soft diagnostics
- **WHEN** residual diagnosis references `contract_exact_match`, strict `slot_f1`, and `slot_f1_soft`
- **THEN** the report MUST keep strict `contract_exact_match` and strict `slot_f1` as authoritative metrics
- **AND** it MUST label `slot_f1_soft` as an internal diagnostic that does not repair, normalize, re-score, or replace strict predictions

#### Scenario: Preserve public-safe evidence boundaries
- **WHEN** residual diagnosis evidence is prepared for commit
- **THEN** leak-scan validation MUST reject raw private rows, absolute local paths, private remote paths, host details, SSH details, secrets, tokens, raw logs, checkpoints, adapters, caches, and oversized generated corpora

#### Scenario: Bound residual interpretation
- **WHEN** public reports or Human Briefs describe the residual diagnosis
- **THEN** they MUST state that this phase performs no training, prediction rerun, evaluator relaxation, semantic-equivalence scoring, slot normalization, prediction repair, prediction replacement, or prediction re-score
- **AND** they MUST NOT claim held-out recovery, model recovery, checkpoint release, adapter release, production readiness, public full-corpus release, private-corpus generalization, or live-browser benchmark improvement

#### Scenario: Recommend next bounded decision only
- **WHEN** diagnosis identifies the likely source of the remaining strict residuals
- **THEN** the report MAY recommend a next bounded OpenSpec phase
- **AND** it MUST NOT automatically materialize new data, change gold policy, launch training, or change evaluator behavior as part of the diagnosis phase

### Requirement: Publish sanitized A100 smoke evidence
The system SHALL produce a public-safe A100 SFT smoke evidence summary that reports training metadata, contract metrics, controlled smoke status, and leak-scan results without exposing private infrastructure or unreleased model artifacts.

#### Scenario: Generate smoke evidence report
- **WHEN** sanitized adapter metadata and public-sample predictions are available from the A100 SFT smoke
- **THEN** the system writes a machine-readable run manifest and a human-readable report that link the base model, manifest ID, metrics path, controlled smoke result, and release status without claiming a public checkpoint

#### Scenario: Validate evidence boundaries
- **WHEN** the evidence pack is prepared for commit
- **THEN** leak-scan validation rejects raw private rows, local absolute paths, secrets, tokens, private IP addresses, SSH details, and oversized generated corpora

#### Scenario: Separate smoke evidence from benchmark claims
- **WHEN** the public report describes A100 smoke results
- **THEN** it labels the result as a public-sample training smoke and contract-level evaluation, not as a live-browser benchmark improvement or production-readiness claim

### Requirement: Publish sanitized A100 trained-prediction evidence
The system SHALL produce a public-safe A100 trained-prediction evidence pack that reports sanitized predictions, contract metrics, controlled smoke status, and leak-scan results without exposing private infrastructure or unreleased model artifacts.

#### Scenario: Generate trained-prediction evidence report
- **WHEN** sanitized trained-path public-sample predictions are available
- **THEN** the system writes a machine-readable run manifest and a human-readable report that link the prediction artifact, base model, dataset manifest ID, metrics path, controlled smoke result, leak-scan result, and release status without claiming a public checkpoint

#### Scenario: Validate trained-prediction evidence boundaries
- **WHEN** the trained-prediction evidence pack is prepared for commit
- **THEN** leak-scan validation rejects raw private rows, local absolute paths, secrets, tokens, private IP addresses, SSH details, raw logs, checkpoints, adapters, caches, and oversized generated corpora

#### Scenario: Separate trained-prediction smoke from benchmark claims
- **WHEN** the public report describes trained-path prediction results
- **THEN** it labels the result as a public-sample prediction/evaluation smoke and separates contract metrics and controlled smoke from live-browser benchmark, production-readiness, or released-checkpoint claims

### Requirement: Publish public-safe contract-output recovery evidence
The system SHALL publish a public-safe recovery evidence pack for A100 SFT contract-output recovery that records schema-failure diagnosis, rerun metrics when available, controlled smoke status, leak-scan status, and claim boundaries without exposing private infrastructure or unreleased model artifacts.

#### Scenario: Record pre-recovery failure evidence
- **WHEN** the recovery evidence pack is generated from the previous trained-path prediction/evaluation smoke
- **THEN** it records the prior schema failure count, JSON validity rate, prediction source kind, dataset manifest ID, and report links without copying raw private logs, checkpoints, adapters, caches, host details, or private paths

#### Scenario: Compare post-rerun metrics
- **WHEN** sanitized post-recovery public-sample predictions and metrics are available
- **THEN** the evidence pack reports post-rerun contract metrics and controlled smoke status alongside the pre-recovery baseline while labeling the result as a public-sample recovery smoke

#### Scenario: Keep recovery claims bounded
- **WHEN** the public recovery report describes the phase
- **THEN** it states that results are schema/contract-level public-sample evidence only and makes no checkpoint release, production-readiness, full-private-corpus, or live-browser benchmark improvement claim

#### Scenario: Validate recovery evidence boundaries
- **WHEN** the recovery evidence pack is prepared for commit
- **THEN** leak-scan validation rejects raw private rows, local absolute paths, secrets, tokens, private IP addresses, SSH details, raw logs, checkpoints, adapters, caches, and oversized generated corpora

### Requirement: Publish post-recovery A100 rerun evidence
The system SHALL publish a public-safe post-recovery A100 rerun evidence pack that compares the rerun result with the pre-recovery trained-path schema-failure baseline without exposing private infrastructure or unreleased model artifacts.

#### Scenario: Record post-recovery prediction metrics
- **WHEN** sanitized post-recovery public-sample predictions are available
- **THEN** the evidence pack records prediction count, prediction source kind, dataset manifest ID, formatting policy, metrics path, JSON validity rate, schema failure count, and failure slices alongside links to the pre-recovery baseline

#### Scenario: Record post-recovery controlled smoke
- **WHEN** controlled execution smoke is run against the sanitized post-recovery predictions
- **THEN** the evidence pack records passed and failed counts, target fixture path, and notes that the result is a controlled public-sample smoke rather than a live-browser benchmark

#### Scenario: Validate post-recovery evidence boundaries
- **WHEN** the post-recovery evidence pack is prepared for commit
- **THEN** leak-scan validation rejects raw private rows, absolute local paths, secrets, tokens, private IP addresses, SSH details, raw logs, checkpoints, adapters, caches, oversized generated corpora, and private remote paths

#### Scenario: Bound post-recovery interpretation
- **WHEN** the public report describes the post-recovery rerun
- **THEN** it states whether schema validity improved, remained partial, or still failed using the observed metrics, and makes no checkpoint release, adapter release, full-private-corpus, production-readiness, or live-browser benchmark improvement claim

### Requirement: Diagnose training-prompt-decoding source alignment
The system SHALL provide public-safe diagnostics that connect Browser Task Contract schema-invalid prediction symptoms to training targets, prompt constraints, split coverage, prediction shape, and decoding evidence availability.

#### Scenario: Audit targets and prediction symptoms
- **WHEN** diagnostics are generated for public-sample gold rows and contract-like private-adapter predictions
- **THEN** the output MUST report whether gold targets contain path-like routes or list-shaped slots, whether predictions contain path-like routes or list-shaped slots, and whether invalid predictions remain invalid

#### Scenario: Audit prompt and split coverage
- **WHEN** diagnostics are generated with SFT training configuration and prediction metadata
- **THEN** the output MUST report the configured training split, prediction split, training row count, training route/task-type coverage, current prompt constraints, and whether the prediction-run metadata contains prompt-constraint evidence

#### Scenario: Audit decoding evidence boundaries
- **WHEN** diagnostics are generated for existing prediction metadata
- **THEN** the output MUST report decoding policy fields that are present and MUST record missing raw decoded sidecar, generated-token count, EOS, or finish-state evidence as evidence gaps rather than inferred causes

#### Scenario: Bound source-diagnostic claims
- **WHEN** source diagnostics are generated for private-adapter public-sample predictions
- **THEN** the report MUST state that it does not repair, normalize, coerce, or replace predictions and MUST NOT claim checkpoint release, adapter release, production readiness, full-private-corpus release, or live-browser benchmark improvement

### Requirement: Publish train-split overfit diagnostic evidence
The system SHALL publish public-safe train-split overfit diagnostic evidence that separates train-internal recovery from held-out generalization and live-browser claims.

#### Scenario: Generate train-split diagnostic manifest
- **WHEN** train-split diagnostic predictions, metrics, objective inspection, prompt snapshot, raw decoded summary, generation trace, and leak-scan results are available
- **THEN** the manifest MUST link those artifacts and record `prediction_split=train`, `overfit_diagnostic=true`, `generalization_claim=false`, release status, and claim boundaries

#### Scenario: Report diagnostic interpretation
- **WHEN** a human-readable train-split diagnostic report is generated
- **THEN** it MUST state whether train-internal schema/route/slot recovery was observed and MUST state that this does not prove dev/test generalization, production readiness, checkpoint release, adapter release, or live-browser benchmark improvement

#### Scenario: Validate diagnostic evidence boundaries
- **WHEN** diagnostic evidence is prepared for commit
- **THEN** leak-scan validation MUST reject raw private rows, local or remote private paths, secrets, private IP addresses, SSH details, raw logs, checkpoints, adapters, caches, oversized generated corpora, and private remote paths

### Requirement: Publish observed A100 train-split diagnostic result
The system SHALL publish a public-safe observed A100 train-split diagnostic evidence pack that records whether train-internal schema, route, slot, safety, and confirmation recovery was observed without claiming held-out generalization or release status.

#### Scenario: Import sanitized diagnostic evidence
- **WHEN** real train-split diagnostic predictions, metrics, objective inspection, prompt snapshot, sanitized raw decoded summary, generation trace, and leak-scan results are available
- **THEN** the manifest and report MUST link those sanitized artifacts, record `prediction_split=train`, `overfit_diagnostic=true`, `generalization_claim=false`, prediction source kind, release status, and claim boundaries without private runtime details

#### Scenario: Report observed recovery status
- **WHEN** the diagnostic report is generated from real private-adapter train-split predictions
- **THEN** it MUST state whether train-internal schema validity, route correctness, slot shape, safety decision, and confirmation behavior recovered, remained partial, or failed using observed metrics and failure slices

#### Scenario: Keep diagnostic evidence public-safe
- **WHEN** diagnostic evidence is prepared for commit
- **THEN** leak-scan validation MUST reject raw private rows, local or remote private paths, secrets, private IP addresses, SSH details, raw logs, checkpoints, adapters, caches, oversized generated corpora, and private remote paths

#### Scenario: Bound diagnostic interpretation
- **WHEN** public documentation or Human Briefs describe the diagnostic result
- **THEN** they MUST state that train-split overfit evidence does not prove dev/test generalization, production readiness, checkpoint release, adapter release, public full-corpus release, or live-browser benchmark improvement

### Requirement: Publish SFT target-template alignment evidence
The system SHALL publish a public-safe SFT target-template alignment evidence pack that links prior train-split failure evidence to training-target, prompt-template, label-mask, and adapter/base diagnostic findings without repairing or replacing predictions.

#### Scenario: Generate alignment evidence pack
- **WHEN** the local alignment diagnostic runs against committed public-sample rows, config templates, prior prediction metadata, and prior objective-inspection evidence
- **THEN** it MUST write machine-readable JSON and human-readable Markdown that summarize training-vs-prediction prompt alignment, assistant target span status, label-mask evidence status, chat-template evidence status, adapter/base metadata alignment, and evidence gaps

#### Scenario: Link prior failed diagnostic without changing it
- **WHEN** the alignment report references the prior A100 train-split diagnostic
- **THEN** it MUST link the prior prediction, metrics, objective-inspection, and report artifacts and MUST NOT alter, repair, normalize, coerce, or replace prior private-adapter prediction rows

#### Scenario: Keep alignment evidence public-safe
- **WHEN** SFT target-template alignment evidence is prepared for commit
- **THEN** leak-scan validation MUST reject raw private rows, local or remote private paths, secrets, private IP addresses, SSH details, raw logs, checkpoints, adapters, caches, oversized generated corpora, and private remote paths

#### Scenario: Bound alignment interpretation
- **WHEN** public documentation or Human Briefs describe the SFT target-template alignment diagnostic
- **THEN** they MUST state that the evidence narrows local formatting and metadata gaps only and does not prove model recovery, held-out generalization, release readiness, production readiness, or live-browser improvement

### Requirement: Publish public-safe SFT label provenance evidence
The system SHALL publish a public-safe SFT label provenance evidence pack that summarizes objective inspection provenance, label-mask status, evidence gaps, prior diagnostic links, and claim boundaries without exposing private runtime details.

#### Scenario: Generate label provenance evidence pack
- **WHEN** label provenance inspection output is prepared for committed evidence
- **THEN** the system MUST write machine-readable JSON and human-readable Markdown that report inspection status, label source, tokenizer/template status, collator status, prompt mask status, assistant-target loss status, evidence gaps, and prior diagnostic artifact links

#### Scenario: Keep evidence public-safe
- **WHEN** label provenance evidence is prepared for commit
- **THEN** leak-scan validation MUST reject raw private rows, local or remote private paths, secrets, private IP addresses, SSH details, raw logs, checkpoints, adapters, caches, oversized generated corpora, and private remote paths

#### Scenario: Bound label provenance interpretation
- **WHEN** public documentation or Human Briefs describe label provenance evidence
- **THEN** they MUST state whether true labels were inspected or unavailable and MUST NOT claim model recovery, held-out generalization, checkpoint release, adapter release, production readiness, or live-browser improvement

### Requirement: Publish runtime label provenance preparation evidence
The system SHALL publish a public-safe runtime label provenance preparation evidence pack that records readiness, blocked/skipped execution state, prior evidence links, validation status, and bounded interpretation.

#### Scenario: Generate preparation evidence pack
- **WHEN** runtime label provenance preparation metadata is generated from public-safe inputs
- **THEN** the system MUST write machine-readable JSON and human-readable Markdown that report runtime check status, private override status, output-root policy status, dependency policy, true label-mask status, evidence gaps, prior evidence links, and non-claim boundaries

#### Scenario: Keep preparation evidence public-safe
- **WHEN** runtime label provenance preparation evidence is prepared for commit
- **THEN** leak-scan validation MUST reject raw private rows, local or remote private paths, secrets, private IP addresses, SSH details, raw logs, checkpoints, adapters, caches, oversized generated corpora, and private remote paths

#### Scenario: Bound preparation interpretation
- **WHEN** public documentation or Human Briefs describe runtime label provenance preparation evidence
- **THEN** they MUST state that the phase prepared a later runtime check but did not run private A100 execution, inspect real labels, release a checkpoint or adapter, prove held-out generalization, claim production readiness, or claim live-browser improvement

### Requirement: Publish observed runtime label provenance evidence
The system SHALL publish a public-safe observed runtime label provenance evidence pack that records sanitized A100 runtime label inspection results and bounded interpretation without exposing private infrastructure or unreleased model artifacts.

#### Scenario: Generate observed runtime evidence pack
- **WHEN** sanitized runtime label provenance metadata is available from an authorized A100 execution or local objective-mask preparation path
- **THEN** the system MUST write machine-readable JSON and human-readable Markdown that report runtime check status, real label tensor availability, label source kind, tokenizer/template status, collator status, prompt mask status, assistant-target loss status, evidence gaps, prior evidence links, leak-scan status, package/runtime policy, and non-claim boundaries

#### Scenario: Keep observed runtime evidence public-safe
- **WHEN** observed runtime label provenance evidence is prepared for commit
- **THEN** leak-scan validation MUST reject raw private rows, local or remote private paths, secrets, private IP addresses, SSH details, raw logs, checkpoints, adapters, caches, model snapshots, oversized generated corpora, and private remote paths
#### Scenario: Separate label evidence from model-quality claims
- **WHEN** public documentation or Human Briefs describe observed runtime label provenance evidence
- **THEN** they MUST state whether real tokenizer/collator labels were inspected, whether prompt/system/user tokens were masked, and whether assistant contract tokens carried loss, and MUST NOT claim model recovery, held-out generalization, checkpoint release, adapter release, production readiness, public full-corpus release, or live-browser benchmark improvement

### Requirement: Publish assistant-only A100 train-split rerun evidence
The system SHALL publish a public-safe evidence pack for the assistant-only A100 train-split rerun that records objective-mask status, train-internal contract metrics, comparison context, and non-claim boundaries without exposing private infrastructure or unreleased model artifacts.

#### Scenario: Import sanitized rerun evidence
- **WHEN** assistant-only rerun adapter metadata, objective/runtime label metadata, predictions, prediction metadata, prompt snapshot, sanitized raw decoded summary, generation trace, metrics, and leak-scan results are available
- **THEN** the manifest and report MUST link those sanitized artifacts, record `prediction_split=train`, `overfit_diagnostic=true`, `generalization_claim=false`, prediction source kind, release status, loss-mask policy, and claim boundaries without private runtime details

#### Scenario: Report observed recovery status after objective repair
- **WHEN** the assistant-only rerun report is generated from real private-adapter train-split predictions
- **THEN** it MUST state whether train-internal schema validity, route correctness, slot shape, safety decision, and confirmation behavior recovered, remained partial, or failed using observed metrics and failure slices

#### Scenario: Compare against prior train-split diagnostic narrowly
- **WHEN** the rerun evidence references prior A100 train-split evidence
- **THEN** it MUST identify the prior evidence as pre-assistant-only-objective-repair context and MUST NOT treat a before/after difference as held-out generalization, checkpoint release, adapter release, production readiness, or live-browser benchmark improvement

#### Scenario: Keep rerun evidence public-safe
- **WHEN** assistant-only rerun evidence is prepared for commit
- **THEN** leak-scan validation MUST reject raw private rows, local or remote private paths, secrets, private IP addresses, SSH details, raw logs, checkpoints, adapters, model caches, oversized generated corpora, and private remote paths
#### Scenario: Bound rerun interpretation
- **WHEN** public documentation, metrics reports, Human Briefs, or loop reports describe the assistant-only rerun
- **THEN** they MUST state that train-split overfit evidence does not prove dev/test generalization, production readiness, checkpoint release, adapter release, public full-corpus release, or live-browser benchmark improvement

### Requirement: Publish assistant-only schema-output diagnosis
The system SHALL publish a public-safe diagnosis for assistant-only A100 rerun outputs that are raw-JSON parseable but fail the Browser Task Contract schema.

#### Scenario: Separate raw JSON parseability from contract schema validity
- **WHEN** assistant-only rerun raw decoded outputs are parseable JSON objects but contract metrics report `json_valid_rate=0.0000`
- **THEN** the diagnosis MUST state that raw JSON parseability is not the same as schema-valid Browser Task Contract output

#### Scenario: Report row-level schema-output failure patterns
- **WHEN** the diagnosis analyzes assistant-only rerun predictions
- **THEN** it MUST report prediction count, raw JSON parseable count, contract schema-valid count, affected row ids, missing required fields, contract field mismatches, and likely failure family without repairing or coercing the predictions

#### Scenario: Preserve train-internal and public-safe boundaries
- **WHEN** the diagnosis is prepared for commit or Human Brief documentation
- **THEN** it MUST state `prediction_split=train`, `overfit_diagnostic=true`, `generalization_claim=false`, and MUST NOT expose private paths, host details, SSH details, raw logs, checkpoints, adapters, private rows, tokens, or make checkpoint release, adapter release, production readiness, held-out generalization, public full-corpus release, or live-browser benchmark improvement claims

### Requirement: Publish required-field repair A100 rerun evidence
The system SHALL publish a public-safe evidence pack for the required-field repair A100 train-split rerun that separates raw attempt schema validity, retry attempt schema validity, validated output source, final contract metrics, and non-claim boundaries.

#### Scenario: Import sanitized rerun evidence
- **WHEN** rerun adapter metadata, objective/runtime label metadata, predictions, prediction metadata, prompt snapshot, sanitized raw decoded summary, generation trace, metrics, and leak-scan results are available
- **THEN** the manifest and report MUST link those sanitized artifacts, record `prediction_split=train`, `overfit_diagnostic=true`, `generalization_claim=false`, prediction source kind, release status, loss-mask policy, schema guard policy, and claim boundaries without private runtime details

#### Scenario: Report raw retry and validated outputs separately
- **WHEN** schema guard or retry metadata is available from rerun predictions
- **THEN** public reports and Human Briefs MUST separate raw attempt schema validity, retry attempt schema validity, validated output source, validated output schema validity, and final contract metrics

#### Scenario: Compare required-field repair narrowly
- **WHEN** the rerun evidence references prior assistant-only train-split evidence
- **THEN** it MUST identify the prior evidence as pre-required-field-repair context and MUST NOT treat any before/after difference as held-out generalization, checkpoint release, adapter release, production readiness, or live-browser benchmark improvement

#### Scenario: Keep rerun evidence public-safe
- **WHEN** required-field repair rerun evidence is prepared for commit
- **THEN** leak-scan validation MUST reject raw private rows, local or remote private paths, secrets, private IP addresses, SSH details, raw logs, checkpoints, adapters, model caches, oversized generated corpora, and private remote paths

#### Scenario: Bound rerun interpretation
- **WHEN** public documentation, metrics reports, Human Briefs, or loop reports describe the rerun
- **THEN** they MUST state that train-split overfit evidence does not prove dev/test generalization, production readiness, checkpoint release, adapter release, public full-corpus release, or live-browser benchmark improvement

### Requirement: Publish constrained-decoding diagnosis evidence
The system SHALL publish a public-safe local diagnosis for the constrained contract decoding repair that classifies required-field rerun raw and retry failures without treating the diagnosis as model-quality evidence.

#### Scenario: Classify required-field rerun failures
- **WHEN** required-field rerun raw and retry decoded summaries are available
- **THEN** the diagnosis MUST report prediction count, raw attempt schema-valid count, retry attempt schema-valid count, validated output schema-valid count, parse status counts, legacy enum/path-like route symptoms, prose-or-Markdown wrapper symptoms, and whether invalid predictions remain invalid

#### Scenario: Bound constrained-decoding interpretation
- **WHEN** public reports or Human Briefs describe the constrained decoding repair
- **THEN** they MUST state that the phase is local decoder/output-shape hardening and MUST NOT claim checkpoint release, adapter release, held-out generalization, production readiness, public full-corpus release, live-browser benchmark improvement, or A100 model recovery

#### Scenario: Validate diagnosis public safety
- **WHEN** constrained-decoding diagnosis evidence is prepared for commit
- **THEN** leak-scan validation MUST reject raw private rows, local or remote private paths, secrets, private IP addresses, SSH details, raw logs, checkpoints, adapters, model caches, oversized generated corpora, and private remote paths

### Requirement: Publish strict-retry A100 train-split prediction rerun evidence
The system SHALL publish a public-safe evidence pack for the strict-retry A100 train-split prediction rerun that separates raw attempt schema validity, retry attempt schema validity, validated output source, final contract metrics, constrained-decoding diagnosis, and non-claim boundaries.

#### Scenario: Import sanitized strict-retry rerun evidence
- **WHEN** strict-retry prediction metadata, predictions, prompt snapshot, sanitized raw decoded summary, generation trace, metrics, schema guard summary, constrained-decoding diagnosis, and leak-scan results are available
- **THEN** the manifest and report MUST link those sanitized artifacts, record `prediction_split=train`, `overfit_diagnostic=true`, `generalization_claim=false`, prediction source kind, release status, schema retry policy, strict retry interpretation, and claim boundaries without private runtime details

#### Scenario: Report strict-retry recovery status
- **WHEN** the strict-retry rerun report is generated from real private-adapter train-split predictions
- **THEN** it MUST report raw attempt schema-valid count, retry attempt schema-valid count, validated output schema-valid count, validated output source distribution, parse status counts, and final contract metrics separately

#### Scenario: Compare strict retry narrowly
- **WHEN** the rerun evidence references prior required-field repair evidence
- **THEN** it MUST identify the prior evidence as pre-strict-retry context and MUST NOT treat any before/after difference as held-out generalization, checkpoint release, adapter release, production readiness, or live-browser benchmark improvement

#### Scenario: Keep strict-retry evidence public-safe
- **WHEN** strict-retry rerun evidence is prepared for commit
- **THEN** leak-scan validation MUST reject raw private rows, local or remote private paths, secrets, private IP addresses, SSH details, raw logs, checkpoints, adapters, model caches, oversized generated corpora, and private remote paths

#### Scenario: Bound strict-retry interpretation
- **WHEN** public documentation, metrics reports, Human Briefs, or loop reports describe the strict-retry rerun
- **THEN** they MUST state that train-split prediction-only evidence does not prove dev/test generalization, production readiness, checkpoint release, adapter release, public full-corpus release, A100 model recovery, or live-browser benchmark improvement

### Requirement: Publish constrained-output repair evidence
The system SHALL publish a public-safe local evidence pack for constrained-output repair that records prompt constraint coverage, strict schema acceptance boundaries, validation status, and non-claim boundaries before any later A100 rerun.

#### Scenario: Generate constrained-output repair evidence
- **WHEN** the constrained-output repair is implemented and local validation passes
- **THEN** the evidence pack MUST record prompt constraint coverage, canonical one-shot visibility, gold-target exclusion, strict retry preservation, schema-valid whole-object acceptance, and validation commands without private runtime details

#### Scenario: Keep constrained-output repair evidence public-safe
- **WHEN** constrained-output repair evidence, Human Briefs, or loop reports are prepared for commit
- **THEN** leak-scan validation MUST reject raw private rows, local or remote private paths, secrets, private IP addresses, SSH details, raw logs, checkpoints, adapters, model caches, oversized generated corpora, and private remote paths

#### Scenario: Bound constrained-output repair interpretation
- **WHEN** public reports, metrics reports, Human Briefs, or loop reports describe the constrained-output repair
- **THEN** they MUST state that local prompt/output-shape hardening does not prove dev/test generalization, production readiness, checkpoint release, adapter release, public full-corpus release, A100 model recovery, or live-browser benchmark improvement

#### Scenario: Recommend later A100 rerun only after local repair
- **WHEN** constrained-output repair evidence is reviewed
- **THEN** the recommended next A100 step, if any, MUST be framed as a later explicitly authorized prediction rerun rather than evidence already produced by this local repair phase

### Requirement: Publish constrained-output A100 train-split rerun evidence
The system SHALL publish a public-safe evidence pack for the constrained-output A100 train-split prediction rerun that separates raw attempt schema validity, retry attempt schema validity, validated output source, parse statuses, prompt constraints, and final contract metrics.

#### Scenario: Import sanitized constrained-output rerun evidence
- **WHEN** constrained-output prediction metadata, predictions, prompt snapshot, sanitized raw decoded summary, generation trace, metrics, schema guard summary, constrained-output diagnosis, and leak-scan results are available
- **THEN** the committed evidence MUST contain only public-safe artifacts and MUST omit private override files, raw private logs, private paths, host details, checkpoints, adapters, model caches, tokens, and private corpus rows

#### Scenario: Report constrained-output rerun status
- **WHEN** the constrained-output rerun report is generated from real private-adapter train-split predictions
- **THEN** it MUST report prediction count, raw attempt schema-valid count, retry attempt schema-valid count, validated output schema-valid count, validated output source distribution, parse status distribution, prompt constraints present at prediction time, and final contract metrics separately

#### Scenario: Compare only against the strict-retry baseline
- **WHEN** the report compares this rerun to prior evidence
- **THEN** it MUST identify `reports/public-sample/a100-strict-retry-train-split-rerun/` as pre-constrained-output context and MUST NOT treat any before/after difference as held-out generalization, checkpoint release, adapter release, production readiness, public full-corpus release, or live-browser benchmark improvement

#### Scenario: Keep constrained-output rerun evidence public-safe
- **WHEN** evidence, Human Briefs, loop reports, or archived OpenSpec artifacts are prepared for commit
- **THEN** leak-scan validation MUST reject raw private rows, local or remote private paths, secrets, private IP addresses, SSH details, raw logs, checkpoints, adapters, model caches, oversized generated corpora, and private remote paths

#### Scenario: Bound constrained-output rerun interpretation
- **WHEN** public documentation, metrics reports, Human Briefs, or loop reports describe the constrained-output rerun
- **THEN** they MUST state that train-split prediction-only evidence does not prove dev/test generalization, production readiness, checkpoint release, adapter release, public full-corpus release, A100 model recovery, or live-browser benchmark improvement

### Requirement: Publish local route ontology repair evidence
The system SHALL publish public-safe local evidence for route ontology prompt repairs that distinguishes prompt readiness from model-output recovery.

#### Scenario: Generate local repair evidence
- **WHEN** a local route ontology repair phase completes
- **THEN** the evidence pack MUST record the prompt constraint summary, affected prompt surface, validation commands, and links to prior failure evidence without launching or implying private A100 execution

#### Scenario: Bound local repair interpretation
- **WHEN** public reports or Human Briefs describe local route ontology repair evidence
- **THEN** they MUST state that the phase did not train, did not run private adapter prediction, did not repair or coerce model outputs, and does not prove model recovery, held-out generalization, checkpoint release, adapter release, production readiness, public full-corpus release, or live-browser benchmark improvement

### Requirement: Publish route-ontology A100 train-split rerun evidence
The system SHALL publish a public-safe evidence pack for the route-ontology A100 train-split prediction rerun that separates raw attempt schema validity, retry attempt schema validity, validated output source, parse statuses, route validity, prompt constraints, and final contract metrics.

#### Scenario: Import sanitized route-ontology rerun evidence
- **WHEN** route-ontology prediction metadata, predictions, prompt snapshot, sanitized raw decoded summary, generation trace, metrics, schema guard summary, route-ontology diagnosis, and leak-scan results are available
- **THEN** the committed evidence MUST contain only public-safe artifacts and MUST omit private override files, raw private logs, private paths, host details, checkpoints, adapters, model caches, tokens, and private corpus rows

#### Scenario: Report route-ontology rerun status
- **WHEN** the route-ontology rerun report is generated from real private-adapter train-split predictions
- **THEN** it MUST report prediction count, raw attempt schema-valid count, retry attempt schema-valid count, validated output schema-valid count, route-valid count, invalid route values, validated output source distribution, parse status distribution, route ontology prompt constraints present at prediction time, and final contract metrics separately

#### Scenario: Compare only against the constrained-output baseline
- **WHEN** the report compares this rerun to prior evidence
- **THEN** it MUST identify `reports/public-sample/a100-constrained-output-train-split-rerun/` as pre-route-ontology-repair context and MUST NOT treat any before/after difference as held-out generalization, checkpoint release, adapter release, production readiness, public full-corpus release, or live-browser benchmark improvement

#### Scenario: Keep route-ontology rerun evidence public-safe
- **WHEN** evidence, Human Briefs, loop reports, or archived OpenSpec artifacts are prepared for commit
- **THEN** leak-scan validation MUST reject raw private rows, local or remote private paths, secrets, private IP addresses, SSH details, raw logs, checkpoints, adapters, model caches, oversized generated corpora, and private remote paths

#### Scenario: Bound route-ontology rerun interpretation
- **WHEN** public documentation, metrics reports, Human Briefs, or loop reports describe the route-ontology rerun
- **THEN** they MUST state that train-split prediction-only evidence does not prove dev/test generalization, production readiness, checkpoint release, adapter release, public full-corpus release, A100 model recovery, or live-browser benchmark improvement

### Requirement: Diagnose missing confirmation-required failures
The system SHALL surface missing `confirmation_required` as an explicit public-safe schema failure detail when predictions are contract-like enough for required-field diagnostics.

#### Scenario: Count missing confirmation-required
- **WHEN** diagnostic evidence is generated for prediction rows that omit `confirmation_required`
- **THEN** the diagnostic output MUST report a missing `confirmation_required` count without repairing, normalizing, coercing, or counting the affected predictions as schema-valid

#### Scenario: Bound confirmation-required repair interpretation
- **WHEN** local repair evidence, Human Briefs, or loop reports describe `confirmation_required` prompt or diagnostic changes
- **THEN** they MUST state that the phase is local prompt/evidence hardening only and MUST NOT claim private-adapter recovery, checkpoint release, adapter release, held-out generalization, production readiness, public full-corpus release, or live-browser benchmark improvement

### Requirement: Publish confirmation-required A100 train-split rerun evidence
The system SHALL publish a public-safe evidence pack for the confirmation-required A100 train-split prediction rerun that separates raw attempt schema validity, retry attempt schema validity, validated output source, parse statuses, `confirmation_required` presence, prompt constraints, and final contract metrics.

#### Scenario: Import sanitized confirmation-required rerun evidence
- **WHEN** confirmation-required prediction metadata, predictions, prompt snapshot, sanitized raw decoded summary, generation trace, metrics, schema guard summary, confirmation-required diagnosis, and leak-scan results are available
- **THEN** the committed evidence MUST contain only public-safe artifacts and MUST omit private override files, raw private logs, private paths, host details, checkpoints, adapters, model caches, tokens, and private corpus rows

#### Scenario: Report confirmation-required rerun status
- **WHEN** the confirmation-required rerun report is generated from real private-adapter train-split predictions
- **THEN** it MUST report prediction count, raw attempt schema-valid count, retry attempt schema-valid count, validated output schema-valid count, missing `confirmation_required` count, validated output source distribution, parse status distribution, prompt constraints present at prediction time, and final contract metrics separately

#### Scenario: Compare only against the route-ontology baseline
- **WHEN** the report compares this rerun to prior evidence
- **THEN** it MUST identify `reports/public-sample/a100-route-ontology-train-split-rerun/` as pre-confirmation-required-repair context and MUST NOT treat any before/after difference as held-out generalization, checkpoint release, adapter release, production readiness, public full-corpus release, or live-browser benchmark improvement

#### Scenario: Keep confirmation-required rerun evidence public-safe
- **WHEN** evidence, Human Briefs, loop reports, or archived OpenSpec artifacts are prepared for commit
- **THEN** leak-scan validation MUST reject raw private rows, local or remote private paths, secrets, private IP addresses, SSH details, raw logs, checkpoints, adapters, model caches, oversized generated corpora, and private remote paths

#### Scenario: Bound confirmation-required rerun interpretation
- **WHEN** public documentation, metrics reports, Human Briefs, or loop reports describe the confirmation-required rerun
- **THEN** they MUST state that train-split prediction-only evidence does not prove dev/test generalization, production readiness, checkpoint release, adapter release, public full-corpus release, A100 model recovery, or live-browser benchmark improvement

### Requirement: Publish confirmation-rerun row-mismatch diagnosis evidence
The system SHALL publish public-safe row-level mismatch diagnosis evidence for the confirmation-required A100 train-split rerun without changing model outputs or evaluator metrics.

#### Scenario: Compare confirmation rerun rows with train gold
- **WHEN** the diagnosis is generated from committed confirmation-required rerun predictions, train-split gold rows, metrics, and schema guard evidence
- **THEN** it MUST report row-level field comparisons for each prediction id and aggregate mismatch counts by field path and failure family

#### Scenario: Preserve source prediction status
- **WHEN** a row is schema-invalid, schema-valid but semantically mismatched, or schema-valid but not exact-match
- **THEN** the diagnosis MUST preserve the source row status and MUST NOT repair, normalize, coerce, replace, or re-score the prediction

#### Scenario: Separate residual failure families
- **WHEN** the human-readable report explains why `contract_exact_match` remains `0.0000`
- **THEN** it MUST distinguish missing required-field schema failure, task/route/safety semantic mismatch, and strict string-field exact-match mismatch

#### Scenario: Bound row-mismatch diagnosis claims
- **WHEN** evidence, Human Briefs, loop reports, or archived OpenSpec artifacts describe the diagnosis
- **THEN** they MUST state that the phase is local evidence-only analysis and MUST NOT claim A100 rerun recovery, held-out generalization, checkpoint release, adapter release, production readiness, public full-corpus release, model-quality improvement, or live-browser benchmark improvement

#### Scenario: Keep row-mismatch diagnosis public-safe
- **WHEN** the diagnosis artifacts are prepared for commit
- **THEN** leak-scan validation MUST reject raw private rows, local or remote private paths, secrets, private IP addresses, SSH details, raw logs, checkpoints, adapters, model caches, oversized generated corpora, and private remote paths

### Requirement: Publish confirmation-rerun normalized-command string-mismatch diagnosis evidence
The system SHALL publish public-safe normalized-command string-mismatch diagnosis evidence for the confirmation-required train-split rerun without changing source predictions, prompt behavior, decoding behavior, or evaluator metrics.

#### Scenario: Derive normalized-command diagnosis from row-mismatch evidence
- **WHEN** the diagnosis is generated from committed confirmation-rerun row-mismatch evidence
- **THEN** it MUST report `normalized_command` mismatch rows, aggregate mismatch counts, source artifact links, and strict metrics inherited from the source evidence

#### Scenario: Separate string mismatch contexts
- **WHEN** the report explains why `normalized_command` contributes to strict exact-match failures
- **THEN** it MUST distinguish strict string-only mismatch, mismatch co-occurring with schema required-field failure, and mismatch co-occurring with task/route/safety semantic mismatch

#### Scenario: Preserve strict evaluator interpretation
- **WHEN** normalized-command differences are reported
- **THEN** the diagnosis MUST NOT normalize, repair, coerce, replace, semantically score, mark equivalent, or re-score prediction fields or evaluator metrics

#### Scenario: Bound normalized-command diagnosis claims
- **WHEN** evidence, Human Briefs, loop reports, or archived OpenSpec artifacts describe the normalized-command diagnosis
- **THEN** they MUST state that the phase is local evidence-only analysis and MUST NOT claim A100 rerun recovery, held-out generalization, checkpoint release, adapter release, production readiness, public full-corpus release, model-quality improvement, or live-browser benchmark improvement

#### Scenario: Keep normalized-command diagnosis public-safe
- **WHEN** normalized-command diagnosis artifacts are prepared for commit
- **THEN** leak-scan validation MUST reject raw private rows, local or remote private paths, secrets, private IP addresses, SSH details, raw logs, checkpoints, adapters, model caches, oversized generated corpora, and private remote paths

### Requirement: Clarify strict normalized-command string-mismatch interpretation
The system SHALL make public-facing evaluation and evidence surfaces explain that `normalized_command` string mismatches are strict exact-match evidence unless a separately scoped metric explicitly defines normalization or semantic equivalence.

#### Scenario: Publish README interpretation boundary
- **WHEN** public documentation references `normalized_command` string mismatches or `contract_exact_match`
- **THEN** it MUST state that `contract_exact_match` remains a strict exact-match metric and that string differences are not automatically treated as semantic equivalents

#### Scenario: Publish evidence-pack interpretation boundary
- **WHEN** a public evidence pack explains the confirmation-rerun normalized-command string mismatch diagnosis
- **THEN** it MUST include a reviewer-facing policy note that distinguishes explanatory row-level string evidence from metric changes, prediction repair, normalization, semantic-equivalence scoring, or re-scoring

#### Scenario: Bound claims for strict string mismatch policy
- **WHEN** README, evidence notes, Human Briefs, loop reports, or archived OpenSpec artifacts describe the strict string mismatch policy
- **THEN** they MUST NOT claim A100 execution, training or prediction rerun, prompt change, evaluator metric change, checkpoint release, adapter release, held-out generalization, production readiness, public full-corpus release, model-quality improvement, or live-browser benchmark improvement

#### Scenario: Validate public-surface wording
- **WHEN** the strict string mismatch policy is prepared for commit
- **THEN** focused tests MUST verify that public-facing surfaces preserve the strict exact-match boundary and the no-semantic-equivalence/no-metric-change boundary

### Requirement: Publish normalized-command policy A100 rerun evidence
The system SHALL publish public-safe train-split evidence for the normalized-command policy A100 rerun that separates strict final metrics from normalized-command exact-string observations and preserves non-claim boundaries.

#### Scenario: Generate normalized-command rerun manifest
- **WHEN** train-split rerun predictions, metrics, prompt snapshot, raw decoded summary, generation trace, normalized-command diagnosis, and leak-scan results are available
- **THEN** the manifest MUST record `prediction_source_kind=private_a100_adapter`, `prediction_split=train`, `overfit_diagnostic=true`, `generalization_claim=false`, strict metric values, normalized-command exact-match counts, and claim boundaries without private paths or host details

#### Scenario: Report normalized-command exact-string diagnosis
- **WHEN** a normalized-command diagnosis is generated for the rerun
- **THEN** it MUST report per-row gold/predicted normalized-command summaries, exact-string match status, mismatch categories, aggregate exact-match counts, and whether the row was otherwise schema-valid without normalizing or re-scoring predictions

#### Scenario: Compare against prior A100 baseline narrowly
- **WHEN** the public report describes the rerun result
- **THEN** it MUST compare only against `reports/public-sample/a100-confirmation-required-train-split-rerun/` for train-split prediction-only evidence and MUST NOT present the comparison as dev/test generalization or model-quality improvement

#### Scenario: Validate normalized-command rerun evidence boundaries
- **WHEN** the evidence pack is prepared for commit
- **THEN** leak-scan validation MUST reject raw private rows, local or remote private paths, secrets, private IP addresses, SSH details, raw logs, checkpoints, adapters, caches, oversized generated corpora, and private remote paths

#### Scenario: Bound normalized-command rerun interpretation
- **WHEN** public documentation or Human Briefs describe the normalized-command rerun
- **THEN** they MUST state that the phase performs no training, checkpoint release, adapter release, evaluator metric change, semantic-equivalence scoring, prediction repair, prediction re-score, production-readiness claim, held-out generalization claim, public full-corpus release, model-quality claim, or live-browser benchmark improvement claim

### Requirement: Publish normalized-command rerun row-mismatch diagnosis evidence
The system SHALL publish public-safe row-level mismatch diagnosis evidence for the A100 normalized-command policy train-split rerun without changing source predictions, prompt behavior, decoding behavior, schema behavior, parser behavior, retry behavior, evaluator metrics, or source strict metric interpretation.

#### Scenario: Derive row-level mismatch diagnosis from prior public artifacts
- **WHEN** the diagnosis is generated
- **THEN** it MUST derive only from `reports/public-sample/a100-normalized-command-policy-train-split-rerun/` public-safe artifacts
- **AND** it MUST record `diagnostic_kind=a100_normalized_rerun_row_mismatch_diagnosis`
- **AND** it MUST preserve source strict metrics including `json_valid_rate=1/3`, `contract_exact_match=0.0`, `task_type_accuracy=0.0`, `route_accuracy=0.0`, `confirmation_accuracy=1/3`, and `slot_f1=0.0`

#### Scenario: Classify residual rows without repairing predictions
- **WHEN** row-level failures are reported
- **THEN** the diagnosis MUST report all three train rows and classify the primary failure families as one missing `confirmation_required` schema failure, one invalid `task_type` enum schema failure, and one schema-valid task/route/safety/slot mismatch
- **AND** invalid predictions MUST remain invalid
- **AND** field-level mismatches MUST remain visible for reviewer inspection

#### Scenario: Bound row-level diagnosis claims
- **WHEN** evidence, Human Briefs, loop reports, or archived OpenSpec artifacts describe the row-mismatch diagnosis
- **THEN** they MUST NOT claim A100 execution in this phase, training, prediction rerun, prompt change, decoding change, schema change, parser change, retry change, evaluator metric change, prediction repair, prediction replacement, prediction re-score, semantic-equivalence scoring, normalized-command normalization, checkpoint release, adapter release, held-out generalization, production readiness, public full-corpus release, model-quality improvement, or live-browser benchmark improvement

#### Scenario: Keep row-level diagnosis public-safe
- **WHEN** diagnosis artifacts are prepared for commit
- **THEN** leak-scan validation MUST reject raw private rows, local or remote private paths, secrets, private IP addresses, SSH details, raw logs, checkpoints, adapters, caches, oversized generated corpora, and private remote paths

### Requirement: Publish public-readonly search contract policy evidence
The system SHALL publish public-safe local evidence for public-readonly search contract policy hardening that links back to the prior row-level mismatch diagnosis without claiming model recovery.

#### Scenario: Generate local policy evidence
- **WHEN** the public-readonly search policy evidence pack is generated
- **THEN** it MUST record the source prior phase `reports/public-sample/a100-normalized-rerun-row-mismatch-diagnosis/`
- **AND** it MUST report the source row mismatch family counts for missing `confirmation_required`, invalid `task_type` enum, and schema-valid task/route/safety/slot mismatch
- **AND** it MUST record prompt constraint flags for public-readonly search policy visibility, `public_readonly` safety reason visibility, search query slot guidance visibility, and task-type-not-route-enum guidance visibility

#### Scenario: Bound local policy evidence claims
- **WHEN** reports, Human Briefs, loop reports, or archived OpenSpec artifacts describe this phase
- **THEN** they MUST state that it is local prompt/policy hardening only
- **AND** they MUST NOT claim A100 execution, training, prediction rerun, decoder repair, schema repair, evaluator metric change, semantic-equivalence scoring, slot normalization, prediction repair, prediction re-score, checkpoint release, adapter release, held-out generalization, production readiness, public full-corpus release, model-quality improvement, or live-browser benchmark improvement

#### Scenario: Keep policy evidence public-safe
- **WHEN** the evidence pack is prepared for commit
- **THEN** leak-scan validation MUST reject raw private rows, local or remote private paths, secrets, private IP addresses, SSH details, raw logs, checkpoints, adapters, caches, oversized generated corpora, and private remote paths

### Requirement: Publish public-readonly search policy A100 rerun evidence
The system SHALL publish public-safe train-split evidence for the public-readonly search policy A100 rerun that separates strict final metrics from row-level task type, route, safety, confirmation, slot, normalized-command, and schema observations while preserving non-claim boundaries.

#### Scenario: Generate public-readonly search rerun manifest
- **WHEN** train-split rerun predictions, metrics, prompt snapshot, raw decoded summary, generation trace, row-level diagnosis, schema guard summary, and leak-scan results are available
- **THEN** the manifest MUST record `prediction_source_kind=private_a100_adapter`, `prediction_split=train`, `overfit_diagnostic=true`, `generalization_claim=false`, strict metric values, row-level field counts, and claim boundaries without private paths or host details

#### Scenario: Report public-readonly search field diagnosis
- **WHEN** a public-readonly search policy diagnosis is generated for the rerun
- **THEN** it MUST report per-row gold/predicted field summaries, exact field match status for `task_type`, `route`, `safety.reason`, `confirmation_required`, `slots`, and `normalized_command`, aggregate field counts, family counts, and whether the row was otherwise schema-valid without normalizing or re-scoring predictions

#### Scenario: Compare against prior A100 baseline narrowly
- **WHEN** the public report describes the rerun result
- **THEN** it MUST compare only against `reports/public-sample/a100-normalized-command-policy-train-split-rerun/` for train-split prediction-only evidence and MUST NOT present the comparison as dev/test generalization or model-quality improvement

#### Scenario: Validate public-readonly search rerun evidence boundaries
- **WHEN** the evidence pack is prepared for commit
- **THEN** leak-scan validation MUST reject raw private rows, local or remote private paths, secrets, private IP addresses, SSH details, raw logs, checkpoints, adapters, caches, oversized generated corpora, and private remote paths

#### Scenario: Bound public-readonly search rerun interpretation
- **WHEN** public documentation or Human Briefs describe the public-readonly search policy rerun
- **THEN** they MUST state that the phase performs no training, checkpoint release, adapter release, evaluator metric change, semantic-equivalence scoring, slot normalization, prediction repair, prediction re-score, production-readiness claim, held-out generalization claim, public full-corpus release, model-quality claim, or live-browser benchmark improvement claim

### Requirement: Publish output-boundary retry-policy repair evidence
The system SHALL publish public-safe local evidence for the public-readonly output-boundary and retry-prompt repair while preserving strict metrics and prior A100 negative evidence.

#### Scenario: Generate local repair manifest
- **WHEN** the local prompt/retry policy repair is complete
- **THEN** the manifest MUST link the prior A100 public-readonly rerun evidence, record prompt constraint flags for single-root object and retry JSON-only guidance, and state that no A100 execution, training, private prediction, prediction repair, or evaluator metric change occurred

#### Scenario: Bound repair interpretation
- **WHEN** public documentation or Human Briefs describe the repair
- **THEN** they MUST state that this phase only prepares a later rerun and does not prove model recovery, held-out generalization, production readiness, checkpoint release, adapter release, model-quality improvement, or live-browser benchmark improvement

#### Scenario: Validate repair evidence boundaries
- **WHEN** the repair evidence pack is prepared for commit
- **THEN** leak-scan validation MUST reject raw private rows, local or remote private paths, secrets, private IP addresses, SSH details, raw logs, checkpoints, adapters, caches, oversized generated corpora, and private remote paths

### Requirement: Publish output-boundary retry-policy A100 rerun evidence
The system SHALL publish public-safe train-split evidence for the output-boundary retry-policy A100 rerun that separates strict final metrics from row-level schema boundary, retry wrapper, task type, route, safety, confirmation, slot, and normalized-command observations while preserving non-claim boundaries.

#### Scenario: Generate output-boundary retry-policy rerun manifest
- **WHEN** train-split rerun predictions, metrics, prompt snapshot, raw decoded summary, generation trace, row-level diagnosis, schema guard summary, and leak-scan results are available
- **THEN** the manifest MUST record `prediction_source_kind=private_a100_adapter`, `prediction_split=train`, `overfit_diagnostic=true`, `generalization_claim=false`, strict metric values, row-level field counts, retry and parser status counts, prompt/retry policy visibility, and claim boundaries without private paths or host details

#### Scenario: Report output-boundary retry diagnosis
- **WHEN** an output-boundary retry-policy diagnosis is generated for the rerun
- **THEN** it MUST report per-row gold/predicted field summaries, raw and retry parse status, exact field match status for `task_type`, `route`, `safety.reason`, `confirmation_required`, `slots`, and `normalized_command`, aggregate field counts, family counts, and whether the row was otherwise schema-valid without normalizing or re-scoring predictions

#### Scenario: Compare against prior A100 and local repair evidence narrowly
- **WHEN** the public report describes the rerun result
- **THEN** it MUST compare only against `reports/public-sample/a100-public-readonly-search-policy-train-split-rerun/` and `reports/public-sample/public-readonly-output-boundary-retry-policy/` and MUST NOT present the comparison as dev/test generalization or model-quality improvement

#### Scenario: Validate output-boundary retry rerun evidence boundaries
- **WHEN** the evidence pack is prepared for commit
- **THEN** leak-scan validation MUST reject raw private rows, local or remote private paths, secrets, private IP addresses, SSH details, raw logs, checkpoints, adapters, caches, oversized generated corpora, and private remote paths

#### Scenario: Bound output-boundary retry rerun interpretation
- **WHEN** public documentation or Human Briefs describe the output-boundary retry-policy rerun
- **THEN** they MUST state that the phase performs no training, checkpoint release, adapter release, evaluator metric change, semantic-equivalence scoring, slot normalization, prediction repair, prediction re-score, production-readiness claim, held-out generalization claim, public full-corpus release, model-quality claim, or live-browser benchmark improvement claim

### Requirement: Publish schema retry wrapper-boundary evidence
The system SHALL publish public-safe local evidence for schema retry wrapper-boundary hardening that connects the repair to prior A100 diagnosis without changing strict metrics or claiming model recovery.

#### Scenario: Generate retry wrapper-boundary manifest
- **WHEN** local retry-wrapper repair evidence is prepared
- **THEN** the manifest MUST record the source A100 diagnosis, prompt boundary constraints, generated artifacts, validation commands, leak-scan results, and non-claim boundaries

#### Scenario: Bound retry wrapper-boundary claims
- **WHEN** evidence, reports, tests, specs, or Human Briefs describe this phase
- **THEN** they MUST state that no A100 execution, training, private prediction rerun, parser relaxation, evaluator metric change, prediction repair, prediction re-score, semantic-equivalence scoring, slot normalization, checkpoint release, adapter release, held-out generalization claim, model-quality claim, or live-browser benchmark improvement claim is made

#### Scenario: Validate retry wrapper-boundary privacy
- **WHEN** the evidence pack is prepared for commit
- **THEN** leak-scan validation MUST reject raw private rows, local or remote private paths, secrets, private IP addresses, SSH details, raw logs, checkpoints, adapters, caches, private overrides, and private remote paths

### Requirement: Publish schema retry wrapper-boundary A100 rerun evidence
The system SHALL publish public-safe train-split evidence for the schema retry wrapper-boundary A100 rerun that separates strict final metrics from row-level retry wrapper, task type, route, safety, confirmation, slot, and normalized-command observations while preserving non-claim boundaries.

#### Scenario: Generate retry wrapper-boundary rerun manifest
- **WHEN** train-split rerun predictions, metrics, prompt snapshot, raw decoded summary, generation trace, row-level diagnosis, schema guard summary, and leak-scan results are available
- **THEN** the manifest MUST record `prediction_source_kind=private_a100_adapter`, `prediction_split=train`, `overfit_diagnostic=true`, `generalization_claim=false`, strict metric values, row-level counts, retry wrapper counts, prompt/retry policy visibility, and claim boundaries without private paths or host details

#### Scenario: Compare only against bounded prior evidence
- **WHEN** the public report describes the rerun result
- **THEN** it MUST compare only against `reports/public-sample/a100-output-boundary-retry-policy-train-split-rerun/` and `reports/public-sample/schema-retry-wrapper-boundary-policy/` and MUST NOT present the comparison as held-out generalization or model-quality improvement

#### Scenario: Bound retry wrapper-boundary rerun interpretation
- **WHEN** public documentation or Human Briefs describe the rerun
- **THEN** they MUST state that the phase performs no training, checkpoint release, adapter release, parser relaxation, evaluator metric change, semantic-equivalence scoring, slot normalization, prediction repair, prediction re-score, production-readiness claim, held-out generalization claim, model-quality claim, or live-browser benchmark improvement claim

### Requirement: Publish retry decoding stop-boundary diagnosis
The system SHALL publish public-safe local evidence that separates observed generation facts, retry wrapper symptoms, and retry stop-boundary evidence gaps after the A100 schema retry wrapper-boundary rerun.

#### Scenario: Record observed decoding facts
- **WHEN** the diagnosis is generated from the latest public-safe A100 sidecars
- **THEN** it MUST record raw attempt generation finish state, EOS visibility, generated token counts, max token limit, retry parse status, retry wrapper counts, and strict final metrics without changing any predictions

#### Scenario: Record retry evidence gaps
- **WHEN** retry decoded summaries are available but retry generation traces are not available
- **THEN** the diagnosis MUST state that retry attempt EOS/stop-token/generated-token evidence is missing and MUST NOT infer retry stop behavior from raw attempt traces

#### Scenario: Bound diagnosis claims
- **WHEN** evidence, reports, tests, specs, or Human Briefs describe this phase
- **THEN** they MUST state that no A100 execution, training, private prediction rerun, decoding change, parser relaxation, evaluator metric change, prediction repair, prediction re-score, semantic-equivalence scoring, slot normalization, checkpoint release, adapter release, model recovery claim, model-quality claim, or live-browser benchmark improvement claim is made

### Requirement: Publish retry generation trace instrumentation evidence
The system SHALL publish public-safe local evidence that retry generation trace instrumentation is available for future trained-adapter prediction exports without changing strict evaluation semantics.

#### Scenario: Generate instrumentation evidence pack
- **WHEN** the instrumentation phase is complete
- **THEN** the evidence pack MUST record source diagnosis links, generated artifacts, validation commands, leak-scan results, local test evidence for raw and retry attempt trace rows, and non-claim boundaries

#### Scenario: Bound instrumentation claims
- **WHEN** evidence, reports, tests, specs, or Human Briefs describe this phase
- **THEN** they MUST state that no A100 execution, training, private prediction rerun, decoding change, parser relaxation, evaluator metric change, prediction repair, prediction re-score, semantic-equivalence scoring, slot normalization, checkpoint release, adapter release, model recovery claim, model-quality claim, or live-browser benchmark improvement claim is made

#### Scenario: Preserve historical A100 interpretation
- **WHEN** the instrumentation evidence references prior A100 retry-wrapper artifacts
- **THEN** it MUST state that prior A100 `generation_trace.jsonl` files only prove their recorded fields and are not rewritten or upgraded by this local instrumentation phase

### Requirement: Publish A100 retry generation trace rerun evidence
The system SHALL publish public-safe train-split evidence for the retry generation trace A100 rerun that separates strict final metrics from raw/retry attempt generation-trace observations while preserving non-claim boundaries.

#### Scenario: Generate retry trace rerun manifest
- **WHEN** train-split rerun predictions, metrics, prompt snapshot, raw decoded summary, generation trace, retry-trace diagnosis, schema guard summary, and leak-scan results are available
- **THEN** the manifest MUST record `prediction_source_kind=private_a100_adapter`, `prediction_split=train`, `overfit_diagnostic=true`, `generalization_claim=false`, strict metric values, raw/retry trace attempt counts, retry wrapper counts, prompt/retry policy visibility, and claim boundaries without private paths or host details

#### Scenario: Report retry trace diagnosis
- **WHEN** a retry trace diagnosis is generated
- **THEN** it MUST report per-row raw/retry trace availability, generated token count, max token limit, EOS visibility, finish state, retry parse status, retry wrapper status, strict final schema validity, and whether any retry stop-boundary claim remains unproven

#### Scenario: Compare only against bounded prior evidence
- **WHEN** the public report describes the rerun result
- **THEN** it MUST compare only against `reports/public-sample/a100-schema-retry-wrapper-boundary-rerun/` and `reports/public-sample/retry-generation-trace-instrumentation/` and MUST NOT present the comparison as held-out generalization or model-quality improvement

#### Scenario: Bound retry trace rerun interpretation
- **WHEN** public documentation or Human Briefs describe the rerun
- **THEN** they MUST state that the phase performs no training, checkpoint release, adapter release, decoding behavior change, retry prompt change, parser relaxation, evaluator metric change, semantic-equivalence scoring, slot normalization, prediction repair, prediction re-score, production-readiness claim, held-out generalization claim, model-quality claim, public full-corpus release, or live-browser benchmark improvement claim

### Requirement: Diagnose retry trace finish-state boundaries
The system SHALL publish a public-safe local diagnosis that explains retry generation trace finish-state semantics without changing decoding behavior or model outputs.

#### Scenario: Interpret finish state without overclaiming stop reason
- **WHEN** retry generation trace rows show `finish_state=no_eos_observed`
- **THEN** the diagnosis MUST state that tokenizer EOS was not observed in the generated token slice and MUST NOT claim the actual generation stop reason unless the evidence directly records model/generation-config stop reason

#### Scenario: Report max-token evidence
- **WHEN** retry generated token counts are below `max_new_tokens`
- **THEN** the diagnosis MUST report per-row generated token count, max token limit, max-token-hit status, EOS visibility, and finish state

#### Scenario: Preserve local diagnostic boundaries
- **WHEN** public documentation or Human Briefs describe the diagnosis
- **THEN** they MUST state that the phase performs no A100 execution, prediction rerun, training, decoding behavior change, retry prompt change, parser relaxation, evaluator metric change, prediction repair, semantic-equivalence scoring, model-quality claim, public full-corpus release, or live-browser benchmark improvement claim

### Requirement: Publish generation stop-boundary instrumentation evidence
The system SHALL publish public-safe local evidence that stop-boundary generation trace instrumentation is available for future trained-adapter prediction exports while preserving strict evaluation and claim boundaries.

#### Scenario: Generate instrumentation evidence pack
- **WHEN** the stop-boundary instrumentation phase is complete
- **THEN** the evidence pack MUST record source diagnosis links, generated artifacts, validation commands, leak-scan results, local test evidence for stop-boundary trace fields, and non-claim boundaries

#### Scenario: Bound instrumentation claims
- **WHEN** evidence, reports, tests, specs, or Human Briefs describe this phase
- **THEN** they MUST state that no A100 execution, training, private prediction rerun, decoding change, retry prompt change, parser relaxation, evaluator metric change, prediction repair, prediction re-score, semantic-equivalence scoring, slot normalization, checkpoint release, adapter release, model recovery claim, model-quality claim, public full-corpus release, or live-browser benchmark improvement claim is made

#### Scenario: Preserve historical A100 interpretation
- **WHEN** the instrumentation evidence references prior A100 retry trace artifacts
- **THEN** it MUST state that prior A100 `generation_trace.jsonl` files only prove their recorded fields and are not rewritten or upgraded by this local instrumentation phase

### Requirement: Publish A100 generation stop-boundary rerun evidence
The system SHALL publish public-safe train-split evidence for the A100 generation stop-boundary rerun that separates strict final metrics from raw/retry stop-boundary trace observations while preserving non-claim boundaries.

#### Scenario: Generate stop-boundary rerun manifest
- **WHEN** train-split rerun predictions, metrics, prompt snapshot, raw decoded summary, generation trace, stop-boundary diagnosis, schema guard summary, and leak-scan results are available
- **THEN** the manifest MUST record `prediction_source_kind=private_a100_adapter`, `prediction_split=train`, `overfit_diagnostic=true`, `generalization_claim=false`, strict metric values, raw/retry trace attempt counts, stop-boundary field coverage, retry wrapper counts, prompt/retry policy visibility, and claim boundaries without private paths or host details

#### Scenario: Report stop-boundary diagnosis
- **WHEN** a stop-boundary diagnosis is generated
- **THEN** it MUST report per-row raw/retry trace availability, generated token count, max-token limit, max-token-hit status, EOS visibility, finish state, finish-state basis, stop-boundary evidence, actual-stop-reason-recorded status, actual stop reason, retry parse status, retry wrapper status, strict final schema validity, and whether any real stop-reason claim remains unproven

#### Scenario: Compare only against bounded prior evidence
- **WHEN** the public report describes the rerun result
- **THEN** it MUST compare only against `reports/public-sample/a100-retry-generation-trace-rerun/` and `reports/public-sample/generation-stop-reason-boundary-instrumentation/` and MUST NOT present the comparison as held-out generalization or model-quality improvement

#### Scenario: Bound stop-boundary rerun interpretation
- **WHEN** public documentation or Human Briefs describe the rerun
- **THEN** they MUST state that the phase performs no training, checkpoint release, adapter release, decoding behavior change, retry prompt change, parser relaxation, evaluator metric change, semantic-equivalence scoring, slot normalization, prediction repair, prediction re-score, production-readiness claim, held-out generalization claim, model-quality claim, public full-corpus release, or live-browser benchmark improvement claim

### Requirement: Publish retry JSON-only boundary hardening evidence
The system SHALL publish public-safe local evidence for schema-retry JSON-only boundary hardening while preserving strict-metric and non-claim boundaries.

#### Scenario: Generate local retry-boundary evidence pack
- **WHEN** the local retry-boundary hardening phase completes
- **THEN** the evidence pack MUST include a manifest, summary report, leak-scan results, source links to the prior A100 stop-boundary rerun, retry prompt constraint visibility, focused test evidence, validation commands, and explicit non-claims

#### Scenario: Bound interpretation of local hardening
- **WHEN** public documentation or Human Briefs describe the retry-boundary hardening phase
- **THEN** they MUST state that the phase performs no A100 execution, training, checkpoint release, adapter release, parser relaxation, evaluator metric change, semantic-equivalence scoring, slot normalization, prediction repair, prediction re-score, held-out generalization claim, model recovery claim, model-quality claim, public full-corpus release, or live-browser benchmark improvement claim

#### Scenario: Preserve prior A100 evidence interpretation
- **WHEN** the evidence pack references the prior A100 generation stop-boundary rerun
- **THEN** it MUST state that the prior strict final metrics remain `json_valid_rate=0.0` and `contract_exact_match=0.0`, and that this local phase does not prove any change in trained-adapter output behavior until a later real A100 rerun is performed

### Requirement: Publish A100 retry JSON-only boundary rerun evidence
The system SHALL publish public-safe train-split evidence for the A100 retry JSON-only boundary rerun that separates strict final metrics from retry-boundary observations and non-claims.

#### Scenario: Generate retry-boundary rerun manifest
- **WHEN** rerun predictions, metrics, prompt snapshot, raw decoded summary, generation trace, retry-boundary diagnosis, schema guard summary, and leak-scan results are available
- **THEN** the manifest MUST record `prediction_source_kind=private_a100_adapter`, `prediction_split=train`, `overfit_diagnostic=true`, `generalization_claim=false`, strict metric values, retry prompt constraint visibility, raw/retry parse status counts, retry wrapper counts, schema-valid counts, source artifact links, and claim boundaries without private paths or host details

#### Scenario: Report retry-boundary outcome
- **WHEN** a retry-boundary diagnosis is generated
- **THEN** it MUST report per-row raw parse status, retry parse status, retry wrapper status, validated output source, strict schema validity, retry trace availability, and whether strict final metrics improved relative to the bounded prior A100 stop-boundary rerun

#### Scenario: Bound rerun interpretation
- **WHEN** public documentation or Human Briefs describe the rerun
- **THEN** they MUST state that the phase performs no training, checkpoint release, adapter release, parser relaxation, evaluator metric change, semantic-equivalence scoring, slot normalization, prediction repair, prediction re-score, held-out generalization claim, production-readiness claim, model-quality claim, public full-corpus release, or live-browser benchmark improvement claim

### Requirement: Publish retry template boundary evidence
The system SHALL publish public-safe local evidence for schema-retry template/decoding-boundary hardening while preserving strict metrics, prior A100 evidence interpretation, and non-claim boundaries.

#### Scenario: Generate local retry template evidence pack
- **WHEN** the local retry template boundary phase completes
- **THEN** the evidence pack MUST include a manifest, summary report, leak-scan results, source links to the prior retry JSON-only hardening and A100 retry JSON-only rerun, retry template boundary metadata, focused test evidence, validation commands, and explicit non-claims

#### Scenario: Bound interpretation of local template hardening
- **WHEN** public documentation or Human Briefs describe the retry template boundary phase
- **THEN** they MUST state that the phase performs no A100 execution, training, checkpoint release, adapter release, parser relaxation, evaluator metric change, semantic-equivalence scoring, slot normalization, prediction repair, prediction re-score, held-out generalization claim, model recovery claim, model-quality claim, public full-corpus release, or live-browser benchmark improvement claim

#### Scenario: Preserve prior A100 evidence interpretation
- **WHEN** the evidence pack references the prior A100 retry JSON-only boundary rerun
- **THEN** it MUST state that the prior strict final metrics remain `json_valid_rate=0.0` and `contract_exact_match=0.0`, retry attempts remained wrapped fragments, and this local phase does not prove any change in trained-adapter output behavior until a later real A100 rerun is performed

### Requirement: Publish A100 retry template boundary rerun evidence
The system SHALL publish public-safe train-split evidence for the A100 retry template boundary rerun that separates strict final metrics from retry-template observations and non-claims.

#### Scenario: Generate retry template rerun manifest
- **WHEN** rerun predictions, metrics, prompt snapshot, raw decoded summary, generation trace, retry-template boundary diagnosis, schema guard summary, and leak-scan results are available
- **THEN** the manifest MUST record `prediction_source_kind=private_a100_adapter`, `prediction_split=train`, `overfit_diagnostic=true`, `generalization_claim=false`, strict metric values, retry-template boundary metadata, raw/retry parse status counts, retry wrapper counts, schema-valid counts, source artifact links, and claim boundaries without private paths or host details

#### Scenario: Report retry template outcome
- **WHEN** a retry-template boundary diagnosis is generated
- **THEN** it MUST report per-row raw parse status, retry parse status, retry wrapper status, validated output source, strict schema validity, retry template boundary visibility, generation trace availability, and whether strict final metrics improved relative to the bounded prior A100 retry JSON-only rerun

#### Scenario: Preserve prior local and A100 evidence interpretation
- **WHEN** the evidence pack references prior artifacts
- **THEN** it MUST link `reports/public-sample/retry-template-decoding-boundary/` as local template-boundary evidence and `reports/public-sample/a100-retry-json-only-boundary-rerun/` as the prior A100 baseline, while stating that only the new rerun can support observed trained-adapter behavior claims for this template boundary

#### Scenario: Bound rerun interpretation
- **WHEN** public documentation or Human Briefs describe the rerun
- **THEN** they MUST state that the phase performs no training, checkpoint release, adapter release, parser relaxation, evaluator metric change, semantic-equivalence scoring, slot normalization, prediction repair, prediction re-score, held-out generalization claim, production-readiness claim, public full-corpus release, live-browser benchmark improvement claim, or model-quality claim

### Requirement: Publish retry-template slot exact-match mismatch diagnosis
The system SHALL publish public-safe row-level diagnosis evidence for the residual exact-match failures after the A100 retry-template boundary rerun without changing source predictions, prompt behavior, decoding behavior, schema behavior, parser behavior, retry behavior, evaluator metrics, or source strict metric interpretation.

#### Scenario: Derive slot mismatch diagnosis from prior public artifacts
- **WHEN** the diagnosis is generated
- **THEN** it MUST derive only from `reports/public-sample/a100-retry-template-boundary-rerun/` public-safe artifacts
- **AND** it MUST record `diagnostic_kind=retry_template_slot_exact_match_mismatch_diagnosis`
- **AND** it MUST preserve source strict metrics including `json_valid_rate=1.0`, `contract_exact_match=0.0`, `task_type_accuracy=1.0`, `route_accuracy=1.0`, `confirmation_accuracy=1.0`, and `slot_f1=0.0`

#### Scenario: Classify residual slot exact-match failures
- **WHEN** row-level failures are reported
- **THEN** the diagnosis MUST report all three train rows and classify the residual slot mismatch families as two rows with `city/date` slot shape instead of gold `query` and one row with a `query` slot exact-string mismatch
- **AND** it MUST report normalized-command exact-string mismatch context when present
- **AND** field-level gold and prediction summaries MUST remain visible for reviewer inspection

#### Scenario: Bound slot diagnosis claims
- **WHEN** evidence, Human Briefs, loop reports, or archived OpenSpec artifacts describe the slot mismatch diagnosis
- **THEN** they MUST NOT claim A100 execution in this phase, training, prediction rerun, prompt change, decoding change, schema change, parser change, retry change, evaluator metric change, prediction repair, prediction replacement, prediction re-score, semantic-equivalence scoring, slot normalization, normalized-command normalization, checkpoint release, adapter release, held-out generalization, production readiness, public full-corpus release, model-quality improvement, or live-browser benchmark improvement

#### Scenario: Keep slot diagnosis public-safe
- **WHEN** diagnosis artifacts are prepared for commit
- **THEN** leak-scan validation MUST reject raw private rows, local or remote private paths, secrets, private IP addresses, SSH details, raw logs, checkpoints, adapters, caches, oversized generated corpora, and private remote paths

### Requirement: Publish search query slot target policy evidence
The system SHALL publish public-safe evidence that the canonical public-readonly search query slot target policy is visible in prompts and aligned in public sample targets without re-scoring historical predictions.

#### Scenario: Generate search query slot policy evidence pack
- **WHEN** the local policy phase completes
- **THEN** the evidence pack MUST include prompt constraint metadata, public sample row checks, DPO chosen/rejected contract checks, source links, validation commands, leak-scan results, and explicit non-claims
- **AND** it MUST record that no A100 execution, training, prediction rerun, evaluator change, parser change, semantic-equivalence scoring, slot normalization, prediction repair, prediction replacement, or re-score was performed

#### Scenario: Bound policy interpretation
- **WHEN** evidence, Human Briefs, loop reports, or archived OpenSpec artifacts describe the search query slot target policy
- **THEN** they MUST state that prior A100 predictions remain historical evidence and are not repaired, normalized, re-scored, or reinterpreted as exact-match recovery
- **AND** they MUST NOT claim held-out generalization, production readiness, model-quality improvement, checkpoint release, adapter release, public full-corpus release, or live-browser benchmark improvement

### Requirement: Publish compact search query rerun evidence without metric reinterpretation
The system SHALL publish a public-safe evidence pack for the A100 search query slot-policy rerun that reports strict metrics and row-level slot/exact-match outcomes without reinterpreting prior predictions.

#### Scenario: Generate rerun evidence pack
- **WHEN** the A100 prediction-only rerun completes
- **THEN** the evidence pack MUST include predictions, gold train rows, prediction metadata, prompt snapshot, raw decoded summary, generation trace, metrics, schema guard summary, slot-policy rerun diagnosis, manifest, report, leak scans, and Human Brief links
- **AND** it MUST compare against the prior retry-template A100 rerun, the prior slot mismatch diagnosis, and the local search query slot target policy evidence
- **AND** it MUST record compact `slots.query` target checks, `city/date` slot counts, exact-match counts, slot mismatch counts, and normalized-command mismatch counts for the three train rows

#### Scenario: Bound claims
- **WHEN** reports, manifests, Human Briefs, or archived OpenSpec artifacts describe the rerun
- **THEN** they MUST state that this is train-split-only prediction evidence
- **AND** they MUST NOT claim held-out generalization, model-quality improvement, production readiness, checkpoint release, adapter release, public full-corpus release, live-browser benchmark improvement, slot normalization, semantic-equivalence scoring, prediction repair, prediction replacement, metric relaxation, or re-score

### Requirement: Publish search-query slot wrapper-boundary diagnosis
The system SHALL publish public-safe local evidence that separates observed generation facts, Markdown wrapper symptoms, and wrapper-boundary evidence gaps after the A100 search-query slot-policy rerun.

#### Scenario: Record observed wrapper facts
- **WHEN** the diagnosis is generated from the latest public-safe search-query slot evidence
- **THEN** it MUST record compact `slots.query` fragments, Markdown-wrapped prediction counts, raw and retry parse status, strict final JSON validity, strict final exact match, and row-level observations without changing predictions or metrics

#### Scenario: Record evidence gaps
- **WHEN** the diagnosis relies on public-safe sidecars and reports only
- **THEN** it MUST state that the wrapper origin is not proven and MUST NOT infer model recovery, output postprocessing success, or parser acceptance from compact fragments alone

#### Scenario: Bound diagnosis claims
- **WHEN** reports, manifests, tests, or Human Briefs describe this phase
- **THEN** they MUST state that no A100 execution, training, decoding change, parser relaxation, slot normalization, metric relaxation, prediction repair, prediction re-score, semantic-equivalence scoring, model-quality claim, held-out generalization claim, or live-browser benchmark improvement claim is made

### Requirement: Publish first-pass output-boundary hardening evidence
The system SHALL publish public-safe local evidence for first-pass prediction output-boundary hardening while preserving strict-metric, privacy, and non-claim boundaries.

#### Scenario: Generate local output-boundary evidence pack
- **WHEN** the local output-boundary behavior-change phase completes
- **THEN** the evidence pack MUST include a manifest, machine-readable summary, human-readable summary, leak-scan results, source links to the prior A100 search-query slot rerun and wrapper-boundary diagnosis, first-pass prompt-boundary visibility metadata, focused test evidence, validation commands, and explicit non-claims

#### Scenario: Bound interpretation of local behavior change
- **WHEN** public documentation or Human Briefs describe the output-boundary behavior-change phase
- **THEN** they MUST state that the phase performs no A100 execution, training, checkpoint release, adapter release, parser relaxation, evaluator metric change, semantic-equivalence scoring, slot normalization, prediction repair, prediction re-score, held-out generalization claim, model recovery claim, model-quality claim, public full-corpus release, or live-browser benchmark improvement claim

#### Scenario: Preserve prior A100 evidence interpretation
- **WHEN** the evidence pack references the prior A100 search-query slot rerun or wrapper-boundary diagnosis
- **THEN** it MUST state that the prior strict schema-valid output remained `0/3`, strict contract exact match remained `0/3`, Markdown-wrapped predictions remained `3/3`, and this local phase does not prove any change in trained-adapter output behavior until a later real A100 rerun is performed

### Requirement: Publish first-pass output-boundary A100 rerun evidence
The system SHALL publish public-safe evidence for the first-pass output-boundary A100 prediction-only rerun while preserving strict parser, metric, privacy, and non-claim boundaries.

#### Scenario: Generate rerun evidence pack
- **WHEN** the A100 prediction-only rerun completes
- **THEN** the evidence pack MUST include predictions, gold train rows, prediction metadata, prompt snapshot, raw decoded summary, generation trace, metrics, schema guard summary, output-boundary comparison diagnosis, manifest, report, leak scans, and Human Brief links
- **AND** it MUST compare against the prior A100 search-query slot-policy rerun and the local output-boundary instrumentation evidence
- **AND** it MUST record strict schema-valid counts, strict exact-match counts, Markdown wrapper counts, compact query fragment counts, raw/retry parse status, and `prediction_output_boundary` visibility

#### Scenario: Bound rerun claims
- **WHEN** reports, manifests, Human Briefs, or archived OpenSpec artifacts describe the rerun
- **THEN** they MUST state that this is train-split-only prediction evidence
- **AND** they MUST NOT claim held-out generalization, model-quality improvement, production readiness, checkpoint release, adapter release, public full-corpus release, live-browser benchmark improvement, slot normalization, semantic-equivalence scoring, prediction repair, prediction replacement, metric relaxation, or re-score

### Requirement: Publish first-pass wrapper persistence diagnosis
The system SHALL publish a public-safe local diagnosis explaining persistent Markdown-wrapped output after first-pass output-boundary visibility is confirmed, while preserving strict parser, privacy, and non-claim boundaries.

#### Scenario: Generate wrapper persistence diagnosis
- **WHEN** the diagnosis is generated from the A100 first-pass output-boundary rerun artifacts
- **THEN** it MUST record prompt boundary visibility, strict schema-valid counts, Markdown wrapper counts, raw and retry parse status counts, finish-state counts, and comparison against the source rerun summary
- **AND** it MUST state that EOS-observed generation completion does not imply strict schema-valid output
- **AND** it MUST NOT alter predictions, repair embedded JSON, relax parser behavior, re-score predictions, or launch a new A100 job

#### Scenario: Bound wrapper persistence claims
- **WHEN** reports, manifests, Human Briefs, or archived OpenSpec artifacts describe the diagnosis
- **THEN** they MUST state that it is local evidence over a three-row train-split A100 rerun
- **AND** they MUST NOT claim held-out generalization, model-quality improvement, model recovery, production readiness, checkpoint release, adapter release, public full-corpus release, live-browser benchmark improvement, semantic-equivalence scoring, slot normalization, prediction repair, metric relaxation, or re-score

#### Scenario: Preserve public-safety boundary
- **WHEN** wrapper persistence diagnosis artifacts are committed
- **THEN** they MUST include leak-scan evidence
- **AND** they MUST NOT include private config paths, raw remote logs, private filesystem paths, host details, SSH details, tokens, secrets, caches, checkpoints, adapters, or private corpus rows

### Requirement: Publish first-pass fence-suppression evidence
The system SHALL publish public-safe local evidence for first-pass Markdown fence suppression while preserving strict-metric, privacy, and non-claim boundaries.

#### Scenario: Generate local fence-suppression evidence pack
- **WHEN** the local fence-suppression behavior-change phase completes
- **THEN** the evidence pack MUST include a manifest, machine-readable summary, human-readable summary, leak-scan results, source links to the prior A100 first-pass output-boundary rerun and wrapper-persistence diagnosis, focused test evidence, validation commands, and explicit non-claims

#### Scenario: Bound interpretation of local suppression evidence
- **WHEN** public documentation or Human Briefs describe the fence-suppression phase
- **THEN** they MUST state that the phase performs no A100 execution, training, checkpoint release, adapter release, parser relaxation, evaluator metric change, semantic-equivalence scoring, slot normalization, prediction repair, prediction re-score, held-out generalization claim, model recovery claim, model-quality claim, public full-corpus release, or live-browser benchmark improvement claim

#### Scenario: Preserve prior A100 evidence interpretation
- **WHEN** the evidence pack references the prior A100 first-pass output-boundary rerun or wrapper-persistence diagnosis
- **THEN** it MUST state that prior strict schema-valid output remained `0/3`, strict exact match remained `0.0`, Markdown-wrapped predictions remained `3/3`, and this local phase does not prove any change in trained-adapter output behavior until a later real A100 rerun is performed

### Requirement: Publish A100 first-pass fence-suppression rerun evidence
The system SHALL publish public-safe evidence for the A100 first-pass fence-suppression rerun with strict metric boundaries and explicit non-claims.

#### Scenario: Generate rerun evidence pack
- **WHEN** sanitized A100 prediction artifacts are available
- **THEN** the evidence pack MUST include predictions, prediction metadata, prompt snapshot, raw decoded summary, generation trace, metrics, schema guard summary, rerun diagnosis, manifest, human-readable report, leak scans, and a Human Brief

#### Scenario: Compare wrapper and strict metrics narrowly
- **WHEN** the rerun evidence is summarized
- **THEN** it MUST report prediction count, train row ids, Markdown-wrapped prediction count, raw and retry schema-valid counts, validated output schema-valid count, validated output source counts, strict JSON valid rate, strict exact match, stop-boundary trace fields, and comparison to prior first-pass output-boundary rerun evidence

#### Scenario: Bound rerun interpretation
- **WHEN** public reports or Human Briefs describe the rerun
- **THEN** they MUST state that this is train-internal prediction-only evidence and MUST NOT claim training, checkpoint release, adapter release, parser relaxation, evaluator metric change, prediction repair, prediction re-score, semantic-equivalence scoring, slot normalization, held-out generalization, production readiness, public full-corpus release, model-quality improvement, model recovery, or live-browser benchmark improvement

#### Scenario: Diagnose residual slot exact-match mismatch
- **WHEN** the fence-suppression rerun has strict schema-valid train-row predictions but strict exact match remains below `1.0`
- **THEN** a local diagnosis MAY derive row-level residual mismatch evidence from the sanitized rerun artifacts
- **AND** it MUST identify residual row ids, gold slots, predicted slots, strict mismatch category, strict metric impact, source rerun artifacts, and remaining non-claim boundaries
- **AND** it MUST NOT run A100, train, rerun prediction, change parser or evaluator behavior, normalize slots, apply semantic-equivalence scoring, repair predictions, re-score outputs, or claim held-out generalization, production readiness, model recovery, broad model-quality improvement, or live-browser benchmark improvement

### Requirement: Publish compact query slot preservation repair evidence
The system SHALL publish public-safe local evidence for compact query slot preservation reinforcement without reinterpreting historical A100 predictions.

#### Scenario: Generate compact query preservation evidence pack
- **WHEN** the local compact-query preservation repair phase completes
- **THEN** the evidence pack MUST include prompt constraint metadata, public sample SFT target checks, public DPO decomposed-slot rejected pair checks, source residual diagnosis links, validation commands, leak-scan results, and explicit non-claims
- **AND** it MUST record that no A100 execution, training, prediction rerun, evaluator change, parser change, semantic-equivalence scoring, slot normalization, prediction repair, prediction replacement, or re-score was performed

#### Scenario: Bound compact query preservation interpretation
- **WHEN** evidence, Human Briefs, loop reports, or archived OpenSpec artifacts describe the repair
- **THEN** they MUST state that prior A100 predictions remain historical evidence and are not repaired, normalized, re-scored, or reinterpreted as exact-match recovery
- **AND** they MUST NOT claim held-out generalization, production readiness, model-quality improvement, model recovery, checkpoint release, adapter release, public full-corpus release, or live-browser benchmark improvement

### Requirement: Publish compact query slot preservation A100 rerun evidence
The system SHALL publish public-safe train-split evidence for the compact query slot preservation A100 rerun that compares strict slot-shape outcomes against the previous `city/date/topic` residual without changing evaluator semantics.

#### Scenario: Generate compact query rerun evidence pack
- **WHEN** sanitized A100 rerun predictions, sidecars, metrics, and leak scans are available
- **THEN** the evidence pack MUST include prediction count, `prediction_source_kind=private_a100_adapter`, `prediction_split=train`, `overfit_diagnostic=true`, `generalization_claim=false`, strict metrics, row-level slot-shape outcomes, prompt/policy visibility, schema guard summary, source residual links, validation commands, and leak-scan results
- **AND** it MUST record whether `seed-search-weather-aug-1` uses compact `slots.query` or remains a decomposed `city/date/topic` strict mismatch
- **AND** it MUST avoid private paths, host details, SSH details, raw logs, checkpoints, adapters, caches, tokens, secrets, and private corpus rows

#### Scenario: Bound compact query rerun interpretation
- **WHEN** reports, Human Briefs, loop reports, or archived OpenSpec artifacts describe the rerun
- **THEN** they MUST state that this is A100 prediction-only train-split diagnostic evidence
- **AND** they MUST NOT claim held-out generalization, production readiness, model-quality improvement, model recovery, checkpoint release, adapter release, public full-corpus release, live-browser benchmark improvement, evaluator relaxation, parser relaxation, slot normalization, semantic-equivalence scoring, prediction repair, prediction replacement, or re-score

#### Scenario: Preserve strict comparison to prior residual
- **WHEN** the rerun evidence compares against prior compact-query residual evidence
- **THEN** it MUST preserve prior A100 predictions and metrics as historical evidence and MUST NOT repair, normalize, re-score, or reinterpret prior `city/date/topic` outputs as exact-match recovery

### Requirement: Publish compact-query exact-match residual diagnosis
The system SHALL publish public-safe local evidence that explains strict exact-match residuals after the compact-query slot-preservation A100 rerun without changing source predictions or evaluator semantics.

#### Scenario: Generate compact-query exact-match residual evidence pack
- **WHEN** the latest compact-query slot-preservation A100 rerun has sanitized predictions, gold targets, metrics, schema guard summary, and manifest artifacts available
- **THEN** the evidence pack MUST include a manifest, machine-readable residual diagnosis, human-readable summary, leak-scan results, source artifact links, inherited strict metrics, row-level residual classifications, validation commands, and explicit non-claims
- **AND** it MUST identify compact-query slot-shape residuals separately from strict `normalized_command` exact-string residuals
- **AND** it MUST record whether `seed-search-weather-aug-1` still predicts decomposed `city/date/topic` slots instead of compact `slots.query`

#### Scenario: Preserve strict source metrics and predictions
- **WHEN** the diagnosis summarizes exact-match residuals
- **THEN** it MUST preserve the source rerun strict metrics and predictions as historical evidence
- **AND** it MUST NOT repair, normalize, replace, re-score, or reinterpret source outputs as exact-match recovery

#### Scenario: Bound compact-query residual diagnosis claims
- **WHEN** reports, Human Briefs, loop reports, or archived OpenSpec artifacts describe the diagnosis
- **THEN** they MUST state that the phase performs no A100 execution, training, prediction rerun, prompt change, decoding change, parser relaxation, evaluator metric change, semantic-equivalence scoring, slot normalization, prediction repair, prediction replacement, or prediction re-score
- **AND** they MUST NOT claim held-out generalization, production readiness, model-quality improvement, model recovery, checkpoint release, adapter release, public full-corpus release, or live-browser benchmark improvement

### Requirement: Publish compact-query exact-match policy hardening evidence
The system SHALL publish public-safe local evidence for compact-query exact-match prompt policy hardening without reinterpreting prior A100 predictions or strict evaluator metrics.

#### Scenario: Generate compact-query exact-match policy hardening evidence pack
- **WHEN** the local prompt policy hardening phase completes
- **THEN** the evidence pack MUST include a manifest, machine-readable policy summary, human-readable report, leak-scan results, source residual-diagnosis links, prompt constraint metadata, public sample target checks, validation commands, and explicit non-claims
- **AND** it MUST record whether compact-query exact-match policy visibility, same-query-phrase alignment visibility, extra-particle avoidance visibility, and decomposed-slot rejection visibility are present
- **AND** it MUST link the prior compact-query exact-match residual diagnosis as historical source evidence without modifying that source evidence

#### Scenario: Preserve prior strict evidence
- **WHEN** the hardening evidence summarizes prior residuals
- **THEN** it MUST preserve prior source predictions, metrics, residual row ids, and field-family counts as historical evidence
- **AND** it MUST NOT repair, normalize, replace, re-score, or reinterpret prior outputs as exact-match recovery

#### Scenario: Bound compact-query hardening evidence claims
- **WHEN** reports, Human Briefs, loop reports, or archived OpenSpec artifacts describe the hardening phase
- **THEN** they MUST state that the phase performs no A100 execution, training, prediction rerun, parser relaxation, strict evaluator metric replacement or relaxation, semantic-equivalence scoring, slot normalization, `normalized_command` normalization, prediction repair, prediction replacement, or prediction re-score
- **AND** they MUST NOT claim held-out generalization, production readiness, model-quality improvement, model recovery, checkpoint release, adapter release, public full-corpus release, or live-browser benchmark improvement

### Requirement: Keep soft slot diagnostics separate from strict metrics
The system SHALL expose soft slot diagnostics only as internal analysis and SHALL keep strict contract metrics authoritative.

#### Scenario: Report slot_f1_soft as internal-only diagnostic
- **WHEN** the evaluator reports `slot_f1_soft`
- **THEN** it MUST continue to report strict `slot_f1` and `contract_exact_match`
- **AND** reports MUST label `slot_f1_soft` as an internal diagnostic rather than strict recovery, production readiness, semantic-equivalence scoring, prediction repair, or prediction re-score

### Requirement: Publish extract-price residual repair evidence
The system SHALL publish public-safe evidence for the extract-price contract residual repair phase that separates strict train-split recovery from held-out or production claims.

#### Scenario: Generate extract residual evidence pack
- **WHEN** extract-price residual rerun predictions, metrics, prompt snapshot, prediction metadata, raw decoded summary, generation trace, residual diagnosis, and leak-scan results are available
- **THEN** the manifest and report MUST link those sanitized artifacts and record `prediction_split=train`, `overfit_diagnostic=true`, `generalization_claim=false`, prediction source kind, release status, extract-price strict exact-match status, compact-query preservation status, and claim boundaries

#### Scenario: Report extract residual families
- **WHEN** the extract residual report is generated from real private-adapter train-split predictions
- **THEN** it MUST state whether extract-price rows failed by task type, route, slots, normalized command, safety, confirmation, schema validity, or exact-match mismatch
- **AND** it MUST compare those residuals with the prior compact-query rerun without treating before/after differences as held-out generalization

#### Scenario: Keep evidence public-safe
- **WHEN** extract residual evidence is prepared for commit
- **THEN** leak-scan validation MUST reject raw private rows, local or remote private paths, secrets, private IP addresses, SSH details, raw logs, checkpoints, adapters, caches, oversized generated corpora, and private remote paths

#### Scenario: Bound extract repair interpretation
- **WHEN** public documentation or Human Briefs describe the extract residual repair result
- **THEN** they MUST state that train-split public-sample evidence does not prove dev/test generalization, production readiness, checkpoint release, adapter release, public full-corpus release, or live-browser benchmark improvement

### Requirement: Publish extract-price canonical wording rerun evidence
The system SHALL publish public-safe evidence for the extract-price canonical wording rerun that separates strict train-split recovery from held-out or production claims.

#### Scenario: Generate canonical wording evidence pack
- **WHEN** canonical wording rerun predictions, metrics, prompt snapshot, prediction metadata, raw decoded summary, generation trace, residual diagnosis, manifest, report, Human Brief, and leak-scan results are available
- **THEN** the manifest and report MUST link those sanitized artifacts and record `prediction_split=train`, `overfit_diagnostic=true`, `generalization_claim=false`, prediction source kind, release status, canonical target exact status, canonical normalized-command exact status, compact-query preservation status, and claim boundaries

#### Scenario: Report canonical wording residual families
- **WHEN** the canonical wording report is generated from real private-adapter train-split predictions
- **THEN** it MUST state whether extract-price rows failed by `slots.target`, `normalized_command`, task type, route, safety, confirmation, schema validity, or exact-match mismatch
- **AND** it MUST compare those residuals with the prior extract-price residual rerun without treating before/after differences as held-out generalization

#### Scenario: Keep canonical wording evidence public-safe
- **WHEN** canonical wording evidence is prepared for commit
- **THEN** leak-scan validation MUST reject raw private rows, local or remote private paths, secrets, private IP addresses, SSH details, raw logs, checkpoints, adapters, caches, oversized generated corpora, and private remote paths

#### Scenario: Bound canonical wording interpretation
- **WHEN** public documentation or Human Briefs describe the canonical wording result
- **THEN** they MUST state that train-split public-sample evidence does not prove dev/test generalization, production readiness, checkpoint release, adapter release, public full-corpus release, or live-browser benchmark improvement

### Requirement: Publish public held-out contract generalization evidence
The system SHALL publish public-safe A100 held-out diagnostic evidence that reports public `dev` and `test` contract metrics separately and bounds interpretation.

#### Scenario: Generate split-specific held-out metrics
- **WHEN** sanitized public held-out predictions are available for `dev` and `test`
- **THEN** the evidence pack MUST include split-specific predictions, gold rows, strict metrics, schema diagnostics, alignment diagnostics, constrained decoding diagnostics, prompt snapshots, raw decoded summaries, generation traces, and prediction metadata

#### Scenario: Generate combined held-out manifest and report
- **WHEN** split-specific evidence has been generated
- **THEN** the combined manifest and report MUST record each split's prediction count, `contract_exact_match`, `slot_f1`, schema-valid count, residual rows, artifact links, and a bounded overall interpretation

#### Scenario: Bound held-out interpretation
- **WHEN** public documentation or Human Briefs describe the held-out result
- **THEN** they MUST state that public `dev`/`test` evidence does not prove private-corpus generalization, checkpoint release, adapter release, production readiness, or live-browser benchmark improvement

#### Scenario: Validate held-out evidence boundaries
- **WHEN** held-out diagnostic evidence is prepared for commit
- **THEN** leak-scan validation MUST reject raw private rows, local or remote private paths, secrets, private IP addresses, SSH details, raw logs, checkpoints, adapters, caches, oversized generated corpora, and private remote paths

### Requirement: Publish public held-out residual repair evidence
The system SHALL publish public-safe evidence for the held-out residual repair rerun that reports train, dev, and test metrics separately and bounds interpretation.

#### Scenario: Generate repair evidence pack
- **WHEN** sanitized repair rerun predictions and sidecars are available for train, dev, and test
- **THEN** the evidence pack MUST include split-specific predictions, gold rows, strict metrics, schema diagnostics, alignment diagnostics, constrained decoding diagnostics, prompt snapshots, raw decoded summaries, generation traces, and prediction metadata

#### Scenario: Report repair interpretation
- **WHEN** the combined repair manifest and report are generated
- **THEN** they MUST record row counts, `contract_exact_match`, `slot_f1`, schema validity, residual rows, prompt-policy visibility, and artifact links per split
- **AND** they MUST identify whether public held-out strict contract behavior recovered, remained partial, or failed

#### Scenario: Bound repair claims
- **WHEN** public documentation or Human Briefs describe the repair result
- **THEN** they MUST state that public-sample train/dev/test evidence does not prove private-corpus generalization, checkpoint release, adapter release, production readiness, public full-corpus release, or live-browser benchmark improvement

#### Scenario: Validate repair evidence boundaries
- **WHEN** repair evidence is prepared for commit
- **THEN** leak-scan validation MUST reject raw private rows, local or remote private paths, secrets, private IP addresses, SSH details, raw logs, checkpoints, adapters, caches, oversized generated corpora, and private remote paths

### Requirement: Publish SFT contract learning-signal evidence
The system SHALL publish a public-safe evidence pack for SFT contract learning-signal diagnostics that links local inspection results to prior repair evidence and claim boundaries.

#### Scenario: Generate learning-signal evidence pack
- **WHEN** the diagnostic completes in local mode
- **THEN** it MUST write machine-readable JSON and human-readable Markdown that include evidence kind, source manifest, inspected row counts, split/task summaries, target-span status, target-pressure summaries, prior repair metrics, evidence gaps, claims, and recommended next step

#### Scenario: Keep learning-signal evidence public-safe
- **WHEN** learning-signal evidence is prepared for commit
- **THEN** leak-scan validation MUST reject raw private rows, local or remote private paths, secrets, private IP addresses, SSH details, raw logs, checkpoints, adapters, caches, oversized generated corpora, and private remote paths

#### Scenario: Bound learning-signal interpretation
- **WHEN** public reports or Human Briefs describe the learning-signal diagnostic
- **THEN** they MUST state that the evidence does not prove model recovery, held-out generalization, private-corpus generalization, checkpoint release, adapter release, production readiness, public full-corpus release, or live-browser benchmark improvement

### Requirement: Publish runtime-label and tiny-overfit diagnostic evidence
The system SHALL publish a public-safe evidence pack that explains whether current public-sample SFT failures are ready for fresh runtime-label inspection, tiny-overfit probing, preference-signal diagnosis, or another bounded follow-up.

#### Scenario: Generate runtime-label tiny-overfit evidence pack
- **WHEN** the diagnostic is run against the current public manifest and prior public-safe artifacts
- **THEN** it MUST write machine-readable JSON and human-readable Markdown that include evidence kind, current manifest ID, current learning-signal status, prior repair metrics, runtime-label freshness, tiny-overfit freshness, recommendation, claims, and artifact policy

#### Scenario: Keep diagnostic evidence public-safe
- **WHEN** runtime-label/tiny-overfit diagnostic evidence is prepared for commit
- **THEN** leak-scan validation MUST reject raw private rows, local or remote private paths, secrets, private IP addresses, SSH details, host details, raw logs, checkpoints, adapters, caches, oversized generated corpora, and private remote paths

#### Scenario: Bound diagnostic interpretation
- **WHEN** public reports or Human Briefs describe the runtime-label/tiny-overfit diagnostic
- **THEN** they MUST state that the evidence does not prove model recovery, held-out generalization, private-corpus generalization, checkpoint release, adapter release, production readiness, public full-corpus release, or live-browser benchmark improvement

#### Scenario: Preserve stale evidence boundaries
- **WHEN** prior runtime-label or tiny-overfit artifacts are stale for the current manifest
- **THEN** the evidence pack MUST identify the source manifest mismatch
- **AND** it MUST recommend a fresh current-manifest check rather than treating stale artifacts as current proof

### Requirement: Publish fresh current-manifest runtime label evidence
The system SHALL publish a public-safe runtime label provenance evidence pack for the current public manifest that clearly distinguishes fresh current-manifest evidence from stale prior artifacts.

#### Scenario: Generate current-manifest runtime label evidence
- **WHEN** runtime label provenance metadata is generated for the current public manifest
- **THEN** the evidence pack MUST report the current manifest ID, runtime check status, real label tensor availability, label source kind, tokenizer/template status, collator status, prompt mask status, assistant-target loss status, evidence gaps, leak-scan status, package/runtime policy, and prior artifact links

#### Scenario: Reject stale evidence as current proof
- **WHEN** prior runtime-label or tiny-overfit evidence references a different manifest ID than the current public manifest
- **THEN** the evidence pack MUST treat that prior evidence as historical context only and MUST NOT present it as current label-mask proof

#### Scenario: Bound current-manifest label interpretation
- **WHEN** public reports, Human Briefs, or loop reports describe current-manifest runtime label evidence
- **THEN** they MUST state whether real tokenizer/collator labels were inspected, whether prompt/system/user tokens were masked, and whether assistant contract tokens carried loss, and MUST NOT claim model recovery, held-out generalization, checkpoint release, adapter release, production readiness, public full-corpus release, or live-browser benchmark improvement

#### Scenario: Keep current-manifest runtime evidence public-safe
- **WHEN** current-manifest runtime label evidence is prepared for commit
- **THEN** leak-scan validation MUST reject raw rendered prompts, raw assistant targets, private rows, local or remote private paths, secrets, private IP addresses, SSH details, raw logs, checkpoints, adapters, caches, model snapshots, oversized generated corpora, and private remote paths

### Requirement: Publish current-manifest tiny-overfit probe evidence
The system SHALL publish a public-safe evidence pack for the current-manifest tiny-overfit probe that separates train-internal memorization from held-out generalization and release claims.

#### Scenario: Import sanitized tiny-overfit evidence
- **WHEN** tiny-overfit training metadata, train-split predictions, metrics, prompt snapshot, sanitized raw decoded summary, generation trace, runtime-label reference, and leak-scan results are available
- **THEN** the manifest and report MUST link those sanitized artifacts, record `prediction_split=train`, `overfit_diagnostic=true`, `generalization_claim=false`, `base_model=Qwen/Qwen2.5-7B-Instruct`, `dataset_manifest_id=public-sample-20260613T072200Z`, selected train row IDs, prediction count, release status, and non-claim boundaries without private runtime details

#### Scenario: Report observed train-internal recovery
- **WHEN** the probe report is generated from real private-adapter train-split predictions
- **THEN** it MUST state whether schema validity, task type, route, slot, safety, confirmation, and strict contract exact match recovered, remained partial, or failed using observed metrics and failure slices

#### Scenario: Keep tiny-overfit evidence public-safe
- **WHEN** tiny-overfit evidence is prepared for commit
- **THEN** leak-scan validation MUST reject raw private rows, local or remote private paths, secrets, private IP addresses, SSH details, raw logs, checkpoints, adapters, caches, oversized generated corpora, model snapshots, and private remote paths
#### Scenario: Bound tiny-overfit interpretation
- **WHEN** public documentation or Human Briefs describe the probe result
- **THEN** they MUST state that train-internal tiny-overfit evidence does not prove dev/test generalization, private-corpus generalization, production readiness, checkpoint release, adapter release, public full-corpus release, or live-browser benchmark improvement

### Requirement: Publish current tiny-adapter held-out prediction evidence
The system SHALL publish public-safe evidence for the current-manifest tiny
adapter's held-out prediction-only diagnostic, reporting `dev` and `test`
contract metrics separately and comparing them with the prior train-internal
tiny-overfit result without broad recovery claims.

#### Scenario: Generate split-specific current tiny held-out metrics
- **WHEN** sanitized current tiny-adapter predictions are available for `dev` and `test`
- **THEN** the evidence pack MUST include split-specific predictions, gold rows, strict metrics, schema diagnostics, alignment diagnostics, constrained decoding diagnostics, prompt snapshots, raw decoded summaries, generation traces, and prediction metadata

#### Scenario: Generate combined current tiny held-out manifest and report
- **WHEN** split-specific evidence has been generated
- **THEN** the combined manifest and report MUST record dataset manifest ID, base model, adapter source kind, prior train-internal exact match, each split's prediction count, `contract_exact_match`, `slot_f1`, schema-valid count, residual rows, artifact links, and bounded overall interpretation

#### Scenario: Bound current tiny held-out interpretation
- **WHEN** public documentation or Human Briefs describe the current tiny held-out result
- **THEN** they MUST state that this is prediction-only public-sample held-out diagnosis
- **AND** they MUST NOT claim new training, DPO, checkpoint release, adapter release, model recovery, private-corpus generalization, production readiness, public full-corpus release, or live-browser benchmark improvement

#### Scenario: Validate current tiny held-out evidence boundaries
- **WHEN** current tiny held-out diagnostic evidence is prepared for commit
- **THEN** leak-scan validation MUST reject raw private rows, local or remote private paths, secrets, private IP addresses, SSH details, raw logs, checkpoints, adapters, caches, oversized generated corpora, model snapshots, and private remote paths

### Requirement: Publish held-out family strategy diagnosis
The system SHALL publish a public-safe local diagnosis that explains current
tiny-adapter held-out failures by task family, contract field, and training
subset coverage before another data, SFT, or DPO strategy is executed.

#### Scenario: Generate family-level strategy evidence
- **WHEN** current tiny-adapter held-out evidence and current public-sample rows are available
- **THEN** the diagnostic MUST report family-level train/dev/test coverage, tiny-adapter training subset coverage, held-out exact-match status, schema-invalid counts, field mismatch counts, and source-family residuals
- **AND** it MUST distinguish dataset-level train coverage from tiny-adapter subset coverage

#### Scenario: Recommend without executing strategy
- **WHEN** the diagnostic recommends a next strategy
- **THEN** the recommendation MUST identify whether the next bounded phase should investigate targeted SFT coverage, DPO hard negatives, prompt/policy adjustment, or local learning-signal evidence
- **AND** it MUST NOT generate new rows, train, run A100 prediction, change evaluator metrics, modify prompts, or execute DPO

#### Scenario: Bound strategy interpretation
- **WHEN** public documentation or Human Briefs describe the diagnosis
- **THEN** they MUST state that the diagnosis does not prove held-out generalization, model recovery, private-corpus generalization, checkpoint release, adapter release, production readiness, public full-corpus release, or live-browser benchmark improvement

#### Scenario: Validate strategy evidence boundaries
- **WHEN** held-out family strategy evidence is prepared for commit
- **THEN** leak-scan validation MUST reject raw private rows, local or remote private paths, secrets, private IP addresses, SSH details, raw logs, checkpoints, adapters, caches, oversized generated corpora, model snapshots, and private remote paths

### Requirement: Publish targeted family coverage probe evidence
The system SHALL publish a public-safe evidence pack for the targeted family coverage probe that separates train learnability from held-out generalization and release claims.

#### Scenario: Generate targeted probe manifest
- **WHEN** targeted family coverage train/dev/test predictions and diagnostics are available
- **THEN** the manifest MUST record selected train source IDs, selected train row IDs, split metrics, primary held-out splits, comparison artifacts, evidence status, and non-claim boundaries
- **AND** it MUST identify whether dev/test strict exact improved from the current tiny-adapter held-out baseline

#### Scenario: Compare targeted probe with prior evidence
- **WHEN** the report interprets targeted probe results
- **THEN** it MUST compare against the current tiny-adapter held-out prediction evidence and the earlier broad public held-out residual repair evidence
- **AND** it MUST state whether the targeted source-family selection produced train memorization, held-out exact-match movement, both, or neither

#### Scenario: Bound targeted probe interpretation
- **WHEN** public documentation or Human Briefs describe targeted family coverage evidence
- **THEN** they MUST state that the evidence does not prove checkpoint release, adapter release, private-corpus generalization, production readiness, public full-corpus release, or live-browser benchmark improvement
- **AND** they MUST NOT promote soft slot F1 or semantic equivalence to the primary metric

#### Scenario: Validate targeted probe public safety
- **WHEN** targeted family coverage evidence is prepared for commit
- **THEN** leak-scan validation MUST reject raw private rows, local or remote private paths, secrets, private IP addresses, SSH details, raw logs, checkpoints, adapters, caches, model snapshots, oversized generated corpora, and private remote paths

### Requirement: Publish targeted slot value residual diagnosis
The system SHALL publish a public-safe diagnosis for the remaining targeted family coverage held-out residuals without changing predictions, metrics, or evaluator semantics.

#### Scenario: Classify remaining value residuals
- **WHEN** targeted family coverage dev/test gold rows, predictions, alignment diagnostics, and manifest evidence are available
- **THEN** the diagnosis MUST classify each remaining mismatching row by split, row id, source family, field path, and value-drift bucket
- **AND** it MUST aggregate residual counts by split, field path, source family, and drift bucket

#### Scenario: Preserve strict evaluation boundaries
- **WHEN** the targeted residual report is generated
- **THEN** it MUST state that strict `contract_exact_match` remains the primary metric
- **AND** it MUST NOT repair predictions, replace predictions, relax evaluator rules, or promote semantic equivalence or soft slot F1 to the primary metric

#### Scenario: Bound next-step recommendation
- **WHEN** the diagnosis recommends a next step
- **THEN** it MUST prefer a bounded slot value generalization/data-design diagnosis before broad scaling, DPO, or production claims
- **AND** it MUST state that the evidence does not prove held-out generalization recovery, private-corpus generalization, adapter release, checkpoint release, production readiness, or live-browser benchmark improvement

#### Scenario: Validate public safety
- **WHEN** targeted residual diagnosis artifacts are prepared for commit
- **THEN** leak-scan validation MUST reject raw private rows, local or remote private paths, secrets, private IP addresses, SSH details, raw logs, checkpoints, adapters, caches, model snapshots, oversized generated corpora, and private remote paths

### Requirement: Report slot value case-design evidence with strict metric boundaries
The system SHALL report slot value generalization case designs as design-only evidence and not as model-quality evidence.

#### Scenario: Bound case-design interpretation
- **WHEN** reports or Human Briefs describe slot value generalization case designs
- **THEN** they MUST state that the design does not prove model recovery, held-out generalization, private-corpus generalization, adapter release, checkpoint release, production readiness, or live-browser benchmark improvement
- **AND** they MUST state that soft slot F1 and semantic equivalence remain diagnostic-only

#### Scenario: Validate public safety
- **WHEN** slot value generalization case-design artifacts are prepared for commit
- **THEN** leak-scan validation MUST reject raw private rows, local or remote private paths, secrets, private IP addresses, SSH details, raw logs, checkpoints, adapters, caches, model snapshots, oversized generated corpora, and private remote paths

### Requirement: Publish slot value candidate probe evidence safely
The system SHALL publish public-safe evidence for slot value candidate SFT probe preparation or execution without leaking private runtime artifacts or overstating model quality.

#### Scenario: Report candidate probe prep evidence
- **WHEN** local dry-run metadata and A100 preflight information are available
- **THEN** the report MUST record candidate row counts, selected row ids, training status, prediction status, dependency status, GPU preflight status, and artifact policy using public-safe values
- **AND** it MUST link the candidate manifest, candidate SFT rows, SFT config, prediction config, and prior materialization evidence

#### Scenario: Preserve public sample boundary
- **WHEN** candidate probe evidence is generated
- **THEN** it MUST state `formal_public_sample_modified=false`
- **AND** it MUST NOT rewrite or replace the formal public sample manifest, SFT JSONL, DPO JSONL, or seed traces

#### Scenario: Bound interpretation
- **WHEN** candidate probe evidence is described in reports or Human Briefs
- **THEN** it MUST state that candidate dry-run or blocked A100 status does not prove model recovery, held-out generalization, checkpoint release, adapter release, production readiness, private-corpus generalization, or live-browser improvement

### Requirement: Publish observed A100 candidate probe evidence safely
The system SHALL publish a public-safe evidence pack for observed or blocked A100 slot value candidate SFT probe execution.

#### Scenario: Report observed candidate SFT status
- **WHEN** A100 candidate SFT execution is attempted
- **THEN** the evidence MUST record sanitized remote preflight, dependency status, selected GPU label, training status, selected candidate row counts, and artifact policy
- **AND** it MUST omit raw logs, adapters, checkpoints, host details, SSH details, private paths, tokens, private overrides, and model caches

#### Scenario: Report candidate train-split prediction status
- **WHEN** train-split candidate prediction is attempted after candidate SFT
- **THEN** the evidence MUST record prediction status, split, row count, metric links when available, and non-claim boundaries using public-safe values
- **AND** if prediction is skipped or blocked, the evidence MUST state the reason without implying model recovery

#### Scenario: Preserve formal public sample boundary
- **WHEN** observed A100 candidate probe evidence is generated
- **THEN** it MUST state `formal_public_sample_modified=false`
- **AND** it MUST NOT rewrite formal public sample seed, SFT, DPO, or manifest files

#### Scenario: Bound observed candidate probe interpretation
- **WHEN** public documentation or Human Briefs describe observed candidate probe evidence
- **THEN** they MUST state that candidate train-split evidence does not prove held-out generalization, private-corpus generalization, checkpoint release, adapter release, production readiness, public full-corpus release, or live-browser benchmark improvement

### Requirement: Publish merged slot value held-out evaluation evidence
The system SHALL publish public-safe evidence for the merged-candidate A100
rerun that separates train learnability from held-out generalization.

#### Scenario: Generate merged-candidate evidence pack
- **WHEN** sanitized merged-candidate train/dev/test predictions, sidecars, and
  metrics are available
- **THEN** the evidence pack MUST record the regenerated manifest ID, formal
  public sample counts, training row counts, split prediction counts,
  `contract_exact_match`, `slot_f1`, schema-valid counts, residual rows, and
  source artifact links

#### Scenario: Compare with prior held-out baseline
- **WHEN** the merged-candidate report is generated
- **THEN** it MUST compare dev/test strict exact against the prior targeted
  family coverage evidence (`1/6` for each split)
- **AND** it MUST identify whether held-out strict exact improved, stayed
  partial, fully recovered on the public sample, or regressed

#### Scenario: Preserve strict metric boundaries
- **WHEN** merged-candidate evidence is described in reports or Human Briefs
- **THEN** strict `contract_exact_match` MUST remain the primary success metric
- **AND** soft slot F1 and semantic equivalence MUST remain diagnostic-only
- **AND** the report MUST NOT repair predictions, replace predictions, relax
  evaluator rules, or re-score prior evidence

#### Scenario: Validate public safety
- **WHEN** merged-candidate evidence is prepared for commit
- **THEN** leak-scan validation MUST reject raw private rows, local or remote
  private paths, secrets, private IP addresses, SSH details, host details, raw
  logs, adapters, checkpoints, caches, model snapshots, oversized generated
  corpora, and private remote paths

### Requirement: Publish merged residual canonical policy evidence
The system SHALL publish public-safe local evidence for merged residual
canonical policy hardening that links back to the merged residual diagnosis
without claiming model recovery.

#### Scenario: Generate local canonical policy evidence
- **WHEN** the merged residual canonical policy evidence pack is generated
- **THEN** it MUST record the source prior phase
  `reports/public-sample/merged-slot-value-residual-diagnosis/`
- **AND** it MUST report residual counts for ambiguous clarify canonical phrase
  drift and unsafe payment canonical command drift
- **AND** it MUST record prompt constraint flags for ambiguous-clarify canonical
  phrase visibility and unsafe-payment canonical command visibility

#### Scenario: Bound local canonical policy evidence claims
- **WHEN** reports, Human Briefs, loop reports, or archived OpenSpec artifacts
  describe this phase
- **THEN** they MUST state that it is local prompt/policy hardening only
- **AND** they MUST NOT claim A100 execution, training, prediction rerun,
  evaluator metric change, semantic-equivalence scoring, slot normalization,
  prediction repair, prediction re-score, checkpoint release, adapter release,
  held-out generalization recovery, production readiness, model-quality
  improvement, or live-browser benchmark improvement

#### Scenario: Keep canonical policy evidence public-safe
- **WHEN** the evidence pack is prepared for commit
- **THEN** leak-scan validation MUST reject raw private rows, local or remote
  private paths, secrets, private IP addresses, SSH details, raw logs,
  checkpoints, adapters, caches, oversized generated corpora, and private
  runtime paths

### Requirement: Publish hardened canonical policy rerun evidence
The system SHALL publish public-safe evidence for the hardened canonical policy
prediction rerun while preserving strict metric semantics and claim boundaries.

#### Scenario: Compare rerun metrics against prior merged evidence
- **WHEN** train/dev/test metrics are available for the hardened-policy rerun
- **THEN** the evidence pack MUST record strict `contract_exact_match`,
  `slot_f1`, `slot_f1_soft`, `json_valid_rate`, and residual row counts by
  split
- **AND** it MUST compare those strict exact metrics with the prior merged
  slot-value held-out evidence

#### Scenario: Keep strict evidence boundaries
- **WHEN** public reports or Human Briefs describe the rerun
- **THEN** they MUST state that dev/test strict `contract_exact_match` remains
  primary
- **AND** they MUST NOT claim private-corpus generalization, checkpoint release,
  adapter release, production readiness, public full-corpus release, or
  live-browser benchmark improvement
- **AND** they MUST NOT treat `json_valid_rate`, train exact match, or soft
  slot F1 as model recovery

#### Scenario: Publish blocked status safely
- **WHEN** SSH, GPU placement, remote dependency, stale-code, or prompt-flag
  checks block the rerun
- **THEN** the evidence pack MUST record a blocked status and reason without
  private host details, private paths, raw logs, checkpoints, adapters, tokens,
  or private corpus rows

### Requirement: Publish merged adapter restore evidence
The system SHALL publish public-safe evidence for the merged slot-value adapter
restore/regeneration prerequisite.

#### Scenario: Record adapter availability evidence
- **WHEN** restore or regeneration evidence is written
- **THEN** it MUST record the restore status, acquisition method, dataset
  manifest ID, source runtime, required adapter-file checks, and sanitized
  dependency/preflight status

#### Scenario: Record blocked prerequisite status
- **WHEN** SSH, GPU placement, dependency, output-root, or training runtime
  checks block adapter restoration/regeneration
- **THEN** the evidence pack MUST record a blocked status and reason without
  private host details, raw private paths, raw logs, adapters, checkpoints,
  tokens, or private corpus rows

#### Scenario: Bound prerequisite interpretation
- **WHEN** public reports or Human Briefs describe the adapter prerequisite
- **THEN** they MUST state that this phase produces no new train/dev/test
  prediction metrics
- **AND** they MUST NOT claim model recovery, adapter release, checkpoint
  release, production readiness, private-corpus generalization, or live-browser
  benchmark improvement

### Requirement: Publish observed hardened canonical policy rerun evidence
The system SHALL publish public-safe observed rerun evidence without overwriting
the earlier blocked evidence directory.

#### Scenario: Preserve blocked evidence traceability
- **WHEN** the restored-adapter observed rerun report is generated
- **THEN** it MUST use a distinct public report directory from the earlier
  blocked rerun evidence
- **AND** diagnostic artifact paths MUST point at the requested observed output
  directory.

#### Scenario: Bound observed rerun claims
- **WHEN** the observed rerun evidence is published
- **THEN** it MAY report public-sample train/dev/test strict contract metrics,
  prompt-policy flags, residual rows, and comparison to prior merged evidence
- **AND** it MUST state that the phase is prediction-only and does not train,
  repair, normalize, or re-score predictions
- **AND** it MUST NOT claim model recovery, private-corpus generalization,
  production readiness, adapter release, checkpoint release, or live-browser
  benchmark improvement.

### Requirement: Keep public project visibility aligned with formal held-out evidence
The system SHALL keep public-facing project summaries aligned with the latest
committed formal public held-out evidence and conservative evaluation claim
boundaries.

#### Scenario: Refresh public summaries after formal held-out evidence
- **WHEN** README files, experiment reports, or Human Briefs describe the current
  Voice2Task model status
- **THEN** they MUST use the latest committed formal public held-out evidence as
  the headline status when such evidence exists
- **AND** they MUST identify strict `contract_exact_match` and strict `slot_f1`
  as primary evidence, with `slot_f1_soft` labeled as an internal diagnostic
  only
- **AND** they MUST NOT claim held-out recovery, model recovery, checkpoint
  release, adapter release, production readiness, private-corpus
  generalization, public full-corpus release, or live-browser benchmark
  improvement unless separate authoritative evidence exists

#### Scenario: Recommend the next bounded phase
- **WHEN** public summaries recommend future Voice2Task work after partial
  held-out evidence
- **THEN** they MUST recommend residual/family diagnosis before new data
  generation, broad retraining, DPO reruns, evaluator changes, or production
  positioning
- **AND** they MUST keep historical private-dev or train-split diagnostics
  separate from current formal public held-out results

### Requirement: Publish formal held-out residual family diagnosis
The system SHALL publish public-safe residual/family diagnosis evidence for the
current formal public held-out prediction artifacts without changing model
outputs or evaluator semantics.

#### Scenario: Diagnose formal held-out residual rows
- **WHEN** formal public held-out dev/test gold rows, predictions, and manifest
  metrics are available
- **THEN** the diagnosis MUST list strict residual rows by split, row id, source
  family id, contract family key, field path, mismatch category, and sanitized
  gold/prediction value summaries
- **AND** it MUST aggregate residuals by split, field path, source family,
  contract family, and category
- **AND** it MUST fail rather than publish if computed residual row counts do
  not match the source manifest residual counts

#### Scenario: Preserve strict metric boundaries
- **WHEN** the diagnosis references `contract_exact_match`, strict `slot_f1`,
  or `slot_f1_soft`
- **THEN** strict `contract_exact_match` and strict `slot_f1` MUST remain the
  primary metrics
- **AND** `slot_f1_soft` MUST be labeled as internal diagnostic-only and MUST
  NOT repair, normalize, re-score, or replace strict predictions

#### Scenario: Recommend a bounded next phase only
- **WHEN** the diagnosis summarizes likely residual clusters
- **THEN** it MAY recommend a next bounded OpenSpec phase
- **AND** it MUST NOT automatically materialize new data, change gold policy,
  launch training, launch DPO, modify evaluator behavior, or claim production
  readiness, model recovery, checkpoint release, adapter release,
  private-corpus generalization, public full-corpus release, or live-browser
  benchmark improvement

### Requirement: Publish formal held-out remediation target selection
The system SHALL publish a public-safe remediation target selection report from
the formal held-out residual-family diagnosis before any new data generation,
training, DPO, prediction rerun, evaluator change, or gold-policy change.

#### Scenario: Rank residual task families
- **WHEN** a committed formal held-out residual-family diagnosis is available
- **THEN** the target selection report MUST rank task families by affected
  strict residual row count and include residual field counts for each family
- **AND** it MUST identify the source diagnosis artifact and preserve source
  residual count consistency

#### Scenario: Select one first remediation target
- **WHEN** task-family rankings are computed
- **THEN** the report MUST select exactly one first remediation target
- **AND** it MUST explain why that target is first, why adjacent high-risk
  families are deferred, and what bounded follow-up OpenSpec phase is
  recommended

#### Scenario: Preserve evidence and metric boundaries
- **WHEN** the report references strict exact match, strict slot F1, or
  `slot_f1_soft`
- **THEN** strict `contract_exact_match` and strict `slot_f1` MUST remain the
  primary metrics
- **AND** `slot_f1_soft` MUST remain diagnostic-only
- **AND** the report MUST NOT claim model recovery, production readiness,
  semantic-equivalence scoring, adapter release, checkpoint release, private
  corpus generalization, public full-corpus release, or live-browser benchmark
  improvement

#### Scenario: Keep artifacts public-safe
- **WHEN** the report is written under `reports/public-sample`
- **THEN** it MUST omit private paths, host details, SSH details, secrets,
  checkpoints, adapters, raw logs, and private corpus rows
- **AND** it MUST use sanitized summaries rather than copying raw prediction
  streams as the planning artifact

### Requirement: Publish form-fill remediation plan diagnosis
The system SHALL publish a public-safe, plan-only diagnosis for the selected
formal held-out `form_fill` residual target before any data generation,
training, DPO, prediction rerun, gold-policy change, or evaluator change.

#### Scenario: Validate source target selection
- **WHEN** the diagnosis is generated from formal held-out remediation target
  selection evidence
- **THEN** it MUST fail rather than publish if the selected target is not
  `form_fill`
- **AND** it MUST preserve the source selection residual row and field counts

#### Scenario: Classify remediation buckets
- **WHEN** `form_fill` residual rows are available
- **THEN** the diagnosis MUST classify residuals into remediation buckets for
  confirmation marker drift, field-name specificity drift, clarify-boundary
  confusion, and any remaining strict drift
- **AND** it MUST include counts by bucket, field path, split, and source family

#### Scenario: Recommend only bounded follow-up
- **WHEN** remediation buckets are summarized
- **THEN** the diagnosis MUST recommend a bounded follow-up phase and acceptance
  boundary
- **AND** it MUST NOT automatically generate data, change prompts, change gold
  labels, launch training, launch DPO, launch A100 prediction, or change
  evaluator behavior

#### Scenario: Preserve public-safe strict metric boundaries
- **WHEN** the diagnosis is written to public-sample reports
- **THEN** it MUST omit private paths, host details, SSH details, secrets,
  checkpoints, adapters, raw logs, and private corpus rows
- **AND** it MUST keep strict `contract_exact_match` and strict `slot_f1` as the
  primary metrics
- **AND** `slot_f1_soft` MUST remain diagnostic-only and MUST NOT be used as a
  semantic-equivalence primary metric

### Requirement: Publish form-fill remediation case design
The system SHALL publish a public-safe, design-only `form_fill` remediation case-design artifact from the existing formal held-out remediation plan before any later materialization, training, DPO, A100, prediction rerun, or evaluator-policy change.

#### Scenario: Validate source plan boundary
- **WHEN** the form-fill remediation case design is generated
- **THEN** the source artifact MUST be `formal_heldout_form_fill_remediation_plan` evidence with `target="form_fill"` and `remediation_status="plan_only_no_data_no_training_no_metric_change"`

#### Scenario: Produce reviewed case groups
- **WHEN** the source plan contains remediation buckets
- **THEN** the case design MUST publish review-ready case groups and prompt/policy guidance for `confirmation_marker_missing_or_reordered`, `field_name_specificity_drift`, and `clarify_boundary_confusion`

#### Scenario: Preserve data and evaluation boundaries
- **WHEN** the case design report or manifest is generated
- **THEN** it MUST state that no seed rows, public-sample splits, held-out gold labels, SFT rows, DPO pairs, predictions, A100 jobs, training runs, or evaluator metrics were created or changed

#### Scenario: Keep claims bounded
- **WHEN** reports, manifests, Human Briefs, or OpenSpec artifacts describe the case-design phase
- **THEN** they MUST keep `contract_exact_match` and strict `slot_f1` as primary metrics, keep `slot_f1_soft` diagnostic-only, and MUST NOT claim model recovery, production readiness, checkpoint release, adapter release, full-corpus release, or live-browser benchmark improvement

#### Scenario: Validate public-safety of artifacts
- **WHEN** the case-design artifacts are prepared for commit
- **THEN** leak-scan validation MUST reject raw private rows, absolute local paths, private remote paths, host details, SSH details, secrets, tokens, raw logs, checkpoints, adapters, caches, and oversized generated corpora

### Requirement: Publish post-form-fill-remediation held-out evidence
The system SHALL publish public-safe prediction-only held-out evidence after the formal public sample includes reviewed `form_fill` remediation candidates.

#### Scenario: Evaluate against the current merged manifest
- **WHEN** sanitized private-adapter predictions are generated for the current formal public sample dev and test splits after the form-fill remediation merge
- **THEN** the system MUST evaluate them with the existing strict contract ladder
- **AND** the evidence MUST record the current public manifest id, formal counts, split counts, prediction split, and prediction artifact set

#### Scenario: Preserve prediction-only and strict-metric boundaries
- **WHEN** post-form-fill-remediation held-out evidence is generated
- **THEN** the evidence MUST state that no SFT training, DPO training, GRPO training, dataset mutation, evaluator relaxation, semantic-equivalence scoring, slot normalization, prediction repair, prediction replacement, or prediction re-score occurred
- **AND** strict `contract_exact_match`, strict `slot_f1`, and the contract evaluation ladder MUST remain authoritative
- **AND** `slot_f1_soft` MUST remain an internal diagnostic only

#### Scenario: Bound evidence interpretation
- **WHEN** reports or Human Briefs describe the post-form-fill-remediation held-out result
- **THEN** they MUST NOT claim held-out recovery, model recovery, checkpoint release, adapter release, production readiness, public full-corpus release, private-corpus generalization, or live-browser benchmark improvement unless a later scoped phase adds separate evidence for that claim

#### Scenario: Record blocked execution safely
- **WHEN** prediction-only execution cannot safely run because the adapter, private override, remote dependency, or idle GPU state is unavailable
- **THEN** the system MUST record a blocked status without writing fabricated predictions or model-quality metrics

#### Scenario: Validate public evidence boundaries
- **WHEN** post-form-fill-remediation held-out artifacts are prepared for commit
- **THEN** leak-scan validation MUST reject raw private rows, absolute local paths, private remote paths, host details, SSH details, secrets, tokens, raw logs, checkpoints, adapters, caches, and oversized generated corpora

### Requirement: Publish formal held-out residual cluster inspection
The system SHALL publish public-safe residual-cluster inspection evidence derived only from committed formal public held-out evidence before recommending data, training, or evaluator changes.

#### Scenario: Inspect current residual clusters
- **WHEN** residual-cluster inspection is generated for the current formal public held-out evidence
- **THEN** the evidence MUST record the source manifest id, strict contract metrics, strict slot metrics, residual row counts, and source residual diagnosis links
- **AND** it MUST group residuals by split, task family, field path, mismatch category, source family, and representative examples

#### Scenario: Preserve analysis-only boundaries
- **WHEN** residual-cluster inspection evidence is generated
- **THEN** the evidence MUST state that no prediction run, SFT training, DPO training, GRPO training, dataset mutation, evaluator relaxation, semantic-equivalence scoring, prediction repair, prediction replacement, or prediction re-score occurred
- **AND** strict `contract_exact_match`, strict `slot_f1`, and the contract evaluation ladder MUST remain authoritative
- **AND** `slot_f1_soft` MUST remain an internal diagnostic only

#### Scenario: Bound recommended next actions
- **WHEN** the residual-cluster inspection recommends follow-up work
- **THEN** recommendations MUST be labeled as candidates derived from observed cluster evidence
- **AND** they MUST NOT mutate data, training, prompts, evaluator semantics, predictions, checkpoints, or adapter release status in the same phase
- **AND** they MUST NOT claim held-out recovery, model recovery, production readiness, private-corpus generalization, public full-corpus release, or live-browser benchmark improvement

#### Scenario: Validate cluster evidence boundaries
- **WHEN** residual-cluster inspection artifacts are prepared for commit
- **THEN** leak-scan validation MUST reject raw private rows, absolute local paths, private remote paths, host details, SSH details, secrets, tokens, raw logs, checkpoints, adapters, caches, and oversized generated corpora

### Requirement: Publish form-fill boundary and field-specificity inspection
The system SHALL publish public-safe form-fill boundary and field-specificity inspection evidence derived only from committed formal held-out residual-cluster evidence before recommending data, prompt, training, or evaluator changes for the top form-fill residual clusters.

#### Scenario: Inspect form-fill residual buckets
- **WHEN** form-fill inspection is generated for the current formal public held-out residual clusters
- **THEN** the evidence MUST record the source manifest id, source residual-cluster report, strict contract metrics, form-fill cluster counts, bucket counts, split counts, source-family counts, and representative examples
- **AND** it MUST separate at least normalized-command residuals from slot residuals
- **AND** it MUST identify diagnostic buckets as candidates rather than root-cause proof

#### Scenario: Preserve analysis-only boundaries
- **WHEN** form-fill inspection evidence is generated
- **THEN** the evidence MUST state that no prediction run, A100 job, SFT training, DPO training, GRPO training, dataset mutation, prompt change, gold policy change, evaluator relaxation, semantic-equivalence scoring, prediction repair, prediction replacement, or prediction re-score occurred
- **AND** strict `contract_exact_match`, strict `slot_f1`, and the contract evaluation ladder MUST remain authoritative
- **AND** `slot_f1_soft` MUST remain an internal diagnostic only

#### Scenario: Bound follow-up recommendations
- **WHEN** the form-fill inspection recommends follow-up work
- **THEN** recommendations MUST be labeled as candidate next actions derived from observed form-fill residual buckets
- **AND** they MUST NOT mutate data, training, prompts, evaluator semantics, predictions, checkpoints, or adapter release status in the same phase
- **AND** they MUST NOT claim held-out recovery, model recovery, production readiness, private-corpus generalization, public full-corpus release, or live-browser benchmark improvement

#### Scenario: Validate form-fill inspection public safety
- **WHEN** form-fill inspection artifacts are prepared for commit
- **THEN** leak-scan validation MUST reject raw private rows, absolute local paths, private remote paths, host details, SSH details, secrets, tokens, raw logs, checkpoints, adapters, caches, and oversized generated corpora

### Requirement: Publish form-fill confirmation and field-specificity policy
The system SHALL publish a public-safe form-fill confirmation and field-specificity policy artifact derived only from committed form-fill boundary inspection evidence before any future data, prompt, training, or evaluator remediation for the observed form-fill residual buckets.

#### Scenario: Define policy from form-fill inspection evidence
- **WHEN** the form-fill policy artifact is generated
- **THEN** the evidence MUST record the source manifest id, source inspection artifact, strict contract metrics, form-fill bucket counts, cluster-row incidence counts, residual-field counts, split counts, field paths, source-family counts, representative examples, and source count consistency
- **AND** it MUST include separate policy sections for confirmation markers, field specificity or alias drift, and route or intent boundary leakage
- **AND** it MUST preserve `cluster_row_incidence_total` terminology without presenting it as unique row count

#### Scenario: Preserve strict metric authority
- **WHEN** the form-fill policy artifact references strict and soft metrics
- **THEN** strict `contract_exact_match`, strict `slot_f1`, and the contract evaluation ladder MUST remain authoritative
- **AND** `slot_f1_soft` MUST remain an internal diagnostic only
- **AND** the artifact MUST NOT repair, normalize, replace, or re-score predictions

#### Scenario: Bound policy execution scope
- **WHEN** the form-fill policy artifact is generated
- **THEN** it MUST state that no prediction run, A100 job, SFT training, DPO training, GRPO training, dataset mutation, candidate generation, prompt change, gold policy mutation, evaluator relaxation, semantic-equivalence scoring, prediction repair, prediction replacement, or prediction re-score occurred
- **AND** it MUST NOT claim held-out recovery, model recovery, checkpoint release, adapter release, production readiness, private-corpus generalization, public full-corpus release, or live-browser benchmark improvement

#### Scenario: Recommend only bounded follow-up actions
- **WHEN** the form-fill policy artifact recommends follow-up work
- **THEN** recommendations MUST be labeled as candidate next actions derived from the observed policy sections
- **AND** recommendations MUST require separate OpenSpec phases before mutating data, prompts, gold policy, evaluator semantics, predictions, checkpoints, adapters, or training runs

#### Scenario: Validate policy artifact public safety
- **WHEN** form-fill policy artifacts are prepared for commit
- **THEN** leak-scan validation MUST reject raw private rows, absolute local paths, private remote paths, host details, SSH details, secrets, tokens, raw logs, checkpoints, adapters, caches, and oversized generated corpora

### Requirement: Publish form-fill confirmation-marker coverage assessment
The system SHALL publish a public-safe coverage assessment that compares the current form-fill confirmation-marker policy evidence with existing form-fill remediation artifacts before any further confirmation-marker data, prompt, training, or evaluator remediation.

#### Scenario: Assess coverage from committed artifacts
- **WHEN** the confirmation-marker coverage assessment is generated
- **THEN** the evidence MUST record the source policy artifact, source case-design artifact, source materialization artifact when available, source merge or integration artifacts when available, source held-out evaluation artifacts when available, source manifest id, confirmation-marker policy counts, existing confirmation candidate counts, represented field labels, and source count consistency
- **AND** it MUST state whether the assessment reads only committed public-safe artifacts

#### Scenario: Preserve assessment-only boundaries
- **WHEN** confirmation-marker coverage evidence is generated
- **THEN** it MUST state that no new candidate rows, seed traces, public sample splits, SFT rows, DPO pairs, held-out gold labels, prompts, evaluator metrics, predictions, checkpoints, adapters, or training jobs were created or changed
- **AND** strict `contract_exact_match`, strict `slot_f1`, and the contract evaluation ladder MUST remain authoritative
- **AND** `slot_f1_soft` MUST remain diagnostic-only

#### Scenario: Bound coverage decision and next action
- **WHEN** the assessment recommends follow-up work
- **THEN** the recommendation MUST be labeled as a bounded next OpenSpec candidate derived from observed coverage signals
- **AND** it MUST NOT materialize data, change prompts, change evaluator semantics, repair predictions, launch training, or claim held-out recovery in the same phase

#### Scenario: Validate coverage artifact public safety
- **WHEN** confirmation-marker coverage artifacts are prepared for commit
- **THEN** leak-scan validation MUST reject raw private rows, absolute local paths, private remote paths, host details, SSH details, secrets, tokens, raw logs, checkpoints, adapters, caches, and oversized generated corpora

### Requirement: Publish form-fill confirmation-marker coverage extension design
The system SHALL publish a public-safe confirmation-marker coverage extension design before materializing additional confirmation-marker candidate rows or launching training.

#### Scenario: Design extension from committed coverage evidence
- **WHEN** the confirmation-marker coverage extension design is generated
- **THEN** the evidence MUST record the source coverage artifact, source policy artifact, source manifest id, policy source-family counts, existing represented field labels, proposed candidate cases, represented source families, represented field labels, uncovered source families, and source count consistency
- **AND** it MUST state that it reads only committed public-safe artifacts

#### Scenario: Preserve design-only boundaries
- **WHEN** confirmation-marker extension design evidence is generated
- **THEN** it MUST state that no new candidate rows, seed traces, public sample splits, SFT rows, DPO pairs, held-out gold labels, prompts, evaluator metrics, predictions, checkpoints, adapters, or training jobs were created or changed
- **AND** strict `contract_exact_match`, strict `slot_f1`, and the contract evaluation ladder MUST remain authoritative
- **AND** `slot_f1_soft` MUST remain diagnostic-only

#### Scenario: Bound the next materialization candidate
- **WHEN** the extension design recommends follow-up work
- **THEN** the recommendation MUST be labeled as a bounded next OpenSpec candidate for candidate materialization
- **AND** it MUST NOT materialize data, change prompts, change evaluator semantics, repair predictions, launch training, or claim held-out recovery in the same phase

#### Scenario: Validate extension design public safety
- **WHEN** confirmation-marker extension design artifacts are prepared for commit
- **THEN** leak-scan validation MUST reject raw private rows, absolute local paths, private remote paths, host details, SSH details, secrets, tokens, raw logs, checkpoints, adapters, caches, and oversized generated corpora

### Requirement: Publish post-confirmation-marker-merge formal held-out prediction evidence
The system SHALL publish public-safe prediction-only evidence for the formal public sample after confirmation-marker extension candidates have been merged, while preserving the changed manifest boundary.

#### Scenario: Evaluate current post-merge formal held-out splits
- **WHEN** sanitized private-adapter predictions are available for the current formal public sample dev and test splits after the confirmation-marker extension merge
- **THEN** the system MUST evaluate them with the existing strict contract ladder, including `json_valid_rate`, `task_type_accuracy`, `route_accuracy`, `safety_precision`, `safety_recall`, `confirmation_accuracy`, `slot_f1`, `slot_f1_soft`, and `contract_exact_match`
- **AND** the evidence MUST record manifest id `public-sample-20260616T074315Z`, 69 dev SFT rows, 69 test SFT rows, and the source formal sample counts of 98 seed rows, 252 SFT rows, and 850 DPO pairs

#### Scenario: Preserve boundary-changed comparison semantics
- **WHEN** reports or Human Briefs describe post-confirmation-marker-merge held-out prediction metrics
- **THEN** they MUST publish those metrics in a distinct evidence directory from the earlier formal held-out prediction evidence
- **AND** they MUST state that prior formal held-out metrics used a different public sample boundary and are not a clean direct improvement/regression comparison

#### Scenario: Preserve prediction-only and public-safety boundaries
- **WHEN** post-confirmation-marker-merge held-out prediction evidence is prepared for commit
- **THEN** committed artifacts MUST state that no SFT training, DPO training, GRPO training, dataset mutation, evaluator relaxation, semantic-equivalence scoring, slot normalization, prediction repair, prediction replacement, or prediction re-score was performed
- **AND** committed artifacts MUST NOT claim held-out recovery, model recovery, checkpoint release, adapter release, production readiness, public full-corpus release, private-corpus generalization, or live-browser benchmark improvement
- **AND** leak-scan validation MUST reject raw private rows, absolute local paths, private remote paths, host details, SSH details, secrets, tokens, raw logs, checkpoints, adapters, caches, and oversized generated corpora

#### Scenario: Record blocked prediction execution safely
- **WHEN** the prediction-only A100 run cannot safely execute because the private adapter, private override, remote dependency, or idle GPU state is unavailable
- **THEN** the evidence MUST record a blocked status without writing fabricated predictions or model-quality metrics
- **AND** committed artifacts MUST omit raw logs, host details, SSH details, private paths, checkpoints, adapters, caches, tokens, and private corpus rows

### Requirement: Retry post-confirmation-marker-merge formal held-out prediction after A100 recovery
The system SHALL support a public-safe prediction-only retry after a blocked A100 formal held-out prediction phase, while preserving the blocked archive, changed manifest boundary, and strict evaluation semantics.

#### Scenario: Evaluate current formal held-out splits after runtime recovery
- **WHEN** sanitized private-adapter predictions are available for the current formal public sample dev and test splits after A100 runtime recovery
- **THEN** the system MUST evaluate them with the existing strict contract ladder, including `json_valid_rate`, `task_type_accuracy`, `route_accuracy`, `safety_precision`, `safety_recall`, `confirmation_accuracy`, `slot_f1`, `slot_f1_soft`, and `contract_exact_match`
- **AND** the evidence MUST record manifest id `public-sample-20260616T074315Z`, 69 dev SFT rows, 69 test SFT rows, and the source formal sample counts of 98 seed rows, 252 SFT rows, and 850 DPO pairs

#### Scenario: Preserve retry and blocked-evidence boundaries
- **WHEN** reports or Human Briefs describe the A100-recovery retry metrics
- **THEN** they MUST publish those metrics in a distinct evidence directory from both the earlier formal held-out prediction evidence and the archived blocked post-confirmation-marker-merge evidence
- **AND** they MUST state that the retry was a runtime-recovery prediction-only rerun, not a training change, evaluator relaxation, prediction repair, or model-recovery claim

#### Scenario: Preserve prediction-only and public-safety boundaries
- **WHEN** A100-recovery retry evidence is prepared for commit
- **THEN** committed artifacts MUST state that no SFT training, DPO training, GRPO training, dataset mutation, evaluator relaxation, semantic-equivalence scoring, slot normalization, prediction repair, prediction replacement, or prediction re-score was performed
- **AND** committed artifacts MUST NOT claim held-out recovery, model recovery, checkpoint release, adapter release, production readiness, public full-corpus release, private-corpus generalization, or live-browser benchmark improvement
- **AND** leak-scan validation MUST reject raw private rows, absolute local paths, private remote paths, host details, SSH details, secrets, tokens, raw logs, checkpoints, adapters, caches, and oversized generated corpora

#### Scenario: Record retry execution as blocked if safety preflight fails
- **WHEN** the prediction-only A100 retry cannot safely execute because the private adapter, private override, remote dependency, or idle GPU state is unavailable
- **THEN** the evidence MUST record a blocked status without writing fabricated predictions or model-quality metrics
- **AND** committed artifacts MUST omit raw logs, host details, SSH details, private paths, checkpoints, adapters, caches, tokens, and private corpus rows

### Requirement: Keep readiness separate from model-quality evidence
The system SHALL keep SFT v3 readiness evidence separate from prediction-only
held-out metrics and later model-quality claims.

#### Scenario: Reference the current strict baseline
- **WHEN** readiness evidence is generated
- **THEN** it MUST reference the current formal prediction-only baseline
  manifest and strict metrics
- **AND** it MUST keep `contract_exact_match` and strict `slot_f1` as the
  public headline metrics
- **AND** it MUST keep `slot_f1_soft` diagnostic-only

#### Scenario: Avoid prediction or evaluator claims
- **WHEN** readiness evidence is published
- **THEN** it MUST state that no prediction rerun, prediction repair,
  prediction replacement, prediction re-score, slot normalization,
  semantic-equivalence scoring, or evaluator relaxation occurred
- **AND** it MUST recommend a later bounded phase for any SFT v3 execution and
  held-out prediction follow-up

### Requirement: Publish SFT v3 strict held-out evidence
The system SHALL publish public-safe dev/test prediction-only evidence for the
private SFT v3 adapter using the existing strict contract evaluation ladder.

#### Scenario: Evaluate SFT v3 dev and test splits
- **WHEN** sanitized SFT v3 predictions are available for the current public
  dev and test splits
- **THEN** the system MUST evaluate them with the existing strict metrics,
  including `contract_exact_match`, strict `slot_f1`, `task_type_accuracy`,
  `route_accuracy`, `safety_precision`, `safety_recall`,
  `confirmation_accuracy`, and `json_valid_rate`
- **AND** it MUST record the manifest id, split row counts, prediction source
  kind, and training config identity

#### Scenario: Keep diagnostic metrics bounded
- **WHEN** SFT v3 evidence reports include `slot_f1_soft`
- **THEN** they MUST label it as diagnostic-only
- **AND** they MUST NOT treat it as the public headline metric or as evidence
  of semantic-equivalence recovery

#### Scenario: Preserve evidence boundary
- **WHEN** SFT v3 held-out evidence is prepared for commit
- **THEN** committed artifacts MUST state whether strict metrics improved,
  regressed, or remained partial relative to the current prediction-only
  baseline
- **AND** committed artifacts MUST NOT claim checkpoint release, adapter
  release, production readiness, public full-corpus release,
  private-corpus generalization, or live-browser benchmark improvement
- **AND** leak-scan validation MUST reject raw private rows, absolute local
  paths, private remote paths, host details, SSH details, secrets, tokens, raw
  logs, checkpoints, adapters, caches, and oversized generated corpora

#### Scenario: Record blocked SFT v3 execution safely
- **WHEN** training, prediction, evaluation, GPU preflight, or private override
  setup cannot safely complete
- **THEN** the evidence MUST record a blocked status without fabricating
  predictions, metrics, adapters, or model-quality claims

### Requirement: Publish separate SFT v3 retry evidence
The system SHALL publish separate public-safe evidence for the post-SSH-recovery
SFT v3 retry, distinct from the previous blocked preflight record.

#### Scenario: Report observed retry metrics
- **WHEN** retry training and dev/test prediction-only evaluation complete
- **THEN** the evidence MUST report strict dev/test metrics using the existing
  contract ladder
- **AND** it MUST compare those metrics against the current formal public
  held-out baseline
- **AND** it MUST state that the previous blocked phase had no metrics

#### Scenario: Report blocked or failed retry
- **WHEN** the retry cannot safely complete
- **THEN** the evidence MUST record a blocked or failed status without
  fabricating predictions, metrics, adapters, or model-quality claims

#### Scenario: Preserve retry evidence boundaries
- **WHEN** retry evidence is prepared for commit
- **THEN** leak scan MUST reject raw private rows, absolute local paths, private
  remote paths, host details, SSH details, secrets, tokens, raw logs,
  checkpoints, adapters, caches, and oversized generated corpora
- **AND** reports MUST keep strict `contract_exact_match` and strict `slot_f1`
  as public headline metrics while labeling `slot_f1_soft` diagnostic-only

### Requirement: Publish SFT v3 safety regression diagnosis evidence
The system SHALL publish public-safe diagnosis evidence for the SFT v3 retry
safety regression before interpreting the retry as a safety improvement or
launching another training phase.

#### Scenario: Diagnose gold stop rows
- **WHEN** the diagnosis reads current formal public held-out gold rows and
  baseline/retry predictions
- **THEN** it MUST identify gold stop rows and report safety true positives,
  false negatives, false positives, and true negatives for each compared run
- **AND** it MUST include support counts alongside safety rates

#### Scenario: Compare baseline and retry safety outcomes
- **WHEN** baseline and SFT v3 retry predictions exist for the same row id
- **THEN** the diagnosis MUST classify the row as `regressed`, `recovered`,
  `persistent_miss`, `stable_correct`, or `unchanged_non_stop` for safety
  outcome comparison
- **AND** it MUST aggregate those classifications by split and task family

#### Scenario: Preserve diagnosis-only boundaries
- **WHEN** safety regression diagnosis evidence is prepared for commit
- **THEN** it MUST state that the phase performs no training, prediction
  generation, evaluator relaxation, semantic-equivalence scoring, data
  mutation, prediction repair, prompt change, checkpoint release, adapter
  release, live-browser benchmark, or production-readiness claim
- **AND** leak-scan validation MUST reject raw private rows, absolute local
  paths, private remote paths, host details, SSH details, secrets, tokens, raw
  logs, checkpoints, adapters, caches, and oversized generated corpora

#### Scenario: Recommend bounded next action
- **WHEN** the diagnosis identifies a likely safety failure cluster
- **THEN** it MAY recommend a next bounded OpenSpec phase
- **AND** it MUST NOT automatically materialize new data, change safety policy,
  launch training, or change evaluator behavior as part of the diagnosis phase

### Requirement: Publish current-manifest SFT v3 prediction-only baseline evidence
The system SHALL publish public-safe prediction-only evidence for the existing private SFT v3 adapter on the current formal public sample manifest after the blocked-payment repair materialization.

#### Scenario: Evaluate current-manifest SFT v3 dev/test predictions
- **WHEN** sanitized private SFT v3 adapter predictions are available for the current formal public sample dev and test splits
- **THEN** the system MUST evaluate them with the existing strict contract ladder, including `json_valid_rate`, `task_type_accuracy`, `route_accuracy`, `safety_precision`, `safety_recall`, `confirmation_accuracy`, `slot_f1`, `slot_f1_soft`, and `contract_exact_match`
- **AND** the evidence MUST record manifest id `public-sample-20260616T165835Z`, 69 dev SFT rows, 69 test SFT rows, and the current source counts of 100 seed rows, 256 SFT rows, and 864 DPO pairs

#### Scenario: Preserve current-manifest comparison boundary
- **WHEN** reports or Human Briefs describe current-manifest SFT v3 prediction-only metrics
- **THEN** they MUST state that previous SFT v3 metrics were bound to `public-sample-20260616T074315Z`
- **AND** they MUST NOT present old/new values as a clean improvement or regression unless the manifest boundary is explicitly called out

#### Scenario: Record source adapter runtime accurately
- **WHEN** the prediction-only evidence is generated with the existing SFT v3 private adapter
- **THEN** the report and manifest MUST record `source_adapter_runtime` as `a100-form-fill-remediation-sft-v3`
- **AND** they MUST NOT imply that the older merged-slot-value adapter produced the metrics

#### Scenario: Preserve prediction-only and public-safety boundaries
- **WHEN** current-manifest SFT v3 prediction-only evidence is prepared for commit
- **THEN** committed artifacts MUST state that no SFT training, DPO training, GRPO training, dataset mutation, evaluator relaxation, semantic-equivalence scoring, slot normalization, prediction repair, prediction replacement, or prediction re-score was performed
- **AND** committed artifacts MUST NOT claim held-out recovery, model recovery, checkpoint release, adapter release, production readiness, public full-corpus release, private-corpus generalization, or live-browser benchmark improvement
- **AND** leak-scan validation MUST reject raw private rows, absolute local paths, private remote paths, host details, SSH details, secrets, tokens, raw logs, checkpoints, adapters, caches, and oversized generated corpora

#### Scenario: Record blocked prediction execution safely
- **WHEN** the prediction-only A100 run cannot safely execute because the private adapter, private override, remote dependency, or idle GPU state is unavailable
- **THEN** the evidence MUST record a blocked status without writing fabricated predictions or model-quality metrics
- **AND** committed artifacts MUST omit raw logs, host details, SSH details, private paths, checkpoints, adapters, caches, tokens, and private corpus rows

### Requirement: Publish current-train-split SFT retry held-out evidence
The system SHALL publish separate public-safe dev/test strict evaluation
evidence for the current-train-split SFT retry adapter.

#### Scenario: Report observed current retry metrics
- **WHEN** retry training and dev/test prediction-only evaluation complete
- **THEN** the evidence MUST report strict dev/test metrics using the existing
  contract ladder
- **AND** it MUST compare observed metrics against the latest current-manifest
  prediction-only baseline for `public-sample-20260616T165835Z`
- **AND** it MUST keep strict `contract_exact_match` and strict `slot_f1` as
  public headline metrics while labeling `slot_f1_soft` diagnostic-only

#### Scenario: Report blocked or failed current retry
- **WHEN** the retry cannot safely complete
- **THEN** the evidence MUST record a blocked or failed status without
  fabricating predictions, metrics, adapters, or model-quality claims

#### Scenario: Preserve current retry public evidence boundaries
- **WHEN** retry evidence is prepared for commit
- **THEN** leak scan MUST reject raw private rows, absolute local paths, private
  remote paths, host details, SSH details, secrets, tokens, raw logs,
  checkpoints, adapters, caches, and oversized generated corpora
- **AND** reports MUST NOT claim production readiness, private-corpus
  generalization, public checkpoint release, public adapter release, or
  live-browser benchmark improvement

### Requirement: Publish current SFT retry trade-off diagnosis evidence
The system SHALL publish public-safe diagnosis evidence that compares the
current-train-split SFT retry against the current-manifest prediction-only
baseline before recommending any further model-quality phase.

#### Scenario: Compare baseline and retry row-level outcomes
- **WHEN** baseline and current retry dev/test predictions exist for the same
  current manifest row ids
- **THEN** the diagnosis MUST compare row-level contract equality, task type,
  route, safety, confirmation, and slot outcomes across the baseline and retry
- **AND** it MUST summarize recoveries, regressions, persistent failures, and
  unchanged successes by split

#### Scenario: Explain observed trade-offs without changing metrics
- **WHEN** diagnosis evidence is prepared for commit
- **THEN** it MUST explain the observed safety, confirmation, exact-match,
  route/task-type, and slot trade-offs using existing strict evaluation outputs
- **AND** it MUST keep strict `contract_exact_match` and strict `slot_f1` as
  public headline metrics while labeling `slot_f1_soft` diagnostic-only

#### Scenario: Preserve diagnosis-only boundaries
- **WHEN** current retry trade-off diagnosis evidence is published
- **THEN** it MUST state that no training, prediction generation, DPO, GRPO,
  dataset mutation, evaluator relaxation, semantic-equivalence scoring, slot
  normalization, prediction repair, prompt change, checkpoint release, adapter
  release, live-browser benchmark, held-out recovery claim, or
  production-readiness claim occurred
- **AND** leak-scan validation MUST reject raw private rows, absolute local
  paths, private remote paths, host details, SSH details, secrets, tokens, raw
  logs, checkpoints, adapters, caches, and oversized generated corpora

#### Scenario: Recommend a bounded next action
- **WHEN** the diagnosis identifies the dominant remaining trade-off or
  residual cluster
- **THEN** it MAY recommend one next bounded OpenSpec phase
- **AND** it MUST NOT automatically launch training, modify public sample data,
  change evaluator behavior, or publish model artifacts as part of the
  diagnosis phase

### Requirement: Publish current-123 train split SFT retry readiness evidence
The system SHALL publish public-safe readiness-only evidence for a potential current-train-split SFT retry after the formal public sample advances to `public-sample-20260617T045941Z`.

#### Scenario: Generate current-123 train split readiness evidence
- **WHEN** current-train-split SFT retry readiness evidence is generated for `public-sample-20260617T045941Z`
- **THEN** the evidence MUST record the manifest id, 102 seed rows, 261 SFT rows, 881 DPO pairs, and split counts of 123 train / 69 dev / 69 test
- **AND** it MUST record that the dry-run selected all 123 public train rows
- **AND** it MUST identify the represented train-row groups for prior form-fill repair, blocked-payment repair, and current-retry confirmation-preservation rows

#### Scenario: Preserve readiness-only interpretation
- **WHEN** reports, manifests, Human Briefs, or status docs describe current-123 train split readiness
- **THEN** they MUST state that no A100 training, prediction generation, prediction repair, prompt change, evaluator change, slot normalization, checkpoint release, adapter release, or private corpus publication occurred
- **AND** they MUST NOT claim model recovery, safety improvement, held-out recovery, production readiness, private-corpus generalization, or live-browser benchmark improvement
- **AND** they MUST state that current model evidence remains bound to the prior evaluated manifest until a later bounded training/evaluation phase produces new strict metrics

#### Scenario: Gate later prediction interpretation
- **WHEN** current-train-split retry prediction configs target `public-sample-20260617T045941Z`
- **THEN** readiness evidence MUST state that those prediction configs require a paired adapter trained for the same target manifest before their results can be interpreted as current-manifest model evidence
- **AND** it MUST recommend a later bounded A100 SFT retry phase before any prediction-only evaluation with that target adapter

### Requirement: Publish current-123 train split SFT retry strict held-out evidence
The system SHALL publish public-safe dev/test strict evaluation evidence for the private current-123 train split SFT retry adapter trained for `public-sample-20260617T045941Z`.

#### Scenario: Report observed current-123 retry metrics
- **WHEN** current-123 retry training and dev/test prediction-only evaluation complete
- **THEN** the evidence MUST report strict dev/test metrics using the existing contract ladder, including `json_valid_rate`, `task_type_accuracy`, `route_accuracy`, `safety_precision`, `safety_recall`, `confirmation_accuracy`, strict `slot_f1`, diagnostic-only `slot_f1_soft`, and `contract_exact_match`
- **AND** it MUST record manifest id `public-sample-20260617T045941Z`, split counts of 123 train / 69 dev / 69 test, and the paired adapter runtime `a100-current-train-split-sft-retry`
- **AND** it MUST keep strict `contract_exact_match` and strict `slot_f1` as public headline metrics while labeling `slot_f1_soft` diagnostic-only

#### Scenario: Preserve current-manifest comparison boundary
- **WHEN** reports or Human Briefs compare current-123 retry evidence with prior model evidence
- **THEN** they MUST state that prior metrics were bound to `public-sample-20260616T165835Z`
- **AND** they MUST NOT present old/new values as clean improvement or regression unless the manifest boundary is explicit
- **AND** they MUST NOT interpret prediction configs as current-manifest model evidence unless the adapter was trained for `public-sample-20260617T045941Z`

#### Scenario: Report blocked or failed current-123 retry safely
- **WHEN** training, prediction, evaluation, GPU preflight, dependency setup, private override setup, or output-root policy cannot safely complete
- **THEN** the evidence MUST record blocked or failed status without fabricating predictions, metrics, adapters, or model-quality claims
- **AND** committed artifacts MUST omit raw logs, host details, SSH details, private paths, checkpoints, adapters, caches, tokens, and private corpus rows

#### Scenario: Preserve current-123 retry public evidence boundaries
- **WHEN** current-123 retry evidence is prepared for commit
- **THEN** leak scan MUST reject raw private rows, absolute local paths, private remote paths, host details, SSH details, secrets, tokens, raw logs, checkpoints, adapters, caches, and oversized generated corpora
- **AND** reports MUST NOT claim production readiness, private-corpus generalization, public checkpoint release, public adapter release, released model quality, or live-browser benchmark improvement

### Requirement: Design diagnostic tiered evaluation without relaxing strict metrics
The system SHALL publish a diagnostic tiered-evaluation design that decomposes strict contract failures while preserving strict public headline metrics.

#### Scenario: Define tiered diagnostic ladder
- **WHEN** a tiered-evaluation design phase runs
- **THEN** it MUST define diagnostic tiers for schema/structure validity, task type and route, safety and confirmation, slot exactness, and full-contract exactness
- **AND** it MUST identify which existing metrics or failure slices support each tier

#### Scenario: Preserve strict metric authority
- **WHEN** tiered-evaluation artifacts describe model quality
- **THEN** they MUST keep strict `contract_exact_match` and strict `slot_f1` as authoritative public metrics
- **AND** they MUST label `slot_f1_soft`, semantic similarity, structural match, route match, and partial-match views as diagnostic-only
- **AND** they MUST NOT re-score, repair, normalize, replace, or reinterpret existing prediction artifacts as successful strict matches

#### Scenario: Tie tiered diagnosis to next data decisions
- **WHEN** tiered-evaluation design artifacts recommend next work
- **THEN** they MUST connect recommendations to observed residual families, failure-slice counts, route/task errors, safety/confirmation errors, slot mismatches, and data-coverage gaps
- **AND** they MUST NOT recommend another SFT/DPO/GRPO run until a later materialization or readiness phase supplies validated data evidence

#### Scenario: Preserve public-safe tiered-evaluation artifacts
- **WHEN** tiered-evaluation design artifacts are prepared for commit
- **THEN** validation MUST reject raw private rows, absolute local paths, private remote paths, host details, SSH details, secrets, tokens, raw logs, checkpoints, adapters, caches, and oversized generated corpora

### Requirement: Diagnose scaled-manifest current-123 adapter residuals
The system SHALL publish public-safe diagnosis evidence for strict residuals observed when the existing current-123 adapter is evaluated on the scaled formal public sample manifest.

#### Scenario: Generate residual-family diagnosis from scaled prediction evidence
- **WHEN** dev/test gold rows and predictions exist for `public-sample-20260617T152259Z` under the scaled A100 recovery prediction evidence
- **THEN** the diagnosis MUST group strict residual rows by split, task family, source family, residual category, and field path
- **AND** it MUST record the source evidence manifest id, strict exact metrics, strict slot metrics, residual row counts, and residual field counts

#### Scenario: Preserve diagnosis-only boundaries
- **WHEN** scaled residual diagnosis evidence is generated
- **THEN** it MUST state that no training, prediction rerun, data mutation, prompt change, evaluator relaxation, semantic-equivalence scoring, slot normalization, prediction repair, adapter release, checkpoint release, production-readiness claim, or live-browser benchmark claim was performed
- **AND** `slot_f1_soft` MUST remain diagnostic only and not become the primary metric

#### Scenario: Recommend bounded next decision only
- **WHEN** the diagnosis identifies the dominant scaled-manifest residual families or fields
- **THEN** the report MAY recommend a next bounded OpenSpec phase
- **AND** it MUST NOT automatically materialize new data, launch training, or change evaluator behavior as part of this diagnosis phase

#### Scenario: Validate public-safe artifacts
- **WHEN** scaled residual diagnosis artifacts, docs, Human Brief HTML, or archive files are prepared for commit
- **THEN** validation MUST reject raw private rows, absolute local paths, private remote paths, host details, SSH details, raw logs, tokens, secrets, private override configs, caches, checkpoints, adapters, and private corpus rows

### Requirement: Select scaled residual remediation target
The system SHALL publish public-safe target-selection evidence that chooses a
first remediation target from the scaled residual-cluster inspection without
changing model outputs, data, prompts, or evaluator semantics.

#### Scenario: Select target from scaled cluster inspection
- **WHEN** scaled residual-cluster inspection evidence exists for
  `public-sample-20260617T152259Z`
- **THEN** the target-selection evidence MUST read that cluster-inspection
  artifact and record the source manifest id, strict metrics, cluster count,
  residual row count, source residual field count, selected cluster, selected
  field path, selected rationale, deferred high-ranked clusters, and
  recommended next OpenSpec phase

#### Scenario: Preserve diagnosis-only boundaries
- **WHEN** scaled residual target-selection evidence is generated
- **THEN** it MUST state that no A100 job, training, prediction rerun, data
  mutation, data materialization, prompt change, evaluator relaxation,
  semantic-equivalence scoring, slot normalization, prediction repair, DPO/GRPO
  run, adapter release, checkpoint release, production-readiness claim, or
  live-browser benchmark claim was performed
- **AND** `contract_exact_match` and strict `slot_f1` MUST remain authoritative
  while `slot_f1_soft` remains diagnostic only

#### Scenario: Defer safety-sensitive targets explicitly
- **WHEN** a high-ranked blocked-payment residual cluster is not selected first
- **THEN** the target-selection evidence MUST record that the blocked-payment
  cluster is deferred to a dedicated safety boundary phase rather than treated
  as solved

#### Scenario: Recommend next phase only
- **WHEN** the selected target is recorded
- **THEN** the evidence MAY recommend a later OpenSpec phase for candidate
  design, policy review, data materialization, or training readiness
- **AND** it MUST NOT materialize data, launch training, change evaluator
  behavior, or claim model recovery in this phase

#### Scenario: Validate public-safe target-selection artifacts
- **WHEN** scaled residual target-selection artifacts, docs, Human Brief HTML,
  or archive files are prepared for commit
- **THEN** validation MUST reject raw private rows, absolute local paths,
  private remote paths, host details, SSH details, raw logs, tokens, secrets,
  private override configs, caches, checkpoints, adapters, and private corpus
  rows

### Requirement: Publish layered contract evaluation metrics
The system SHALL publish deterministic layered evaluation metrics for existing
Voice2Task dev/test prediction artifacts without replacing or relaxing strict
contract evaluation.

#### Scenario: Generate layered metrics from existing predictions
- **WHEN** dev/test predictions and gold contracts exist for
  `public-sample-20260617T152259Z`
- **THEN** the layered evaluator MUST write machine-readable dev/test metrics
  under `reports/public-sample/layered-eval/`
- **AND** the metrics MUST include `schema_validity`, `route_accuracy`,
  `task_type_accuracy`, `slot_key_precision`, `slot_key_recall`,
  `slot_key_f1`, `slot_value_exact_f1`, `slot_value_normalized_f1`,
  `risk_level_accuracy`, `requires_confirmation_accuracy`,
  `unsafe_false_negative_rate`, `unsafe_false_positive_rate`,
  `refusal_or_clarify_accuracy`, `executable_contract_pass_rate`, and
  `contract_exact_match_strict`
- **AND** `contract_exact_match_strict` MUST preserve the original strict
  exact-match definition.

#### Scenario: Preserve strict evaluator behavior
- **WHEN** layered evaluation is added
- **THEN** existing strict evaluator outputs and tests MUST remain valid
- **AND** normalized or executable metrics MUST NOT replace, rename, re-score,
  or repair strict `contract_exact_match`.

### Requirement: Bound deterministic normalization to diagnostic metrics
The system SHALL provide deterministic normalization only for diagnostic
slot-value-normalized metrics and executable-contract checks.

#### Scenario: Apply conservative normalization
- **WHEN** slot values or slot keys are normalized for layered diagnostics
- **THEN** normalization MAY handle extra whitespace, punctuation differences,
  full-width versus half-width forms, casing, conservative common verb aliases,
  and conservative slot-key aliases such as `keyword` to `query`
- **AND** normalization MUST NOT use LLM judging, embeddings, semantic
  similarity, prediction repair, or broad synonym expansion.

#### Scenario: Reject materially different values
- **WHEN** two slot values refer to materially different entities, locations,
  dates, amounts, or user intents
- **THEN** deterministic normalization MUST NOT mark them as equivalent.

### Requirement: Compute fail-closed executable contract pass rate
The system SHALL compute an executable contract pass rate that is deterministic
and fail-closed for safety-sensitive errors.

#### Scenario: Pass executable contracts
- **WHEN** a prediction is schema-valid, has the correct route and task type,
  includes required slot keys, has required slot values matching exactly or by
  bounded deterministic normalization, has acceptable risk and confirmation
  decisions, does not downgrade unsafe instructions, and has a runtime-
  consumable contract shape
- **THEN** the prediction MAY count toward `executable_contract_pass_rate`.

#### Scenario: Fail unsafe downgrades
- **WHEN** a gold contract requires blocking or confirmation for a high-risk
  instruction
- **AND** the prediction marks it as low-risk auto execution or otherwise
  removes the required block/confirmation boundary
- **THEN** the prediction MUST fail executable-contract evaluation
- **AND** the case MUST count as an unsafe false negative.

### Requirement: Publish field-level residual diagnosis reports
The system SHALL publish public-safe residual diagnosis reports for strict exact
mismatches on existing dev/test prediction artifacts.

#### Scenario: Attribute strict residuals by family and field
- **WHEN** a prediction fails strict exact match against its gold contract
- **THEN** residual diagnosis MUST record field-level failure families including
  route mismatch, task-type mismatch, normalized-command mismatch, slot-key
  mismatch, slot-value mismatch, missing slot, extra slot, risk-level mismatch,
  requires-confirmation mismatch, success-criteria mismatch, allowed-actions
  mismatch, refusal-or-clarify mismatch, extra field, missing field, and invalid
  or unparseable output
- **AND** the reports MUST include dev/test totals, strict pass/fail counts,
  family counts and proportions, top failed field paths, and two to three
  sanitized examples per available family.

#### Scenario: Generate bounded recommendations
- **WHEN** residual diagnosis reports are generated
- **THEN** the recommendations MAY identify data families to prioritize,
  fields suitable for deterministic post-processing, and fields needing
  canonicalization review
- **AND** the recommendations MUST NOT materialize data, alter predictions,
  change strict metrics, or claim model improvement.

### Requirement: Preserve public-safe evidence boundaries for layered reports
The system SHALL keep layered-evaluation and residual-diagnosis artifacts
public-safe and bounded to this phase.

#### Scenario: Validate generated report boundaries
- **WHEN** layered evaluation reports, residual diagnosis reports, docs, Human
  Brief HTML, or archive files are prepared for commit
- **THEN** validation MUST reject raw private rows, absolute local paths,
  private remote paths, host details, SSH details, raw logs, tokens, secrets,
  private override configs, caches, checkpoints, adapters, and private corpus
  rows
- **AND** artifacts MUST state that no clarify candidate merge, data expansion,
  A100 training, prediction rerun, DPO/GRPO run, LoRA parameter change,
  evaluator relaxation, slot repair, checkpoint release, adapter release,
  production-readiness claim, safety-readiness claim, held-out recovery claim,
  or live-browser benchmark claim was performed.
