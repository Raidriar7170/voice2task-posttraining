# clean-compiler-model-evaluation-boundary Specification

## Purpose
Define the fail-closed operational contract for binding, freezing, materializing, atomically sealing, and publicly attesting a clean metadata-only compiler/model evaluation boundary without creating evaluation rows or running experiments.

## Requirements
### Requirement: Bind the exact canonical execution inventory before protocol freeze
The system SHALL require one authoritative typed dossier containing exactly the 29 canonical execution bindings from the reviewed clean-matched design before it advances beyond `DESIGN_ONLY`.

#### Scenario: Accept only a complete concrete binding dossier
- **WHEN** the binding dossier is evaluated for `EXPERIMENT_BINDINGS_COMPLETE`
- **THEN** it MUST contain exactly `acquisition_source`, `acquisition_frame_version`, `semantic_family_key`, `partition_algorithm`, `partition_seed`, `strata_definition`, `target_total_family_count`, `target_partition_allocation`, `minimum_families_per_partition`, `compiler_control`, `compiler_intervention`, `model_control`, `model_training_intervention`, `paired_model_seed_list`, `compiler_effect_scale`, `model_effect_scale`, `compiler_mde_or_sensitivity_target`, `model_mde_or_sensitivity_target`, `compiler_target_power_or_beta`, `model_target_power_or_beta`, `alpha`, `compiler_family_variance_or_icc_assumption`, `model_family_variance_or_icc_assumption`, `paired_seed_correlation_assumption`, `seed_failure_or_attrition_assumption`, `compiler_interval_and_multiplicity_method`, `model_interval_and_multiplicity_method`, `guardrail_margins`, and `stop_rules`
- **AND** every binding MUST record a concrete typed value, unit when applicable, public-safe authority label, authority/source hash, derivation method and input hashes when derived, applicability statement, no-clean-row/gold/outcome/lockbox-row-access attestation, and review verdict
- **AND** null, aliases, conflicting duplicates, private paths, `UNBOUND_BY_DESIGN`, `UNBOUND`, `TBD`, `UNKNOWN`, or blocked sentinels MUST cause `BINDING_INCOMPLETE_OR_PLACEHOLDER` and keep the current state at `DESIGN_ONLY`

#### Scenario: Keep protocol identities separate from executable arm artifacts
- **WHEN** compiler and model arm identities are bound
- **THEN** they MUST name immutable control/intervention protocol definitions with source hashes, exactly one model-training intervention, and one identical paired-seed list across model arms
- **AND** the paired-seed list MUST contain at least three assigned seeds while allowing the frozen power contract to require more
- **AND** binding those definitions MUST NOT set `arm_artifacts_status` to frozen or make either experiment executable

### Requirement: Accept only an independently attested metadata-only source frame
The system SHALL require an explicitly supplied, source-hashed, independently authorized family-level sampling frame that excludes ancestry from current public train/dev/test, remediation, challenge, prediction, and lockbox-v1 row content.

#### Scenario: Block when the clean acquisition source is absent or unverifiable
- **WHEN** no source contract, authority, expected frame hash, or ancestry attestation can be verified
- **THEN** the phase MUST emit `ACQUISITION_SOURCE_UNAVAILABLE_OR_UNVERIFIABLE`
- **AND** it MUST remain at `DESIGN_ONLY` without substituting public, challenge, remediation, prediction, synthetic convenience, or lockbox-v1 data

#### Scenario: Enforce an explicit private source path policy before reads
- **WHEN** a source attestation or frame path is supplied
- **THEN** the materializer MUST accept it only below `data/local-private/clean-compiler-model-evaluation-boundary-v1/`, open relative to a trusted root descriptor with component-safe `openat`-style operations and final `O_NOFOLLOW`, verify the opened identity with `fstat`, require a regular file with `st_nlink=1`, and enforce frozen byte/record limits
- **AND** hashing and schema validation MUST use one bytes snapshot read once from the same verified descriptor, while parent replacement, exchanged symlinks, hardlinks, identity drift, globbing, and directory discovery are rejected before payload use
- **AND** public-sample, lockbox, public-report, cache, adapter, checkpoint, run, and log paths MUST be rejected by exact or prefix policy before reads

#### Scenario: Reject row or outcome content in the source frame
- **WHEN** source-frame records are validated
- **THEN** each record MUST represent exactly one semantic-family candidate and be limited to a unique opaque ASCII family candidate id, source batch identity, unique source family key, frozen stratum, eligibility, coarse provenance class, ancestry-attestation digest, and unit hash
- **AND** strict JSONL parsing MUST reject duplicate or unknown keys, invalid UTF-8/BOM, non-finite numbers, invalid opaque-id grammar, trailing content, and noncanonical records; `unit_hash` MUST cover the canonical record with `unit_hash` removed
- **AND** any input text, audio, transcript, annotation, gold, target contract, prediction, metric, outcome, free-form note, or private-path field MUST mark the acquisition compromised with `EARLY_ROW_GOLD_OR_OUTCOME_ACCESS`, prevent registry creation, and prohibit correction/retry under the same source contract or expected frame digest

### Requirement: Freeze one deterministic protocol before family materialization
The system SHALL freeze a canonical protocol covering all bindings, the source contract and frame hash, schemas, lifecycle, partition mechanics, compiler/model cards, statistical assumptions, invariants, privacy policy, and hard stops before creating a family registry or partition membership.

#### Scenario: Create a reproducible protocol freeze
- **WHEN** all 29 bindings and the metadata-only source preflight pass
- **THEN** canonical protocol serialization MUST use a frozen strict UTF-8 JSON encoding with sorted keys, no duplicate/unknown keys, no non-finite numbers, integers or canonical decimal strings for numeric values, no insignificant whitespace, and no runtime wall-clock value in reproducibility bytes
- **AND** it MUST render byte-identically on repeated runs and produce one `protocol_sha256`
- **AND** only then may the lifecycle advance from `EXPERIMENT_BINDINGS_COMPLETE` to `PROTOCOL_FROZEN`
- **AND** document presence or a partially populated manifest MUST NOT imply either state

#### Scenario: Freeze before the first source-frame payload open
- **WHEN** the source contract is preflighted before protocol freeze
- **THEN** only the independently reviewed contract/attestation and its declared expected frame digest may be validated; the frame payload MUST NOT be opened or decoded
- **AND** only after `PROTOCOL_FROZEN` may the payload be opened for the first time, and its one-snapshot actual digest MUST equal the frozen expected digest before record decoding or registry staging

#### Scenario: Reject in-place changes after freeze
- **WHEN** any frozen binding, source/frame hash, schema, partition algorithm, seed, strata, allocation, minimum, statistical assumption, guardrail, or stop rule changes
- **THEN** the existing protocol MUST fail with `PROTOCOL_FREEZE_HASH_DRIFT`
- **AND** the system MUST require a new protocol version and separately reviewed change rather than overwrite, repair, or silently regenerate the frozen protocol

### Requirement: Freeze defensible pre-outcome power and uncertainty contracts
The system SHALL bind separate compiler and model statistical dossiers without using clean outcomes or treating spent aggregate evidence as clean dependence estimates.

#### Scenario: Choose exactly one planning mode for each estimand
- **WHEN** compiler or model sample-size planning is frozen
- **THEN** its dossier MUST select exactly one of `EFFECT_TARGETED` with a predeclared meaningful MDE or `CAPACITY_CONSTRAINED` with independently available source capacity
- **AND** the dossier MUST NOT optimize both MDE and capacity or use clean outcomes to resize, top up, repartition, select, or tune the population
- **AND** an ambiguous or incomplete mode MUST cause `POWER_ASSUMPTION_UNSUPPORTED`

#### Scenario: Preserve family and paired-seed dependence
- **WHEN** the compiler power dossier is validated
- **THEN** it MUST model paired-record contrasts, family clustering, and paired discordance or a sourced conservative finite sensitivity grid
- **AND** when the model power dossier is validated, it MUST model family-by-paired-seed hierarchy, paired-seed correlation, all-assigned-seed ITT failure coding, and seed failure/attrition assumptions
- **AND** historical public or consumed-lockbox aggregates MUST NOT be represented as point estimates of clean-family ICC, paired discordance, paired-seed correlation, or seed failure probability
- **AND** if no defensible assumption grid or worst-case bound is available, the corresponding binding MUST remain incomplete and materialization MUST block

#### Scenario: Freeze exact-capacity and integer quota semantics
- **WHEN** `target_total_family_count` and `target_partition_allocation` are bound
- **THEN** the allocation MUST be an integer quota matrix indexed by frozen stratum and the two partition ids, with nonnegative cells and validated row, column, and overall sums equal to `target_total_family_count`
- **AND** the eligible metadata frame MUST contain exactly `target_total_family_count` unique families; both shortfall and oversupply MUST cause `INSUFFICIENT_FAMILY_COUNT_OR_STRATA`
- **AND** v1 MUST NOT down-select, delete, top up, or introduce a separate inclusion seed/algorithm

### Requirement: Materialize a private metadata-only family registry with staged lineage gates
The system SHALL create a private semantic-family metadata registry only after protocol freeze and SHALL keep unavailable row-level disjointness checks explicitly pending.

#### Scenario: Build the registry from one frozen source snapshot
- **WHEN** a frozen protocol authorizes materialization
- **THEN** the materializer MUST first open and recheck the source-frame hash, consume one immutable bytes snapshot, and deterministically produce unique opaque family identities with source-unit hash, semantic-family key, stratum, provenance class, and registry-entry hash
- **AND** record and root hashes MUST use frozen canonical JSON, stable record ordering, and versioned domain-separated, length-delimited SHA-256 inputs rather than ambiguous concatenation
- **AND** duplicate family keys, invalid eligibility/provenance, source drift, or ambiguous ancestry MUST stop with `FAMILY_REGISTRY_INVALID` or `LINEAGE_OR_LOCKBOX_ATTESTATION_FAILED`

#### Scenario: Keep row-level disjointness pending rather than fabricated
- **WHEN** no evaluation row text has been authored
- **THEN** exact, normalized, and template disjointness MUST be recorded as `PENDING_ROW_AUTHORING_GATE`
- **AND** only source/provenance ancestry and semantic-family-level checks may be reported as evaluated
- **AND** the materialized family registry MUST NOT be described as row-clean, natural-ASR evidence, or an evaluated benchmark

#### Scenario: Consume lockbox overlap only through sealed aggregate attestation
- **WHEN** lockbox-v1 ancestry exclusion is checked
- **THEN** the materializer MUST accept only a `SEALED_AGGREGATE_ATTESTATION_ONLY` that binds protocol hash, expected and actual source-frame roots, family-registry root, public lockbox manifest hash, validator implementation/version hash, separately authorized validator and reviewer approval identities/digests, comparison-category aggregate counts, `row_level_output_count=0`, and an attestation digest or signature
- **AND** missing or unauthorized identities, missing fields, digest/signature drift, nonzero overlap, or nonzero row-level output MUST cause `LINEAGE_OR_LOCKBOX_ATTESTATION_FAILED`
- **AND** the materializer MUST NOT read lockbox rows, row/member hashes, row failures, gold, or outcomes

### Requirement: Assign and seal exactly two family-disjoint partitions once
The system SHALL assign every eligible family exactly once to `compiler_system_evaluation` or `model_learning_evaluation` using the frozen algorithm, seed, strata, allocation, and minimum rules, then atomically seal both partitions without opening them.

#### Scenario: Produce deterministic exactly-once membership
- **WHEN** the frozen family registry passes lineage validation
- **THEN** partition ordering MUST use the frozen versioned domain plus length-prefixed seed, stratum, and canonical family id, and repeated assignment from identical protocol and registry bytes MUST produce identical membership and root hashes independent of filesystem or iteration order
- **AND** every eligible family MUST appear in exactly one partition, cross-partition overlap MUST equal zero, and manual reassignment, alternate-seed retry, post-hoc balancing, top-up, or family deletion MUST be rejected as `PARTITION_NONDETERMINISM_OR_OVERLAP`

#### Scenario: Enforce capacity and stratum gates before promotion
- **WHEN** candidate memberships are staged
- **THEN** realized total MUST equal the frozen target exactly and every integer stratum/partition quota and minimum-family constraint MUST pass before a canonical registry, membership, or seal is promoted
- **AND** any shortfall, oversupply, or quota mismatch MUST cause `INSUFFICIENT_FAMILY_COUNT_OR_STRATA` without promoting a partial canonical population

#### Scenario: Promote one immutable generation atomically
- **WHEN** registry, membership, seal, determinism, capacity, privacy, and zero-access checks all pass
- **THEN** all canonical private artifacts MUST be flushed inside one new staging generation directory on the same filesystem as the final canonical parent
- **AND** one directory rename MUST publish the complete immutable generation, an existing final generation MUST never be overwritten, and all seal references MUST resolve only within that generation
- **AND** failure before the directory rename MUST leave no partially canonical registry, membership, or seal

#### Scenario: Seal both one-look states without eligibility
- **WHEN** both memberships and aggregate roots reproduce and all privacy gates pass
- **THEN** the partitions MUST be atomically sealed with one-look state `SEALED_NOT_ELIGIBLE`, `access_count=0`, and `consumed=false`
- **AND** this change MUST NOT advance to `ARM_ARTIFACTS_FROZEN` or `ELIGIBLE_FOR_ONE_LOOK`

### Requirement: Enforce monotonic success and blocked terminal states
The system SHALL advance readiness only through fully verified atomic states and SHALL preserve the last valid state on failure.

#### Scenario: Publish the exact successful terminal truth surface
- **WHEN** binding, freeze, registry, lineage, capacity, assignment, privacy, and seal gates all pass
- **THEN** the terminal status MUST be `evidence_status=EVALUATION_BOUNDARY_MATERIALIZED`, `decision=POPULATION_BOUNDARY_READY_ARM_ARTIFACTS_BLOCKED`, `execution_bindings_status=COMPLETE`, `protocol_freeze_status=FROZEN`, `clean_population_status=MATERIALIZED_AND_SEALED`, `population_unit=SEMANTIC_FAMILY_METADATA_ONLY`, `current_readiness_state=POPULATION_MATERIALIZED_AND_SEALED`, and `maximum_state_this_change=POPULATION_MATERIALIZED_AND_SEALED`
- **AND** it MUST also report `clean_evaluation_rows_status=NOT_CREATED`, row-level disjointness `PENDING_ROW_AUTHORING_GATE`, `arm_artifacts_status=NOT_FROZEN`, `experiment_preregistration_status=NOT_EXECUTABLE`, `execution_readiness=false`, and both causal-identification statuses `CAUSAL_IDENTIFICATION_BLOCKED`
- **AND** `clean_independent_evidence_claim`, `row_clean_claim`, and `evaluated_benchmark_claim` MUST all be false

#### Scenario: Publish the exact S0 source or binding blocked truth
- **WHEN** the source is unavailable/unverifiable or any binding remains incomplete before freeze
- **THEN** status MUST be `evidence_status=BLOCKED`, `decision=CLEAN_EVALUATION_BOUNDARY_MATERIALIZATION_BLOCKED`, `current_readiness_state=DESIGN_ONLY`, `execution_bindings_status=INCOMPLETE`, `protocol_freeze_status=NOT_FROZEN`, `clean_population_status=NOT_MATERIALIZED`, and `boundary_integrity_status=NOT_CREATED`
- **AND** canonical registry/membership/seal created flags MUST be false, both partitions MUST be `NOT_MATERIALIZED`, both one-look states MUST be `NOT_AVAILABLE` with access=0 and consumed=false, unavailable hashes MUST be `NOT_AVAILABLE`, `boundary_reuse_allowed=false`, and `execution_readiness=false`

#### Scenario: Publish the exact S1 freeze blocked truth
- **WHEN** all bindings pass but canonical protocol freeze fails
- **THEN** status MUST be `evidence_status=BLOCKED`, `decision=CLEAN_EVALUATION_BOUNDARY_MATERIALIZATION_BLOCKED`, `current_readiness_state=EXPERIMENT_BINDINGS_COMPLETE`, `execution_bindings_status=COMPLETE`, `protocol_freeze_status=NOT_FROZEN`, `clean_population_status=NOT_MATERIALIZED`, and `boundary_integrity_status=NOT_CREATED`
- **AND** canonical registry/membership/seal created flags MUST be false, both partitions MUST be `NOT_MATERIALIZED`, both one-look states MUST be `NOT_AVAILABLE` with access=0 and consumed=false, unavailable hashes MUST be `NOT_AVAILABLE`, `boundary_reuse_allowed=false`, `new_protocol_version_required=true`, and `execution_readiness=false`

#### Scenario: Publish the exact S2 materialization or seal blocked truth
- **WHEN** the protocol is frozen but registry, lineage, capacity, assignment, privacy, or seal validation fails before atomic promotion
- **THEN** status MUST be `evidence_status=BLOCKED`, `decision=CLEAN_EVALUATION_BOUNDARY_MATERIALIZATION_BLOCKED`, `current_readiness_state=PROTOCOL_FROZEN`, `execution_bindings_status=COMPLETE`, `protocol_freeze_status=FROZEN`, `clean_population_status=NOT_MATERIALIZED`, and `boundary_integrity_status=INTACT_BLOCKED`
- **AND** canonical registry/membership/seal created flags MUST be false, both partitions MUST be `NOT_MATERIALIZED`, both one-look states MUST be `NOT_AVAILABLE` with access=0 and consumed=false, unavailable artifact hashes MUST be `NOT_AVAILABLE`, `boundary_reuse_allowed=false`, `new_protocol_and_acquisition_required=true`, and `execution_readiness=false`
- **AND** every S0, S1, and S2 blocked path MUST keep both causal-identification statuses blocked and `clean_independent_evidence_claim`, `row_clean_claim`, `evaluated_benchmark_claim`, and every performance/readiness claim false

#### Scenario: Invalidate rather than repair a compromised boundary
- **WHEN** early row/gold/outcome access, one-look access, public membership leakage, sealed-artifact drift, or experiment execution is detected
- **THEN** status MUST be `evidence_status=BLOCKED`, `decision=CLEAN_EVALUATION_BOUNDARY_MATERIALIZATION_BLOCKED`, `boundary_integrity_status=COMPROMISED`, `boundary_reuse_allowed=false`, and reason `ONE_LOOK_OR_EXPERIMENT_SCOPE_BREACH` or `SEALED_ARTIFACT_DRIFT_OR_MEMBERSHIP_LEAK`
- **AND** current state, binding/protocol/population status, artifact-created flags, and one-look state/access_count/consumed MUST reflect the observed facts rather than inherit success or zero-access defaults
- **AND** it MUST NOT be repaired, rehashed, repartitioned, corrected, or reused; a new independent acquisition and separately reviewed protocol are required, and every performance/readiness claim remains false

### Requirement: Publish aggregate-only evidence with truthful mutation and claim flags
The system SHALL keep all source-frame, family, and membership records private while publishing deterministic aggregate-only evidence and an explicit no-experiment boundary.

#### Scenario: Separate public evidence from private membership
- **WHEN** success or blocked evidence is generated
- **THEN** public artifacts MUST exist only under `reports/public-sample/clean-compiler-model-evaluation-boundary-v1/` and be limited to versioned domain-separated protocol/source/registry/membership root hashes, aggregate total/partition/stratum/provenance counts, violation counts, lifecycle states, blocked reasons, and execution/claim flags
- **AND** a hash unavailable on a blocked path MUST be represented as `NOT_AVAILABLE`, never null, empty text, or a fabricated digest
- **AND** public artifacts MUST NOT contain private paths, opaque member ids, per-member hashes, membership lists, row text, audio, transcript, annotation, gold, prediction, outcome, secret, host detail, or raw log
- **AND** deterministic regeneration, HTML-link validation, and public leak scanning MUST pass before the evidence is current

#### Scenario: Report materialization mutation without widening execution scope
- **WHEN** a successful private family registry and membership are sealed
- **THEN** `boundary_materialization`, `private_family_registry_created`, and `private_partition_membership_created` MUST be true
- **AND** `public_data_mutation`, `formal_training_data_mutation`, `lockbox_mutation`, `clean_evaluation_row_creation`, `gold_access`, `outcome_access`, `prediction_run`, `training_run`, `a100_execution`, `experiment_execution`, and one-look access MUST remain false
- **AND** `clean_independent_evidence_claim`, `row_clean_claim`, `evaluated_benchmark_claim`, model improvement, compiler effect, executable improvement, natural-ASR generalization, checkpoint/adapter release, production readiness, safety readiness, and live-browser benchmark claims MUST remain false

#### Scenario: Preserve the existing evidence-index classification vocabulary
- **WHEN** the phase publishes its final evidence-index entry
- **THEN** a successful sealed boundary MUST use evidence-index status `CURRENT` and a blocked phase MUST use evidence-index status `BLOCKED`
- **AND** the entry MUST preserve the phase-specific internal report status and exact decision without adding a new evidence-index status value
