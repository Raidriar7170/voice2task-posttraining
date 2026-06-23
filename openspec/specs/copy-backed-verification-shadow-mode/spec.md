# copy-backed-verification-shadow-mode Specification

## Purpose
Define the sidecar-only shadow-mode integration for copy-backed slot verification over current Voice2Task prediction contracts, including input-boundary validation, one-sidecar-per-prediction attachment, task-scoped policy reuse, action exclusion, provenance/correctness separation, non-enforcement proof, and compact public-safe evidence.
## Requirements
### Requirement: Validate shadow-mode input boundary
The system SHALL validate that shadow-mode integration uses only the current recovered raw inputs and the completed copy-backed verification slice evidence.

#### Scenario: Accepted shadow boundary
- **WHEN** the shadow-mode report is generated
- **THEN** it confirms the previous copy slice decision is `COPY_SLICE_READY_FOR_SHADOW_INTEGRATION`, enabled task-scoped triples are unchanged, `action` remains disabled, V1 evaluator metric delta is zero, raw input hashes are preserved, and no active OpenSpec predecessor is required
- **AND** it proceeds without reading superseded adapters, raw model logs, checkpoints, private rows, external services, or runtime browser state

#### Scenario: Invalid shadow boundary blocks output
- **WHEN** required source artifacts are missing, the previous copy slice is not ready, raw file hashes drift, action is enabled, or V1 evaluator zero-delta evidence is absent
- **THEN** the system writes `blocked.json` with `decision=SHADOW_MODE_BLOCKED_INVALID_INPUT`
- **AND** it MUST NOT write success summaries, shadow sidecars, enforcement recommendations, or model-quality claims

### Requirement: Attach copy-backed verifier as prediction-contract shadow sidecars
The system SHALL produce one deterministic sidecar row per Control/Treatment prediction contract without mutating the prediction contract.

#### Scenario: One sidecar per prediction contract
- **WHEN** shadow mode runs over the recovered dev/test Control/Treatment predictions
- **THEN** it writes exactly one shadow sidecar per `(split, sample_id, run_role)` prediction contract
- **AND** each sidecar includes `shadow_mode_enabled=true`, `enforcement_enabled=false`, `prediction_contract_hash`, `input_hash`, `policy_version`, and a deterministic nested `slot_diagnostics` list

#### Scenario: Prediction payload is immutable
- **WHEN** shadow sidecars are generated
- **THEN** recovered prediction files, gold files, evaluator inputs, `BrowserTaskContract` V1, `ContractCoreV2`, training targets, prompts, and runtime behavior remain unchanged
- **AND** the report proves raw input hashes and V1 evaluator metric deltas remain unchanged

### Requirement: Preserve task-scoped policy and action exclusion
The system SHALL reuse the previously approved task-scoped copy-backed policy without expanding enabled slots.

#### Scenario: Enabled slots remain query field target
- **WHEN** eligible prediction slots are verified in shadow mode
- **THEN** only task-scoped `query`, `field`, and `target` values from approved triples may receive `system_verified_source` provenance
- **AND** out-of-policy slots MUST be marked out-of-scope or unresolved in slot diagnostics

#### Scenario: Action stays disabled in shadow mode
- **WHEN** prediction contracts contain `action`
- **THEN** action diagnostics MUST have `verification_enabled=false`, `provenance=unresolved`, and no source-verified acceptance
- **AND** action counts MUST be reported separately as disabled analysis, not as a readiness gate success

### Requirement: Separate shadow provenance from correctness and enforcement
The system SHALL report shadow provenance, gold correctness side analysis, and enforcement status as distinct fields.

#### Scenario: Source verified does not imply correctness
- **WHEN** an eligible prediction value is source verified in a shadow sidecar
- **THEN** the report separately counts source-verified predictions, source-verified-and-gold-correct predictions, and source-verified-but-gold-mismatch predictions
- **AND** it MUST state that source-backed provenance is not task correctness, slot accuracy, executable quality, runtime readiness, or production readiness

#### Scenario: Shadow mode cannot enforce behavior
- **WHEN** a shadow sidecar contains failed, missing, ambiguous, unsupported, invalid, or out-of-scope diagnostics
- **THEN** the sidecar MUST NOT alter the prediction, suppress output, request clarification, or affect evaluator results
- **AND** `enforcement_enabled` MUST remain false for every sidecar

### Requirement: Report shadow-mode decision gates
The system SHALL publish deterministic shadow-mode metrics and exactly one final decision label.

#### Scenario: Required shadow metrics are present
- **WHEN** shadow-mode reporting completes
- **THEN** `summary.json` MUST include sidecar attachment count/rate, prediction contract count, enabled slot diagnostic count, out-of-scope diagnostic count, action disabled diagnostic count, source-verified prediction count/rate, source-verified-and-gold-correct count/rate, source-verified-but-gold-mismatch count/rate, fail-closed count/rate, provenance false accept count, silent fallback count, deterministic rerun rate, raw input hash preservation, V1 evaluator metric delta evidence, and enforcement enabled count

#### Scenario: Ready label requires all gates
- **WHEN** every shadow-mode gate is satisfied
- **THEN** the final decision label MAY be `SHADOW_MODE_READY_FOR_REVIEW`
- **AND** the only recommended next change MUST be `review-copy-backed-shadow-mode-before-runtime-wiring`

#### Scenario: Non-ready labels stay narrow
- **WHEN** input boundary is valid but shadow-mode readiness gates are not satisfied
- **THEN** the final decision label MUST be `SHADOW_MODE_PARTIAL_NEEDS_REFINEMENT` or `SHADOW_MODE_NOT_READY`
- **AND** the report MUST name exactly one bounded next change and MUST NOT recommend immediate runtime enforcement, action enablement, training, evaluator changes, or prediction repair

### Requirement: Publish compact public-safe shadow evidence
The system SHALL publish a compact public-safe evidence bundle and concise documentation for shadow-mode integration.

#### Scenario: Evidence bundle surface
- **WHEN** shadow-mode integration succeeds
- **THEN** `reports/public-sample/copy-backed-verification-shadow-mode/` MUST contain at most `summary.md`, `summary.json`, `shadow-sidecars.jsonl`, `shadow-compatibility.json`, `recommended-next-change.md`, and `blocked.json` only when blocked
- **AND** it MUST NOT include raw private rows, model outputs beyond current public-safe recovered contracts, checkpoints, adapters, raw logs, private paths, host details, SSH details, tokens, or secrets

#### Scenario: Documentation and Human Brief
- **WHEN** the phase completes
- **THEN** `docs/copy-backed-verification-shadow-mode.md` and a Chinese Human Brief MUST summarize shadow semantics, sidecar schema, verifier reuse, action exclusion, non-mutation proof, verification commands, evidence links, and claim boundaries
- **AND** they MUST NOT claim model improvement, slot accuracy improvement, executable quality improvement, runtime enforcement, production readiness, safety readiness, held-out recovery, or live-browser improvement

### Requirement: Review shadow interface before prediction hook
The system SHALL review and harden the copy-backed shadow interface before any prediction-pipeline shadow hook is proposed.

#### Scenario: Review input boundary passes
- **WHEN** the review replay is generated
- **THEN** it uses only the current recovered raw inputs, the completed copy-backed verification slice, the previous shadow-mode sidecar evidence, the frozen scope policy, local code, docs, and OpenSpec artifacts
- **AND** it does not read or mutate runtime browser state, model checkpoints, private logs, training data, adapters, evaluator logic, predictions, gold rows, or downstream runtime behavior beyond the already public-safe recovered inputs

#### Scenario: Review input boundary blocks invalid input
- **WHEN** required source artifacts are missing or incompatible
- **THEN** the review writes `blocked.json` with `decision=SHADOW_REVIEW_BLOCKED_INVALID_INPUT`
- **AND** it MUST NOT write success summaries, sidecars, audits, hook recommendations, or runtime claims

### Requirement: Freeze copy-backed scope policy v1
The system SHALL freeze the copy-backed shadow review scope with a hash-validated policy artifact.

#### Scenario: Frozen policy is valid
- **WHEN** the review loads the scope policy
- **THEN** `policy_id` is `copy-backed-scope-policy-v1`, `action_enabled=false`, `normalized_trusted=false`, and enabled triples are exactly `search:search_web:query`, `form_fill:fill_form:field`, and `extract:extract_page:target`
- **AND** the report records the policy version, evidence hash, policy hash, enabled triples, disabled triples, action exclusion, and normalized-trusted exclusion

#### Scenario: Policy drift blocks review
- **WHEN** the policy hash, enabled triples, action flag, or normalized-trusted flag drifts
- **THEN** the review writes `blocked.json` with `decision=SHADOW_REVIEW_BLOCKED_POLICY_DRIFT`
- **AND** it MUST NOT produce a ready interface label

### Requirement: Split online sidecar from offline evaluation audit
The system SHALL separate the online shadow sidecar surface from offline gold/evaluator audit evidence.

#### Scenario: Online sidecar has no gold dependency
- **WHEN** an online shadow sidecar is generated
- **THEN** the generation function accepts no gold/evaluator argument and the sidecar contains no `gold`, `correct`, evaluator-score, or model-quality fields
- **AND** trusted/candidate provenance is derived only from input text, prediction contract, policy, verifier output, request/sample identity, and hashes

#### Scenario: Evaluation audit joins gold offline
- **WHEN** the offline audit is generated
- **THEN** it joins the online sidecar to gold/evaluator evidence in a separate function and writes correctness fields only to `evaluation-audits.jsonl`
- **AND** audit results MUST NOT mutate online sidecars, predictions, gold files, evaluator inputs, runtime decisions, or V1 metrics

### Requirement: Gate trusted provenance on exact unique span validation
The system SHALL trust only exact unique source spans that pass full validation.

#### Scenario: Exact unique trusted
- **WHEN** an enabled eligible slot is `VERIFIED_EXACT_UNIQUE` with `match_kind=exact`, one candidate span, a valid source hash, valid offsets, matching current input hash, and exact back-slice equality
- **THEN** the sidecar MAY set `trusted_provenance=true`

#### Scenario: Normalized remains candidate-only
- **WHEN** an enabled eligible slot is `VERIFIED_NORMALIZED_UNIQUE`
- **THEN** the sidecar MUST set `trusted_provenance=false`, `candidate_provenance=true`, and record the normalization rule id
- **AND** normalized verification MUST NOT be counted as trusted provenance

#### Scenario: Disabled scopes never trust
- **WHEN** a slot is out of the frozen policy scope, including `action`
- **THEN** the sidecar MUST set `policy_enabled=false`, `trusted_provenance=false`, and `candidate_provenance=false` even if text-span lookup could find the value

### Requirement: Publish review metrics, per-scope breakdowns, and latency evidence
The system SHALL publish a bounded review bundle with explicit denominators and local CPU latency evidence.

#### Scenario: Metrics use explicit denominators
- **WHEN** the review summary is generated
- **THEN** it reports total slot event count, out-of-scope count/rate over total, eligible slot event count, trusted exact count/rate over eligible, normalized candidate count/rate over eligible, eligible verification failure count/rate over eligible, global non-verified count/rate over total, trusted-exact gold correctness counts/rates over trusted exact, false accepts, silent fallbacks, contract mutation count, runtime decision delta count, and V1 evaluator metric deltas

#### Scenario: Per-scope and latency evidence are present
- **WHEN** review artifacts are written
- **THEN** they include per-scope metrics for each enabled triple by split, run role, task type, route, and slot path, plus a local CPU microbenchmark for policy lookup, exact unique span lookup, full span validation, and sidecar serialization
- **AND** latency evidence MUST NOT include hostnames, private IPs, SSH details, or production SLO claims

### Requirement: Decide bounded next step without runtime claims
The system SHALL emit exactly one bounded review decision and next change recommendation.

#### Scenario: Ready for prediction hook only
- **WHEN** online sidecars have no gold dependency, offline audits are isolated, trusted provenance is exact-only, normalized trusted count is zero, action trusted count is zero, false accepts and silent fallbacks are zero, contract mutation and runtime decision deltas are zero, V1 metric deltas are zero, deterministic replay is 1.0, policy hash is fixed, per-scope metrics are complete, and leak scan is clean
- **THEN** the decision MAY be `SHADOW_INTERFACE_READY_FOR_PREDICTION_HOOK`
- **AND** the next change MUST be `integrate-copy-backed-verification-prediction-shadow-hook`, still with no runtime enforcement

#### Scenario: Scope limitations are separated
- **WHEN** interface safety gates pass but per-scope evidence shows high mismatch, not-found, or ambiguity risk
- **THEN** the decision MAY be `SHADOW_INTERFACE_READY_WITH_SCOPE_LIMITATIONS`
- **AND** the next change MUST be `refine-shadow-hook-scope-before-integration`

#### Scenario: Unsafe interface is not ready
- **WHEN** online sidecars depend on gold, normalized provenance is trusted, the trusted-span validator is incomplete, false accepts appear, action is enabled, runtime behavior changes, evaluator behavior changes, policy is unfrozen, or evidence is incomplete
- **THEN** the decision MUST be `SHADOW_INTERFACE_NOT_READY`, `SHADOW_REVIEW_BLOCKED_INVALID_INPUT`, or `SHADOW_REVIEW_BLOCKED_POLICY_DRIFT`
- **AND** the report MUST NOT recommend runtime enforcement, action enablement, training, evaluator changes, prediction repair, model-quality claims, or production readiness

### Requirement: Integrate observe-only prediction shadow hook
The system SHALL integrate a disabled-by-default copy-backed shadow hook into the canonical prediction pipeline.

#### Scenario: Canonical prediction entrypoint is hooked
- **WHEN** `voice2task-train sft-predict` or library callers use `run_sft_prediction_export`
- **THEN** the hook observes prediction values only after the existing prediction result has been determined
- **AND** it MUST NOT change model invocation, decoding, parser semantics, prediction output JSONL, evaluator input, runtime decision behavior, or exit status

#### Scenario: Default disabled behavior is unchanged
- **WHEN** prediction config omits `copy_backed_shadow` or sets `enabled=false`
- **THEN** prediction output and metadata behavior remain compatible with previous configs
- **AND** no copy-backed shadow sidecar file is created

#### Scenario: Enabled hook writes only explicit sidecars
- **WHEN** `copy_backed_shadow.enabled=true` and `sidecar_output_path` is null
- **THEN** the hook MAY compute in-memory outcomes but MUST NOT implicitly write a file
- **WHEN** `sidecar_output_path` is provided
- **THEN** sidecars are written as separate JSONL rows and MUST NOT be mixed into the prediction JSONL

### Requirement: Fail-isolate invalid prediction and hook errors
The system SHALL isolate all shadow-hook failures from the primary prediction path.

#### Scenario: Invalid predictions remain primary outputs
- **WHEN** a prediction is malformed JSON, empty, unsupported, parser-invalid, or not a valid BrowserTaskContract V1 object
- **THEN** the hook records a bounded invalid status
- **AND** the original prediction remains unchanged and unrepaired

#### Scenario: Hook internals cannot fail primary prediction
- **WHEN** policy loading, policy validation, verifier execution, sidecar serialization, or sidecar sink writing fails
- **THEN** the hook records a bounded isolated status and error code
- **AND** the primary prediction caller receives the same prediction result and status it would have received with the hook disabled

### Requirement: Fully validate frozen copy-backed scope policy
The system SHALL validate the frozen copy-backed scope policy before trusted provenance is emitted.

#### Scenario: Policy consistency passes
- **WHEN** `configs/copy-backed-scope-policy-v1.json` is loaded
- **THEN** policy id and version are non-empty, policy hash matches loaded content, enabled/disabled triple keys are unique and disjoint, scope rows are unique, scope-row keys equal enabled plus disabled keys, enabled rows equal `enabled_triples`, disabled rows equal `disabled_triples`, action is disabled, normalized trusted is false, and enabled triples are exactly `search:search_web:query`, `form_fill:fill_form:field`, and `extract:extract_page:target`
- **AND** every hook sidecar records policy id, policy version, and policy hash

#### Scenario: Policy invalid fails closed
- **WHEN** policy validation fails
- **THEN** the hook records `SHADOW_POLICY_INVALID`, emits no trusted provenance, does not use a fallback default policy, and does not affect primary prediction

### Requirement: Preserve exact-only trusted provenance and privacy defaults
The system SHALL emit trusted provenance only for exact unique source spans and default to hash-and-offset-only sidecars.

#### Scenario: Exact unique source span can be trusted
- **WHEN** an enabled slot is `VERIFIED_EXACT_UNIQUE`, exact, one candidate span, policy-valid, source-span-valid, current-input-hash-matched, and exact back-slice matched to the predicted value
- **THEN** the sidecar MAY set `trusted_provenance=true`

#### Scenario: Normalized and action paths are never trusted
- **WHEN** a slot is `VERIFIED_NORMALIZED_UNIQUE`
- **THEN** it MUST be candidate-only with `trusted_provenance=false`
- **WHEN** an action slot is observed
- **THEN** it MUST remain disabled and untrusted

#### Scenario: Sidecars avoid private text by default
- **WHEN** online sidecars are generated with default retention
- **THEN** they MUST NOT include full input text, raw model output, full prediction contract, raw request id, gold/evaluator fields, or `source_span.text`
- **AND** source span records default to start, end, source text hash, and span hash

### Requirement: Publish prediction-hook evidence and bounded decision
The system SHALL publish compact public-safe evidence and select one bounded decision label.

#### Scenario: Evidence proves output invariance
- **WHEN** the phase evidence is generated
- **THEN** it reports disabled, NullSink, and JsonlSink prediction output hashes, hash equality, contract mutation count, runtime decision delta count, V1 metric delta, deterministic rerun status, per-scope metrics, latency benchmark, leak scan result, and repo-wide lint status

#### Scenario: Ready observe-only label remains non-enforcement
- **WHEN** all acceptance gates pass
- **THEN** the decision MAY be `PREDICTION_SHADOW_HOOK_READY_OBSERVE_ONLY`
- **AND** the only recommended next change is `evaluate-frozen-copy-shadow-policy-on-template-disjoint-challenge-set`
- **AND** the system MUST NOT recommend runtime enforcement

### Requirement: Harden prediction shadow hook before challenge evaluation
The system SHALL reject misleading shadow configuration, freeze policy per prediction run, detect policy drift, and isolate sidecar path conflicts before any template-disjoint challenge prediction is evaluated.

#### Scenario: Reserved config values fail closed
- **WHEN** `copy_backed_shadow.retain_input_text=true`, `copy_backed_shadow.retain_raw_model_output=true`, or `copy_backed_shadow.fail_isolated=false`
- **THEN** the hook records a bounded configuration error and the primary prediction output remains unchanged
- **AND** the system MUST NOT silently ignore those non-default values

#### Scenario: Policy is loaded once per run
- **WHEN** an enabled copy-backed shadow prediction run starts
- **THEN** the policy is loaded, fully validated, hashed, and converted into an immutable run-level snapshot once
- **AND** every hook sidecar and run artifact records the same policy id, version, and hash with `policy_loaded_once=true`

#### Scenario: Policy drift fails closed for shadow evidence
- **WHEN** the policy file hash changes between run start and run end
- **THEN** the run records `policy_drift_detected=true`
- **AND** the decision MUST NOT pass a ready/validated label
- **AND** the primary prediction output remains unchanged

#### Scenario: Sidecar path conflicts are isolated
- **WHEN** `sidecar_output_path` resolves to the prediction output path, prediction metadata path, prompt snapshot path, raw generation summary path, generation trace path, or another primary prediction artifact path
- **THEN** the hook records `SHADOW_SINK_PATH_CONFLICT_ISOLATED`
- **AND** it MUST NOT create, append, overwrite, or fallback-write sidecar data
- **AND** the primary prediction output remains unchanged

### Requirement: Materialize and freeze template-disjoint copy-shadow challenge v1
The system SHALL create a public-safe `copy-shadow-template-disjoint-challenge-v1` challenge set before any prediction or shadow evaluation.

#### Scenario: Challenge rows have required schema
- **WHEN** challenge rows are frozen
- **THEN** each row includes challenge id, challenge version, input text, task type, route, slot path, gold slot value, gold contract, expected scope enablement, expected gold verification class, condition tags, public-safe flag, template signature, input hash, and gold hash
- **AND** every gold contract MUST validate as BrowserTaskContract V1

#### Scenario: Challenge covers enabled scopes and negative controls
- **WHEN** the challenge set is accepted
- **THEN** it contains at least 96 rows and targets 120 rows with roughly balanced `search:search_web:query`, `form_fill:fill_form:field`, and `extract:extract_page:target` enabled-scope rows
- **AND** it includes out-of-scope action and other negative-control rows

#### Scenario: Required condition tags are covered
- **WHEN** challenge rows are accepted
- **THEN** the set covers exact unique, duplicate exact, source absent, multiple entity distractor, partial span trap, normalization candidate, normalization collision, long input, ASR-style noise, synthetic PII, out-of-scope action, and invalid/unparseable output fault-injection conditions

#### Scenario: Template-disjoint audit passes before freeze
- **WHEN** candidate rows are compared with current train/dev/test rows and known template families
- **THEN** sample ids, exact input text, canonical template signatures, and slot-value-stripped template signatures have no overlap
- **AND** character 3-gram Jaccard is below 0.80 and normalized edit similarity is below 0.85 for accepted rows
- **AND** near-duplicate rows MUST NOT enter the frozen set

#### Scenario: Gold verifier feasibility matches tags
- **WHEN** gold slot values are checked before prediction
- **THEN** exact unique rows verify as `VERIFIED_EXACT_UNIQUE`, duplicate rows verify as ambiguous, source-absent rows verify as not found, and out-of-scope action rows remain untrusted
- **AND** rows whose gold feasibility does not match the expected condition MUST NOT enter the frozen set

### Requirement: Evaluate frozen policy through canonical prediction hook
The system SHALL evaluate the frozen policy only through the canonical prediction pipeline and shall fail closed when frozen adapters are not identity-verifiable.

#### Scenario: Canonical prediction hook path is used
- **WHEN** challenge predictions are evaluated
- **THEN** prediction runs go through `voice2task-train sft-predict` or library-equivalent `voice2task.training.run_sft_prediction_export`
- **AND** online sidecars are produced by the integrated post-parse copy-backed shadow hook
- **AND** standalone verifier scripts MUST NOT be used as the primary online-sidecar result

#### Scenario: Adapter identity is verified
- **WHEN** frozen adapter prediction is attempted
- **THEN** the report records adapter identity, base model revision, tokenizer revision, prediction config hash, prompt hash, decoding config, and policy hash
- **AND** the change MUST NOT train or modify an adapter

#### Scenario: Missing adapter blocks challenge evaluation
- **WHEN** no frozen adapter identity can be verified
- **THEN** the system writes `blocked.json` with decision `CHALLENGE_EVALUATION_BLOCKED`
- **AND** it MUST NOT fabricate predictions, train a replacement adapter, or emit a validated/generalized policy decision label

#### Scenario: Hook preserves prediction output
- **WHEN** shadow disabled, enabled with NullSink, and enabled with JsonlSink runs are compared for the same frozen prediction artifact boundary
- **THEN** primary prediction output, parsed contracts, evaluator input, exit status, runtime decision status, and V1 metrics remain unchanged
- **AND** sidecars remain separate artifacts

### Requirement: Separate online sidecars from offline correctness audits
The system SHALL keep online sidecars gold-free and compute gold correctness only in offline challenge audits after prediction and sidecar artifacts are frozen.

#### Scenario: Online sidecars remain private-safe
- **WHEN** online challenge sidecars are written
- **THEN** they default to hash-and-offset-only fields and omit full input text, span text, raw model output, raw request id, complete private prediction contract, gold fields, evaluator fields, private paths, hostnames, IPs, tokens, and real PII

#### Scenario: Offline audit joins gold after freeze
- **WHEN** evaluation audit rows are generated
- **THEN** they join frozen prediction sidecars to frozen challenge gold without mutating sidecars, predictions, gold rows, evaluator inputs, runtime decisions, or V1 metrics
- **AND** reports separately label technical source provenance and gold correctness

### Requirement: Report challenge metrics with conservative decision labels
The system SHALL publish compact challenge evidence with pipeline integrity, scope coverage, correctness, adversarial condition, Wilson interval, latency, policy-freeze, and privacy metrics.

#### Scenario: Required reports are written
- **WHEN** challenge evaluation completes or blocks
- **THEN** `reports/public-sample/copy-shadow-template-disjoint-challenge-v1/` contains only the bounded report files allowed for this change, including challenge manifest, template-disjoint audit, summary, per-scope metrics, per-condition metrics, latency benchmark, policy-freeze audit, privacy audit, recommended next change, and `blocked.json` only when blocked

#### Scenario: Technical safety gates are reported
- **WHEN** summary metrics are written
- **THEN** they include prediction run success rate, hook invocation count, sidecar attachment rate, hook error count, sink error count, policy drift count, path conflict count, contract mutation count, runtime decision delta count, prediction output hash mismatch count, V1 metric delta, provenance false accept count, silent fallback count, action trusted count, and normalized trusted count

#### Scenario: Correctness and condition metrics are reported
- **WHEN** offline audits are complete
- **THEN** they report trusted/gold-correct, trusted/gold-mismatch, untrusted/gold-correct, and neither trusted nor correct rates overall, per enabled scope, per adapter, and per condition tag
- **AND** duplicate, source-absent, normalization-collision, partial-span, action, synthetic-PII, and invalid-output high-risk false-trust or leakage counts are reported

#### Scenario: Wilson intervals are reported
- **WHEN** proportions are reported for trusted exact rate, trusted gold-correct rate, trusted gold-mismatch rate, eligible verification failure rate, and per-scope trusted rate
- **THEN** each proportion includes a 95 percent Wilson interval
- **AND** single-point estimates MUST NOT be presented as production-stable metrics

#### Scenario: Final decision is bounded
- **WHEN** all technical gates pass and overall trusted gold-correct rate is at least 0.80 with every enabled scope at least 0.70
- **THEN** the decision MAY be `FROZEN_POLICY_CHALLENGE_VALIDATED_OBSERVE_ONLY`
- **AND** the only recommended next change MUST be `prospective-copy-shadow-observation-on-future-predictions`
- **AND** runtime enforcement MUST NOT be recommended

#### Scenario: Scope limitations are explicit
- **WHEN** technical gates pass but one or more enabled scopes fall below correctness or coverage thresholds
- **THEN** the decision MUST be `FROZEN_POLICY_VALIDATED_WITH_SCOPE_LIMITATIONS` or `FROZEN_POLICY_NOT_GENERALIZED`
- **AND** the report MUST name scopes to retain, narrow, disable, or redesign in a future change without modifying the current frozen policy

#### Scenario: Unsafe or invalid challenge hard-stops
- **WHEN** technical false accepts, duplicate/source-absent/collision false-trust, action trust, normalized trust, output mutation, runtime decision delta, privacy leak, policy drift, or primary-path hook failure occurs
- **THEN** the decision MUST be `CHALLENGE_POLICY_UNSAFE_OR_INVALID`
- **AND** the system MUST NOT recommend observe deployment or enforcement

### Requirement: Publish documentation and bounded truth surface updates
The system SHALL document the challenge evaluation and update current truth surfaces without expanding project claims.

#### Scenario: Challenge documentation is added
- **WHEN** the phase completes or blocks
- **THEN** `docs/copy-shadow-template-disjoint-challenge.md` explains the challenge purpose, template-disjoint definition, freeze flow, enabled scopes, negative controls, canonical prediction pipeline, provenance/correctness split, exact-only trust, normalized candidate-only path, action exclusion, privacy defaults, frozen policy, no enforcement, no training, decision gate, and claim boundaries

#### Scenario: Current truth surfaces are concise
- **WHEN** README, README_en, CONTEXT, evidence index, and Human Brief are updated
- **THEN** they report challenge size, template-disjoint status, final decision label, overall/per-scope trusted gold-correct rates when available, high-risk false-trust counts, next bounded change, and explicit no-training/no-enforcement/no-model-improvement boundaries
- **AND** they MUST NOT present long historical narrative or unsupported production/safety claims
