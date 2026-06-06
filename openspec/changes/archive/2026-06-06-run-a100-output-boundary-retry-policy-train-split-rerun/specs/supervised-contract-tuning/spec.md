## ADDED Requirements

### Requirement: Run A100 output-boundary retry-policy train-split rerun
The system SHALL support a bounded, explicitly authorized A100 prediction-only train-split rerun after output-boundary and retry-prompt policy repair, while keeping all private runtime artifacts outside git.

#### Scenario: Launch output-boundary retry-policy rerun
- **WHEN** a developer launches the rerun with A100 authorization, a repo-external private override, an idle A100 GPU, and an approved private output root represented in public artifacts as `<a100_project_root>`
- **THEN** the system MUST use `prediction_split=train`, `overfit_diagnostic=true`, `generalization_claim=false`, `schema_repair_applied=false`, `schema_retry_enabled=true`, and generate private-adapter predictions plus public-safe prompt snapshot, raw decoded summary, generation trace, and prediction metadata sidecars

#### Scenario: Record output-boundary and retry-prompt policy visibility
- **WHEN** prediction metadata or prompt snapshots are generated for the rerun
- **THEN** they MUST record that single-root JSON object guidance, no-premature-root-close guidance, whole-object boundary guidance, public-readonly `task_type="search"` not `search_web` guidance, and retry JSON-only guidance are visible

#### Scenario: Reject unresolved or accidental execution
- **WHEN** the rerun command is launched without explicit prediction opt-in, with unresolved template paths, without a configured private adapter path, outside the approved output root, or without explicit GPU placement
- **THEN** the system MUST NOT load private model artifacts or start remote prediction and MUST report that no private adapter rerun occurred

#### Scenario: Keep private A100 artifacts private
- **WHEN** the real rerun completes or fails
- **THEN** raw logs, checkpoints, adapters, caches, private overrides, host details, SSH details, private paths, tokens, and private corpus rows MUST remain outside committed artifacts

#### Scenario: Preserve diagnostic model output
- **WHEN** the private adapter emits schema-invalid, truncated, non-JSON, JSON-fragment, prose-wrapped, contract-like but wrong, or strict-string-mismatched output
- **THEN** the prediction artifact and sidecars MUST preserve sanitized model evidence without replacing it with fixture-mode, rule-baseline, gold-contract predictions, semantic-equivalence labels, slot-normalized fields, parser-relaxed outputs, or repaired strings
