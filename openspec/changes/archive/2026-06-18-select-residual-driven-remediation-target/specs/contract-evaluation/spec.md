## ADDED Requirements

### Requirement: Publish residual-driven remediation target-selection evidence
The system SHALL publish public-safe remediation target-selection evidence from
the committed layered evaluator and residual diagnosis artifacts without
changing evaluator semantics, model outputs, public-sample data, or split
boundaries.

#### Scenario: Generate remediation target selection from current artifacts
- **WHEN** committed layered-eval dev/test metrics and current residual-diagnosis dev/test artifacts exist
- **THEN** the system MUST write `summary.md`, `summary.json`, `top-failures.md`, and `recommended-next-change.md` under `reports/public-sample/remediation-target-selection/`
- **AND** the output MUST include dev/test sample counts and the current layered metrics for strict exact, executable contract pass rate, slot key F1, slot value exact F1, slot value normalized F1, route accuracy, task type accuracy, risk-level accuracy, requires-confirmation accuracy, unsafe false-negative rate, and refusal/clarify accuracy

#### Scenario: Rank residual failure families
- **WHEN** residual-diagnosis artifacts contain dev/test residual families
- **THEN** the system MUST aggregate failure-family counts across dev and test
- **AND** it MUST include each family count, residual proportion, dev/test distribution, top affected task/route/family hint when available, and public-safe sanitized examples

#### Scenario: Select bounded remediation strategies
- **WHEN** the system ranks residual families
- **THEN** it MUST map frequent failures to one of `DATA_REMEDIATION`, `SCHEMA_CANONICALIZATION`, `DETERMINISTIC_POSTPROCESSOR`, `SAFETY_REPAIR`, or `DEFER`
- **AND** it MUST select at most two next remediation targets based on count, safety risk, and impact on executable contract pass rate
- **AND** each selected target MUST include a target id, evidence count, rationale, proposed next change id, allowed operations, non-goals, expected measurable effect, and claim boundaries

#### Scenario: Preserve analysis-only boundaries
- **WHEN** remediation target-selection evidence is generated
- **THEN** it MUST state that strict exact remains the canonical diagnostic, executable contract pass is a deterministic layered metric, normalized slot metrics are diagnostic only, and this phase does not claim model improvement
- **AND** it MUST NOT train, predict, expand data, merge candidates, change train/dev/test splits, change evaluator metric definitions, relax strict exact, use an LLM judge, perform semantic equivalence scoring, repair predictions, publish checkpoints or adapters, claim held-out recovery, claim production readiness, claim safety readiness, or claim live-browser benchmark improvement

#### Scenario: Validate public-safe artifacts
- **WHEN** remediation target-selection artifacts, docs, Human Brief HTML, or archive files are prepared for commit
- **THEN** validation MUST reject raw private rows, absolute local paths, private remote paths, host details, SSH details, raw logs, tokens, secrets, checkpoints, adapters, caches, and private corpus rows
- **AND** historical layered evaluator, strict evaluator, residual diagnosis, scaled residual diagnosis, and scaled remediation target-selection artifacts MUST remain unmodified
