## ADDED Requirements

### Requirement: Bind a deterministic public train-only SFT artifact
The public-sample builder SHALL emit a dedicated canonical JSONL artifact containing exactly the ordered subsequence of generated SFT rows whose split is `train`, without rewriting row content or provenance, and SHALL bind its repo-relative path, final-byte SHA-256, exact row count, split declaration, and canonical-JSONL declaration inside the public manifest.

#### Scenario: Build a train-only derivative
- **WHEN** a developer runs the canonical public-sample builder
- **THEN** the builder writes `sft_train_public_sample.jsonl` using the same canonical row serialization as the mixed SFT artifact
- **AND** every dedicated row has `split="train"`
- **AND** the dedicated rows equal the mixed artifact's ordered train subsequence exactly
- **AND** only the canonical formal output records `data/public-samples/sft_train_public_sample.jsonl`
- **AND** every non-formal output, whether repo-internal or external, records the manifest-relative basename

#### Scenario: Bind current formal train rows
- **WHEN** the current formal public sample is materialized
- **THEN** the dedicated artifact contains exactly 282 non-empty uniquely identified train rows
- **AND** the manifest binds the artifact path, SHA-256, row count, split, and canonical-JSONL facts

### Requirement: Validate train-only artifact integrity fail closed
Dataset validation MUST fail closed when a manifest contains either a train-only artifact path or train-only integrity metadata unless both are present and match one safe canonical artifact.

Ordinary formal validation with `public=True` MUST require both binding halves even when both are absent. Explicit local/legacy validation with `public=False` MAY accept double absence for historical compatibility, but MUST reject a partial binding.

#### Scenario: Validate a bound train-only artifact
- **WHEN** the path is relative and contained, no path component is a symlink, the final bytes match the bound SHA-256 and canonical JSONL encoding, the row count matches, IDs are non-empty and unique, every split is train, and rows equal the mixed train subsequence
- **THEN** train-only artifact validation succeeds and reports the verified train-row count
- **AND** resolution uses the exact canonical manifest identity to distinguish formal repo-relative references from non-formal manifest-relative basenames

#### Scenario: Reject path or identity drift
- **WHEN** the path is absolute, contains traversal or backslashes, resolves outside its allowed root, includes a symlink component, is missing, or its bytes do not match the bound SHA-256
- **THEN** validation fails without accepting an alternate artifact
- **AND** a non-formal manifest cannot select the repo root merely by supplying a `data/public-samples/` prefix

#### Scenario: Reject content drift
- **WHEN** the artifact contains a non-train row, blank or duplicate ID, wrong row count, non-canonical bytes, reordered rows, changed content, or changed provenance
- **THEN** validation fails without silently filtering or repairing the artifact

#### Scenario: Reject public binding downgrade
- **WHEN** formal validation runs with `public=True` and both the train-only path and integrity metadata are absent
- **THEN** validation fails instead of treating the manifest as an unbound historical artifact
- **AND** explicit `public=False` local/legacy validation may accept the same double absence
- **AND** either mode rejects either binding half appearing alone

### Requirement: Preserve formal population and historical evidence identities
Train-only materialization MUST remain a derivative artifact-set extension and MUST NOT change the formal seed, mixed SFT, DPO, row population, split assignment, manifest ID, generated-at timestamp, historical report bytes, or clean-evaluation truth fields.

#### Scenario: Materialize the current derivative
- **WHEN** the 282-row train-only artifact is added to the current formal manifest
- **THEN** two independent temporary builds produce identical train artifact bytes
- **AND** regenerated mixed SFT and DPO bytes equal their committed counterparts
- **AND** current counts remain 696 SFT rows with train/dev/test counts 282/207/207

#### Scenario: Preserve a prior manifest hash
- **WHEN** the live manifest bytes change only to bind the new derivative artifact
- **THEN** historical audit readers that froze the prior manifest SHA resolve the exact prior bytes from an immutable hash-named snapshot
- **AND** historical expected hashes and historical report outputs remain unchanged

#### Scenario: Synchronize current split evidence without rewriting history
- **WHEN** the live manifest gains the train-only binding
- **THEN** the CURRENT split-integrity JSON and Markdown bind the new live manifest hash while retaining the prior diagnostic conclusion and `DEVELOPMENT_ONLY_SPENT` status
- **AND** historical audit readers resolve the exact prior split-integrity summary bytes from an immutable hash-named snapshot

#### Scenario: Preserve non-readiness truth
- **WHEN** materialization completes
- **THEN** clean-evaluation acquisition, authoritative-binding count, human acceptance, protocol freeze, population materialization, freeze authorization, and execution readiness remain unchanged
- **AND** no training, prediction, evaluation, or model-improvement status is emitted

## MODIFIED Requirements

### Requirement: Keep public sample artifacts synchronized after seed expansion
The system SHALL regenerate public sample SFT, train-only SFT, DPO, and manifest artifacts whenever committed public seed traces change.

#### Scenario: Regenerate derived public sample artifacts
- **WHEN** `data/public-samples/seed_traces.jsonl` is expanded or edited
- **THEN** `sft_public_sample.jsonl`, `sft_train_public_sample.jsonl`, `dpo_public_sample.jsonl`, and `manifest_public_sample.json` MUST be regenerated from the same seed file
- **AND** the manifest counts MUST match the generated SFT and DPO JSONL row counts
- **AND** the manifest train-only binding MUST match the generated train-only artifact path, final-byte SHA-256, and row count
- **AND** the generated artifacts MUST remain public-safe
