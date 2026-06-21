## ADDED Requirements

### Requirement: Current Snapshot Documentation
The repository SHALL maintain README.md, README_en.md, and CONTEXT.md as compact
current truth surfaces for Voice2Task evidence. These documents MUST identify
the current formal sample boundary, latest model experiment conclusion, latest
Contract V2 projection conclusion, current recommended next change, and claim
boundaries without presenting historical or superseded metrics as current.

#### Scenario: Current docs reflect latest evidence
- **WHEN** a reviewer opens README.md, README_en.md, or CONTEXT.md
- **THEN** the document exposes the latest formal data boundary and current
  evidence conclusion while explicitly forbidding model-improvement,
  executable-quality, production-readiness, safety-readiness, held-out recovery,
  live-browser, checkpoint, adapter-release, DPO, and canonical-candidate-loop
  claims unless later evidence explicitly supports them

### Requirement: Evidence Index Classification
The repository SHALL provide a unified public-sample evidence index that
classifies evidence entries using only CURRENT, HISTORICAL, SUPERSEDED, BLOCKED,
DESIGN_ONLY, RAW_INPUT, or ARCHIVED. Each indexed entry MUST include a
repo-relative path, a concise conclusion or summary, a current-claim permission
flag, and supersession metadata when applicable.

#### Scenario: Evidence statuses are machine-checkable
- **WHEN** the evidence index is validated
- **THEN** every indexed path exists, every status belongs to the allowed set,
  CURRENT entries are not blocked-only artifacts, SUPERSEDED entries include a
  supersession target or explanation, BLOCKED entries do not declare current
  model metrics, and DESIGN_ONLY entries do not declare model improvement

### Requirement: Evidence Surface Consistency Check
The repository SHALL include a lightweight consistency check that validates
README/CONTEXT current metrics against the latest Contract V2 projection summary
and formal public-sample manifest, validates evidence-index path/status rules,
validates the active OpenSpec count, and scans public artifacts for private-path
or secret leakage.

#### Scenario: Drift is caught before closeout
- **WHEN** `python scripts/check_current_truth_surface.py` runs from the repo
  root
- **THEN** it exits successfully only if README.md, README_en.md, CONTEXT.md,
  the evidence index, latest summary metrics, latest manifest counts, OpenSpec
  active-change count, and public leak checks agree with the current evidence
  boundary

### Requirement: Historical Evidence Preservation
The evidence cleanup MUST preserve raw reports, negative results, blocked
artifacts, and superseded artifacts. It MUST NOT delete, rewrite, recompute, or
merge historical metrics across manifests.

#### Scenario: Cleanup keeps prior evidence auditable
- **WHEN** a completed, blocked, or superseded phase is removed from the active
  OpenSpec root
- **THEN** its artifacts remain available through archived OpenSpec paths,
  report directories, or evidence-index entries that explain its historical,
  blocked, superseded, design-only, raw-input, or archived status
