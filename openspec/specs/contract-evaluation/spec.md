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
