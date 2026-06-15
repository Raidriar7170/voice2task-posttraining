## ADDED Requirements

### Requirement: Restore or regenerate the merged slot-value A100 adapter
The system SHALL support a bounded prerequisite phase that restores or
regenerates the private `a100-merged-slot-value-heldout-eval` adapter needed by
later prediction-only reruns.

#### Scenario: Prefer exact adapter restoration
- **WHEN** an existing adapter is found under the approved A100 project root
- **THEN** the system MAY restore or relink it only if it corresponds to the
  merged slot-value held-out evaluation runtime
- **AND** it MUST verify required LoRA files before treating the adapter as
  available

#### Scenario: Regenerate adapter from approved config
- **WHEN** no reusable adapter exists
- **THEN** the system MAY run the existing merged slot-value SFT config with
  `allow_heavy_training=true`, dataset manifest
  `public-sample-20260615T040231Z`, and train split only
- **AND** it MUST keep all generated adapter, cache, log, and temporary outputs
  under `<approved_remote_root>`

#### Scenario: Preserve prerequisite boundary
- **WHEN** the adapter restore/regeneration phase completes
- **THEN** it MUST NOT claim new prediction metrics, model recovery, release
  readiness, private-corpus generalization, or live-browser benchmark
  improvement
