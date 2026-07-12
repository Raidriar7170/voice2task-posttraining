## ADDED Requirements

### Requirement: Audit formal public split contamination deterministically
The system SHALL produce public-safe deterministic JSON and Markdown evidence that audits the committed formal public seed and SFT split boundary without changing the input artifacts.

#### Scenario: Report cross-split lexical and target overlap
- **WHEN** the audit reads public train, dev, and test rows
- **THEN** it MUST report train-versus-dev/test counts for exact input overlap, complete target-contract overlap, `normalized_command` overlap, slots overlap, and structural contract overlap
- **AND** findings and examples MUST be deterministically sorted and sanitized

#### Scenario: Report template and provenance contamination
- **WHEN** digit-normalized seed templates span more than one split or train-row provenance resolves to a dev/test source row, family, or declared source split
- **THEN** the audit MUST report the affected signature or row counts, the explicit heuristic/methodology version, and the clean-split gate failure

#### Scenario: Version and bind the complete audit evidence
- **WHEN** JSON and Markdown audit artifacts are generated
- **THEN** they MUST record the methodology version, repo-relative paths and hashes for seed, SFT, DPO, and manifest inputs, input validation, split/input counts, deterministic zero-gate counts, diagnostic overlap counts, `historical_rows_mutated=false`, and `historical_metrics_rescored=false`
- **AND** regeneration MUST be independent of the caller's current working directory

#### Scenario: Reject invalid audit inputs while preserving evidence
- **WHEN** seed/SFT inputs are empty, omit train/dev/test, use an unknown split, contain duplicate IDs, or violate required row/object shapes
- **THEN** input validation and the clean gate MUST fail, the CLI MUST exit non-zero even in observation mode, and deterministic JSON/Markdown invalid-input evidence MUST still be written

#### Scenario: Publish diagnostic limitations
- **WHEN** the audit report is generated
- **THEN** it MUST state that lexical/template/provenance checks do not establish semantic independence, real-ASR provenance, or model quality

#### Scenario: Preserve committed data and metrics
- **WHEN** the audit runs on the current formal public sample
- **THEN** it MUST NOT mutate seed, SFT, DPO, manifest, prediction, evaluator-history, training, or lockbox artifacts

### Requirement: Fail closed before a future independent split claim
The system SHALL expose an explicit clean-split enforcement mode for future data boundaries that are intended to support an independent held-out claim.

#### Scenario: Reject a contaminated future boundary
- **WHEN** clean-split enforcement finds any exact-input overlap, digit-normalized template spanning splits, or train provenance resolving to dev/test
- **THEN** the command MUST exit non-zero and MUST identify the failed checks without rewriting the dataset

#### Scenario: Keep shared labels diagnostic-only
- **WHEN** complete target, `normalized_command`, slots, or structural-contract signatures repeat across splits without an exact-input, digit-template, or provenance violation
- **THEN** the audit MUST report those diagnostic counts but MUST NOT fail the clean gate solely because task labels or ontology structure repeat

#### Scenario: Accept a clean family-disjoint fixture
- **WHEN** clean-split enforcement receives rows with disjoint inputs, digit-normalized templates, source references, and declared source splits
- **THEN** it MUST report the clean gate as passed and exit successfully

### Requirement: Label the current public dev and test splits as spent development evidence
The system SHALL describe the current public dev/test splits as development-only/spent because they informed repeated diagnosis and remediation, while keeping lockbox-v1's frozen aggregate evaluation boundary distinct.

#### Scenario: Audit the current formal boundary
- **WHEN** the audit reads manifest `public-sample-20260619T090925Z` with 696 SFT rows and train/dev/test counts 282/207/207
- **THEN** it MUST set the clean gate to failed and the evidence status to `DEVELOPMENT_ONLY_SPENT`
- **AND** the committed seed, SFT, DPO, and manifest file hashes MUST remain unchanged

#### Scenario: Describe current public split evidence
- **WHEN** README, current status, CONTEXT, the evidence index, or the split audit describes the current 282/207/207 boundary
- **THEN** it MUST NOT call public dev/test blind, independent, leakage-free, or final-generalization evidence
- **AND** it MUST state that historical artifacts and metrics remain preserved rather than being invalidated or recomputed

#### Scenario: Preserve lockbox interpretation
- **WHEN** documentation distinguishes public dev/test from lockbox-v1
- **THEN** it MUST keep lockbox-v1 as one-look frozen aggregate evidence and MUST NOT infer row-level failure causes, natural-ASR generalization, or an overall SFT causal effect from it
