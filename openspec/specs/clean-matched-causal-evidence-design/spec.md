# clean-matched-causal-evidence-design Specification

## Purpose
TBD - created by archiving change preregister-clean-matched-compiler-and-model-evidence-design. Update Purpose after archive.
## Requirements
### Requirement: Design a clean family-level evaluation population without materializing it
The system SHALL define a future acquisition, lineage, family grouping, sample-size, and sealing contract without creating, selecting, annotating, reading, or scoring any clean evaluation row in this change.

#### Scenario: Keep execution bindings explicit and unbound
- **WHEN** the design bundle is generated
- **THEN** one canonical execution-binding inventory MUST contain `acquisition_source`, `acquisition_frame_version`, `semantic_family_key`, `partition_algorithm`, `partition_seed`, `strata_definition`, `target_total_family_count`, `target_partition_allocation`, `minimum_families_per_partition`, `compiler_control`, `compiler_intervention`, `model_control`, `model_training_intervention`, `paired_model_seed_list`, `compiler_effect_scale`, `model_effect_scale`, `compiler_mde_or_sensitivity_target`, `model_mde_or_sensitivity_target`, `compiler_target_power_or_beta`, `model_target_power_or_beta`, `alpha`, `compiler_family_variance_or_icc_assumption`, `model_family_variance_or_icc_assumption`, `paired_seed_correlation_assumption`, `seed_failure_or_attrition_assumption`, `compiler_interval_and_multiplicity_method`, `model_interval_and_multiplicity_method`, `guardrail_margins`, and `stop_rules`
- **AND** every canonical inventory value MUST be exactly `UNBOUND_BY_DESIGN` in this change, with no artifact-specific extension or conflicting alias
- **AND** those fields MUST block `EXPERIMENT_BINDINGS_COMPLETE`, `PROTOCOL_FROZEN`, and execution readiness

#### Scenario: Define cleanliness by lineage and independence
- **WHEN** the future clean population contract is reviewed
- **THEN** it MUST exclude ancestry from current public train/dev/test, remediation, challenge, prediction, and lockbox-v1 artifacts
- **AND** it MUST predeclare exact, normalized, template, semantic-family, and provenance disjointness checks before row creation
- **AND** merely being newly created, authored, synthetic, or chronologically later MUST NOT establish clean, natural-ASR, or independent evidence

#### Scenario: Preserve the no-row design boundary
- **WHEN** this change is proposed, applied, reviewed, or archived
- **THEN** `clean_row_creation`, `clean_row_selection`, `clean_row_annotation`, `clean_outcome_access`, and `data_mutation` MUST remain false
- **AND** no clean manifest, row file, gold label, prediction, adapter, checkpoint, or executable experiment artifact may be produced

### Requirement: Preserve two family-disjoint sealed one-look partitions
The system SHALL define `compiler_system_evaluation` and `model_learning_evaluation` partitions under one future acquisition plan, with partition mechanics frozen before acquisition and actual membership assigned by semantic family at materialization before any row authoring, annotation, gold access, or outcome access.

#### Scenario: Freeze partition mechanics before acquisition
- **WHEN** a future materialization phase is approved to acquire a population
- **THEN** the acquisition source/frame, family key, partition algorithm, random seed, strata, target allocation, target count, and minimum-size rule MUST already be bound, source-hashed, and protocol-frozen
- **AND** no row, annotation, gold label, or outcome may exist or be accessible at that point

#### Scenario: Assign actual membership only from frozen mechanics
- **WHEN** the future source-hashed acquisition frame is materialized into a family registry
- **THEN** actual family membership MUST be assigned exactly once from the frozen family key, algorithm, seed, strata, and allocation before row authoring, annotation, gold access, or outcome access
- **AND** realized counts and the membership attestation MUST be recorded as materialization evidence rather than retroactively represented as design-time bindings
- **AND** no semantic family may appear in both partitions or in training, development, remediation, or challenge inputs

#### Scenario: Consume one-look state independently
- **WHEN** the compiler partition is opened in a future experiment
- **THEN** only the compiler partition one-look state may become consumed
- **AND** the model-learning partition MUST remain sealed and ineligible for inspection, selection, tuning, or compiler-result-driven changes

#### Scenario: Block shared or post-hoc repartitioning
- **WHEN** family overlap, outcome-aware allocation, post-materialization seed/strata change, or reuse of one partition for the other estimand is detected
- **THEN** the protocol MUST fail closed before any causal claim or readiness transition

### Requirement: Keep compiler and model-learning estimands separate
The system SHALL maintain separate observation units, eligible populations, interventions, controls, outcomes, denominators, invariants, uncertainty contracts, status reasons, and claim labels for compiler/system and model-learning effects.

#### Scenario: Prevent a merged headline effect
- **WHEN** both preregistration cards are rendered
- **THEN** no shared primary delta or combined improvement headline may merge compiler-filled and model-authored outcomes
- **AND** each estimand MUST retain an independent causal-identification status

#### Scenario: Prevent attribution leakage
- **WHEN** deterministic compilation changes route, safety, confirmation, normalized command, language, version, semantic validity, or compiled V1 exact
- **THEN** the change MUST be labeled a system/compiler transformation effect or negative-control movement
- **AND** it MUST NOT be attributed to improved model parameters

### Requirement: Preregister paired compiler arms over identical frozen raw records
The system SHALL define a compiler/system card whose observation unit is one frozen raw record and whose control and intervention consume byte-identical model output and provenance.

#### Scenario: Bind compiler control and intervention
- **WHEN** the compiler card reaches `EXPERIMENT_BINDINGS_COMPLETE`
- **THEN** the control MUST be a named identity or preserve-legacy path and the intervention MUST be one named candidate compiler
- **AND** both arms MUST preserve raw-core identity, legacy envelope metadata, row/order identity, source hashes, prompt/decoding provenance, evaluator version, and no prediction repair

#### Scenario: Keep the primary denominator full-population ITT
- **WHEN** a future compiler effect is estimated
- **THEN** the primary outcome MUST be compiled-V1 strict exact over the complete fixed eligible denominator
- **AND** invalid, renderer-unsupported, compiler-error, or missing records MUST remain primary failures
- **AND** supported-only results MUST be secondary diagnostics with their smaller denominator printed explicitly

#### Scenario: Bind guardrails and negative controls
- **WHEN** the compiler card is reviewed
- **THEN** it MUST predeclare safety, confirmation, slot, and executable guardrails
- **AND** it MUST include constant-only, field-copy-only, policy-default-only, and evaluation-plumbing negative controls
- **AND** any future effect label MUST be `system_compiler_transformation_effect`

#### Scenario: Preserve paired family-clustered compiler uncertainty
- **WHEN** a future compiler effect and interval are computed
- **THEN** each frozen raw record MUST contribute one paired within-record arm contrast before contrasts are aggregated within semantic family
- **AND** the interval or randomization method MUST preserve family clustering and its predeclared multiplicity policy
- **AND** rows from the same semantic family MUST NOT be treated as independent samples

### Requirement: Preregister matched multi-seed model-learning arms
The system SHALL define a model-learning card whose observation unit is one preregistered evaluation family and whose primary outcomes cover only model-authored fields.

#### Scenario: Bind exactly one model intervention
- **WHEN** the model card is evaluated for completeness
- **THEN** it MUST name exactly one training intervention and one matched control
- **AND** if prompt, output schema, decoder, compiler policy, evaluator, data boundary, optimization budget, or eligible evaluation population differ beyond that intervention, model-learning identification MUST remain blocked as a bundled pipeline comparison

#### Scenario: Match arms and paired seeds
- **WHEN** a future model experiment is declared ready
- **THEN** both arms MUST share data boundary, prompt, decoding, compiler policy, evaluator version, optimization budget, eligible evaluation population, and a frozen list of at least three paired seeds
- **AND** every assigned seed MUST remain in the primary seed-level ITT denominator, with missing, failed, or invalid arm results assigned a predeclared failure code rather than deleted, replaced, or rerun selectively
- **AND** aggregation MUST proceed within family for each assigned seed and then pair the same assigned seed list across arms with failure-coded seeds retained

#### Scenario: Restrict model outcomes to model-authored fields
- **WHEN** primary model-learning outcomes are selected
- **THEN** compiler-filled constants, route, safety, confirmation, normalized command, language, version, and compiled full-V1 exact MUST NOT serve as primary evidence that model parameters improved
- **AND** any pipeline-level metric MUST be reported separately with its compiler contribution identified

### Requirement: Predeclare sample size and hierarchical uncertainty
The system SHALL bind sample-size/MDE methodology and uncertainty calculations before any clean outcome is accessible.

#### Scenario: Freeze sensitivity planning before outcomes
- **WHEN** a future population size is chosen
- **THEN** compiler and model contracts MUST separately bind effect scale, MDE or sensitivity target, target power or beta, alpha, family-level variance or ICC assumptions, interval method, multiplicity policy, guardrail margins, and stop rules from pre-outcome assumptions or historical aggregate-only evidence
- **AND** the model contract MUST additionally bind paired-seed correlation and seed failure/attrition assumptions
- **AND** clean outcomes MUST NOT be used to resize, repartition, or select the population

#### Scenario: Respect family and seed dependence
- **WHEN** model-learning uncertainty is computed
- **THEN** aggregation order, interval method, multiplicity policy, family clustering, and paired-seed structure MUST be predeclared
- **AND** all-assigned-seed failure coding MUST be applied before aggregation without deleting incomplete seeds
- **AND** repeated rows within a family or repeated runs sharing a seed MUST NOT be treated as independent row-level samples

### Requirement: Enforce machine-checkable invariants, negative controls, and readiness states
The system SHALL define a fail-closed lifecycle and machine checks for every transition toward a future one-look execution.

#### Scenario: Limit this change to design-only state
- **WHEN** this change completes
- **THEN** its status MUST be exactly `evidence_status=DESIGN_ONLY`, `decision=PREREGISTRATION_DESIGN_READY_EXECUTION_BLOCKED`, `design_contract_status=REVIEWED_DESIGN_ONLY`, `protocol_freeze_status=NOT_FROZEN`, `clean_population_status=NOT_MATERIALIZED`, `experiment_preregistration_status=NOT_EXECUTABLE`, and `execution_readiness=false`
- **AND** compiler and model-learning causal identification MUST remain `CAUSAL_IDENTIFICATION_BLOCKED`

#### Scenario: Advance through the lifecycle in order
- **WHEN** a later phase requests a readiness transition
- **THEN** it MUST advance in order through `DESIGN_ONLY`, `EXPERIMENT_BINDINGS_COMPLETE`, `PROTOCOL_FROZEN`, `POPULATION_MATERIALIZED_AND_SEALED`, `ARM_ARTIFACTS_FROZEN`, and `ELIGIBLE_FOR_ONE_LOOK`
- **AND** no state may be skipped or inferred from document presence alone

#### Scenario: Fail closed on invariant violations
- **WHEN** required bindings are missing or lineage ambiguity, partition-family overlap, hash drift, early outcome access, arm mismatch, seed loss, prediction repair, unsupported-case filtering, or one-look reuse is detected
- **THEN** readiness advancement MUST stop with machine-readable reasons
- **AND** no causal effect, clean-evidence, model-improvement, or execution-readiness claim may be emitted

### Requirement: Publish a deterministic public-safe design bundle
The system SHALL publish deterministic JSON and Markdown design evidence plus a Chinese Human Brief from an explicit public-safe source whitelist.

#### Scenario: Bind design evidence to authoritative sources
- **WHEN** the design bundle is generated
- **THEN** it MUST record methodology version, source paths/hashes, clean acquisition and partition schema, both preregistration cards, bound/unbound fields, lifecycle state, invariants, negative controls, uncertainty contract, status reasons, execution scope, and claim flags
- **AND** byte-identical regeneration MUST be verified

#### Scenario: Preserve aggregate-only and private-artifact boundaries
- **WHEN** the design helper reads current evidence
- **THEN** it MAY read only explicitly whitelisted public-safe source and aggregate status artifacts
- **AND** it MUST NOT read lockbox rows, drafts, row failures, raw/private predictions, private corpora, caches, adapters, checkpoints, raw logs, secrets, host details, or private paths

#### Scenario: Keep all execution and claim flags false
- **WHEN** JSON, Markdown, navigation, tests, or the Human Brief describe this design
- **THEN** `clean_row_creation`, `clean_row_selection`, `clean_row_annotation`, `clean_outcome_access`, `compiler_implementation`, `decoder_implementation`, `training_run`, `prediction_run`, `a100_execution`, `data_mutation`, `prompt_change`, `schema_change`, `evaluator_change`, `runtime_change`, `lockbox_row_level_read`, and `experiment_execution` MUST be false
- **AND** model improvement, executable improvement, natural-ASR generalization, checkpoint/adapter release, production readiness, safety readiness, and live-browser benchmark claims MUST be false

### Requirement: Recommend exactly one materialization-and-freeze phase without executing it
The system SHALL recommend one bounded next phase only after the design contract passes review, without creating data or running either experiment.

#### Scenario: Route to independent population materialization
- **WHEN** the design decision is `PREREGISTRATION_DESIGN_READY_EXECUTION_BLOCKED`
- **THEN** the only next recommendation MUST be `materialize-and-freeze-clean-compiler-model-evaluation-boundary-v1`
- **AND** that recommendation MUST be marked unexecuted and separately reviewable
- **AND** this change MUST NOT acquire rows, open outcomes, implement a compiler/decoder, launch training/prediction, run A100, or reuse lockbox-v1
