## ADDED Requirements

### Requirement: Internal hybrid slot representation design
The system SHALL define an internal-only Hybrid Slot Representation V1 proposal without changing `BrowserTaskContract` V1, `ContractCoreV2`, current evaluators, current training targets, recovered predictions, gold contracts, or downstream runtime behavior.

#### Scenario: External contract remains V1
- **WHEN** the hybrid representation design is generated
- **THEN** the design states that external serialization remains `BrowserTaskContract` V1 and no schema or runtime migration occurred

### Requirement: Verifier-owned metadata boundary
The system SHALL distinguish model-authored fields from system-derived fields, and SHALL keep `representation_kind`, verified `source_span`, `normalization_rule`, `verification_status`, `provenance`, source hash, task-key validation, and fallback decision under system ownership unless a future spec explicitly narrows that boundary.

#### Scenario: Model cannot claim verified provenance
- **WHEN** the design describes Hybrid Slot Representation V1 fields
- **THEN** verified provenance and verification status are assigned to deterministic verifier output, not to trusted model-authored output

### Requirement: Source span semantics
The system SHALL define source spans as verifier-owned half-open Unicode character offsets over the original input text or fixed sanitized transcript, with `start` inclusive, `end` exclusive, and exact source-text back-slice validation before any allowlisted normalization.

#### Scenario: Copy verification uses half-open offsets
- **WHEN** a slot value is marked as verified copy-backed
- **THEN** the design requires `source_text[start:end]` to recover the verified source substring exactly

### Requirement: Evidence-driven representation matrix
The system SHALL generate a task-type / slot-path representation matrix from current authoritative evidence, covering high-frequency and high-error slot paths including `query`, `field`, `target`, `action`, `url`, `ambiguity`, and `reason`, with one primary strategy per row.

#### Scenario: Slot path receives one primary strategy
- **WHEN** the representation matrix is generated
- **THEN** each row has exactly one primary proposed representation, a verifier requirement, fallback behavior, confidence level, and evidence reference

### Requirement: Strategy taxonomy
The system SHALL define and use bounded representation strategies for `copy`, `copy_then_normalize`, `enum`, `task_schema_constrained`, `bounded_structured`, `limited_free_generation`, and `unresolved`, with unsupported cases failing closed or moving to clarification/unresolved instead of being silently repaired.

#### Scenario: Unsupported value fails closed
- **WHEN** a current prediction value cannot be verified by the selected representation strategy
- **THEN** the feasibility projection marks it as failing closed or unresolved rather than repairing it or counting it as model success

### Requirement: Offline feasibility projection
The system SHALL produce a read-only offline feasibility projection from current public-safe gold and prediction artifacts, reporting representation coverage, copy-backed coverage, copy-normalize coverage, enum/classification coverage, bounded-structured coverage, limited-free-generation coverage, unresolved rate, currently verifiable prediction rate, and currently fail-closed prediction rate.

#### Scenario: Projection preserves predictions
- **WHEN** the feasibility projection runs
- **THEN** it reads current artifacts without mutating predictions, gold contracts, datasets, evaluator behavior, or model outputs

### Requirement: Current boundary validation
The system SHALL hard-stop with `DESIGN_BLOCKED_INVALID_INPUT` and a blocked artifact when required source boundaries are invalid, including missing recovered raw inputs, failed metric reproduction, missing `MIXED_SLOT_REPRESENTATION_REQUIRED`, non-V1 external schema, changed training target, or changed internal-core responsibility.

#### Scenario: Invalid source boundary blocks design
- **WHEN** required source artifacts or boundary checks are not valid
- **THEN** the system writes a blocked artifact and does not generate success reports that imply a completed design

### Requirement: Single vertical slice recommendation
The system SHALL select exactly one primary next vertical slice and at most one fallback, and SHALL stop after the design phase without automatically implementing the slice, training, expanding data, changing schema, or building a challenge set.

#### Scenario: One next change is recommended
- **WHEN** the design report is complete
- **THEN** it names one primary next change, explains why the full hybrid system is not implemented immediately, and lists claims that remain unsupported
