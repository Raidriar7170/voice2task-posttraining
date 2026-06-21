## ADDED Requirements

### Requirement: Merge scaled clarify slot-boundary candidates into the formal public sample
The system SHALL support a guarded formal merge of reviewed scaled clarify
slot-boundary candidate seeds into the committed public sample while preserving
clarify contract shape, candidate provenance, split labels, synchronized
derived artifacts, and comparison-boundary warnings.

#### Scenario: Promote reviewed scaled clarify candidates exactly once
- **WHEN** the merge command runs with the current formal public seed file and
  `scaled_clarify_slot_boundary_seed_candidates.jsonl`
- **THEN** it MUST validate exactly 9 reviewed scaled clarify candidate seed
  rows
- **AND** it MUST reject missing, extra, duplicate, already-formal, unreviewed,
  non-public-safe, non-standalone, or non-clarify candidate rows before
  rewriting formal public sample artifacts
- **AND** each promoted seed MUST preserve `task_type="clarify"`,
  `route="clarify"`, `safety.allow=true`,
  `safety.reason="ambiguous_request"`, `confirmation_required=true`, and a
  non-empty `slots.ambiguity`
- **AND** each promoted seed MUST use formal-public-sample provenance that
  retains the candidate design theme, materialization source artifact, and
  candidate source artifact
- **AND** each promoted seed MUST preserve its reviewed `train`, `dev`, or
  `test` split label

#### Scenario: Rebuild synchronized formal clarify artifacts
- **WHEN** scaled clarify candidates are promoted into the formal public sample
- **THEN** the system MUST rebuild `seed_traces.jsonl`,
  `sft_public_sample.jsonl`, `dpo_public_sample.jsonl`, and
  `manifest_public_sample.json` from the updated formal seed file
- **AND** the rebuilt manifest MUST record the previous manifest id, the new
  manifest id, pre-merge counts, post-merge counts, candidate seed counts,
  candidate SFT row counts, DPO pair counts, split counts, and source material
  identity
- **AND** the derived artifacts MUST validate through the public dataset
  validator

#### Scenario: Publish scaled clarify merge evidence
- **WHEN** the scaled clarify merge completes
- **THEN** the system MUST publish JSON, Markdown, and manifest evidence under
  `reports/public-sample/scaled-clarify-slot-boundary-public-sample-merge/`
- **AND** the evidence MUST record pre-merge counts, post-merge counts,
  candidate seed/SFT/DPO contributions, validation status, execution scope,
  claim boundaries, and candidate source identity
- **AND** the evidence MUST include public-safe leak-scan results or a linked
  public-safe leak-scan artifact

#### Scenario: Preserve comparison and claim boundaries
- **WHEN** merge evidence, reports, manifests, tests, or Human Briefs describe
  the scaled clarify formal merge
- **THEN** they MUST state that the formal public sample boundary changed and
  old metrics are not directly comparable
- **AND** they MUST state that strict `contract_exact_match`, strict `slot_f1`,
  and the contract evaluation ladder remain authoritative
- **AND** they MUST state that `slot_f1_soft` is diagnostic-only
- **AND** they MUST NOT claim held-out recovery, model quality improvement,
  safety improvement, model recovery, checkpoint release, adapter release,
  production readiness, private-corpus generalization, public full-corpus
  release, or live-browser benchmark improvement
- **AND** they MUST state `training_run=false`, `prediction_run=false`,
  `a100_execution=false`, `prompt_change=false`,
  `slot_normalization=false`, `prediction_repair=false`, and
  `evaluator_metric_change=false`
