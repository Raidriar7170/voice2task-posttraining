## ADDED Requirements

### Requirement: Merge scaled public-sample candidates into the formal public sample
The system SHALL support a guarded formal merge of reviewed scaled
public-sample candidate seeds into the committed public sample while preserving
candidate provenance, split labels, derived artifact synchronization, and
comparison-boundary warnings.

#### Scenario: Promote reviewed scaled candidates exactly once
- **WHEN** the merge command runs with the current formal public seed file and
  `scaled_public_sample_seed_candidates.jsonl`
- **THEN** it MUST validate exactly the reviewed 138 scaled candidate seed rows
- **AND** it MUST reject missing, extra, duplicate, already-formal, unreviewed,
  non-public-safe, or non-standalone candidate rows before rewriting formal
  public sample artifacts
- **AND** each promoted seed MUST use
  `source_mode="scaled_public_sample_formal_public_seed"`,
  `candidate_status="formal_public_sample"`, and a source reference to the
  candidate seed artifact
- **AND** each promoted seed MUST preserve its reviewed `train`, `dev`, or
  `test` split label

#### Scenario: Rebuild synchronized scaled formal artifacts
- **WHEN** scaled candidates are promoted into the formal public sample
- **THEN** the system MUST rebuild `seed_traces.jsonl`,
  `sft_public_sample.jsonl`, `dpo_public_sample.jsonl`, and
  `manifest_public_sample.json` from the updated formal seed file
- **AND** the rebuilt manifest MUST record 240 seed rows, 675 SFT rows, 2046 DPO
  pairs, and SFT split counts of train 261, dev 207, and test 207
- **AND** the manifest MUST summarize scaled candidate seed/SFT counts, group
  counts, family counts, and balanced candidate seed split counts
- **AND** the derived artifacts MUST validate through the public dataset
  validator

#### Scenario: Publish scaled merge evidence
- **WHEN** the scaled merge completes
- **THEN** the system MUST publish JSON, Markdown, and manifest evidence under
  `reports/public-sample/scaled-public-sample-merge/`
- **AND** the evidence MUST record pre-merge counts, post-merge counts,
  candidate seed/SFT/DPO contributions, DPO rejection deltas, validation status,
  execution scope, claim boundaries, and candidate source identity

#### Scenario: Preserve comparison and claim boundaries
- **WHEN** merge evidence, reports, manifests, tests, or Human Briefs describe
  the scaled formal merge
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
  `slot_normalization=false`, and `evaluator_metric_change=false`
