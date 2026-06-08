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
