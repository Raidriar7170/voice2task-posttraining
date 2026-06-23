## ADDED Requirements

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
