## ADDED Requirements

### Requirement: Preserve JSON value types in strict contract exact match
The system SHALL compute future `contract_exact_match` rows only after strict schema and semantic validation by comparing complete parsed contracts with type-preserving JSON structural equality.

#### Scenario: Distinguish JSON boolean, integer, and floating-point slot values
- **WHEN** a prediction and gold contract differ only because an untyped slot value is `true`, `1`, or `1.0`
- **THEN** the evaluator MUST treat the JSON-distinct values as different and the row MUST NOT count as a strict exact match

#### Scenario: Ignore serialization-only differences
- **WHEN** a prediction and gold contract contain the same JSON values but use different object key order or insignificant serialization whitespace
- **THEN** the evaluator MUST count the row as strict exact when the existing strict schema and semantic gates also pass

#### Scenario: Compare nested objects and arrays recursively
- **WHEN** prediction and gold slot values contain nested JSON objects or arrays
- **THEN** object key order MUST be ignored, array order MUST be preserved, and every nested value MUST satisfy the same JSON type-strict comparison

#### Scenario: Fail closed outside the finite JSON domain
- **WHEN** either side contains a non-finite number or a non-JSON Python value such as a tuple or custom object
- **THEN** the row MUST NOT count as a strict exact match

#### Scenario: Preserve historical evidence
- **WHEN** the type-preserving evaluator repair is applied
- **THEN** committed historical predictions, aggregate metrics, comparison artifacts, and lockbox results MUST remain unchanged and MUST NOT be re-scored in this phase

### Requirement: Keep final lockbox evidence navigation synchronized
The system SHALL classify the completed lockbox-v1 final comparison as current evidence and preserve the earlier blocked lineage-guard phase as superseded history in every public evidence index representation.

#### Scenario: Navigate to completed final lockbox evidence
- **WHEN** a reader or checker inspects the machine-readable or Markdown evidence index
- **THEN** it MUST find a current item pointing to the aggregate-only final lockbox comparison
- **AND** the item MUST state that final SFT did not improve strict exact match under the frozen one-look protocol without making a general model-quality claim

#### Scenario: Preserve the earlier blocked phase as superseded
- **WHEN** the earlier `must-fix-phase-3-lockbox-lineage-guard` item is indexed
- **THEN** its status MUST be `SUPERSEDED`, it MUST link to the final lockbox item, and it MUST NOT remain in the Markdown blocked-runs table

#### Scenario: Reject index drift
- **WHEN** current truth-surface validation runs
- **THEN** it MUST fail if the JSON and Markdown indexes omit the final item, retain the earlier item as blocked, or break the supersession relationship

#### Scenario: Keep raw lockbox artifacts authoritative
- **WHEN** the navigation index summarizes lockbox-v1
- **THEN** `data/lockbox/lockbox-v1.manifest.json`, `reports/lockbox-v1/final-evaluation/run-card.json`, both per-arm metrics files, and `reports/lockbox-v1/final-evaluation/comparison.json` MUST remain authoritative
- **AND** any index disagreement with their frozen row/family counts, one-look status, protocol identity, or aggregate metrics MUST fail validation without rewriting the authoritative artifacts
