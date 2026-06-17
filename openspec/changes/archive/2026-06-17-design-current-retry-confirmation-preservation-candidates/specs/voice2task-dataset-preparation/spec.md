## ADDED Requirements

### Requirement: Design current-retry confirmation-preservation candidates before materialization
The system SHALL publish a public-safe candidate-design artifact for
current-retry confirmation-preservation before modifying public sample seeds,
generating derived rows, or launching additional training.

#### Scenario: Derive candidates from trade-off diagnosis
- **WHEN** current SFT retry trade-off diagnosis evidence is available
- **THEN** the candidate design MUST identify source rows where confirmation
  regressed between the current-manifest baseline and the current-train-split
  retry
- **AND** each candidate family MUST record source row ids, source split,
  source task family, support counts, accepted target sketch, rejected drift
  sketches, and suggested public-safe utterance templates

#### Scenario: Preserve unsafe-payment confirmation target shape
- **WHEN** candidate design covers unsafe payment rows whose accepted target
  requires confirmation
- **THEN** accepted target sketches MUST preserve `task_type="blocked"`,
  `route="deny"`, `safety.allow=false`, `safety.reason="unsafe_payment"`,
  and `confirmation_required=true`
- **AND** rejected drift sketches MUST include variants that drop confirmation,
  allow the request as `form_fill/fill_form`, or otherwise weaken the unsafe
  payment denial target

#### Scenario: Preserve public navigation non-confirmation target shape
- **WHEN** candidate design covers public-readonly navigation rows whose
  accepted target does not require confirmation
- **THEN** accepted target sketches MUST preserve `task_type="navigate"`,
  `route="open_url"`, `safety.allow=true`, `safety.reason="public_readonly"`,
  and `confirmation_required=false`
- **AND** rejected drift sketches MUST include variants that drift toward
  `clarify/clarify`, require confirmation, or change the accepted canonical URL

#### Scenario: Keep design separate from data mutation
- **WHEN** confirmation-preservation candidate design evidence is published
- **THEN** it MUST state that no public seed rows, SFT rows, DPO pairs,
  manifest files, local/private corpora, prompts, evaluator metrics,
  predictions, checkpoints, or adapters were modified
- **AND** it MUST NOT claim model recovery, held-out recovery, safety
  improvement, production readiness, private-corpus generalization, or
  live-browser benchmark improvement

#### Scenario: Recommend a bounded next action
- **WHEN** the candidate design identifies sufficient candidate coverage
- **THEN** it MAY recommend one later bounded materialization phase
- **AND** it MUST NOT automatically materialize candidates, rebuild public
  sample artifacts, train, run DPO/GRPO, generate predictions, or change
  evaluator behavior as part of the design phase
