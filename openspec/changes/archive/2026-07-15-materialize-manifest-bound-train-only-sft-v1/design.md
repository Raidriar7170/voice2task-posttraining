## Context

The formal public sample `public-sample-20260619T090925Z` contains 696 SFT rows in one mixed JSONL artifact: 282 train, 207 dev, and 207 public-test. The row order interleaves splits, so prefix extraction is unsafe. The existing public builder already constructs every SFT row once from sanitized seeds and writes canonical JSONL with sorted keys, UTF-8, and one trailing newline per row.

The user authorizes a bounded formal materializer to inspect the mixed public artifact only to generate and validate one train-only derivative. This authorization does not extend to training, prediction, evaluation, model loading, or downstream reads of dev/test. Existing clean-evaluation acquisition, binding, acceptance, freeze, population, authorization, and readiness facts remain unchanged.

## Goals / Non-Goals

**Goals:**

- Make every canonical public build emit a deterministic train-only SFT artifact.
- Bind its repo-relative path and exact byte-level integrity facts inside the public manifest.
- Prove the artifact is exactly the ordered train subsequence of the mixed SFT rows, with unchanged row objects and provenance.
- Materialize the current 282-row artifact without changing the existing seed, mixed SFT, DPO, population counts, split counts, manifest ID, or generated-at timestamp.
- Preserve historical audits that intentionally bind the old manifest bytes.

**Non-Goals:**

- No training, prediction, evaluation, A100 access, tokenizer/model load, DPO, GRPO, hyperparameter search, or metric claim.
- No consumer/curriculum rerun and no fallback from a future train-only consumer to the mixed artifact.
- No public-test, lockbox, or clean-evaluation outcome use.
- No new population, split reassignment, row rewrite, provenance rewrite, or public full-corpus release.
- No commit, push, PR, archive, merge, or release.

## Decisions

### 1. Extend the canonical builder instead of adding a second CLI

`build_public_sample_dataset` will derive `train_rows` from the already validated in-memory `rows` list, preserving order, and write `sft_train_public_sample.jsonl` with the existing canonical `write_jsonl` helper. Only output at canonical `REPO_ROOT/data/public-samples` uses `_safe_artifact_ref` and records `data/public-samples/sft_train_public_sample.jsonl`; every other build location, including repo-internal report/build directories and external temporary directories, records the manifest-relative basename. The existing `voice2task-data build-public` command remains the only build entry point.

Alternative rejected: a standalone ad hoc filter CLI. It would create a second derivation path and make it easier for a future caller to bypass canonical row construction or integrity checks.

### 2. Bind integrity through existing manifest fields

The manifest `files` mapping will add `sft_train`. `source_summary.sft_train_artifact` will bind `sha256`, `row_count`, `split="train"`, and `canonical_jsonl=true`. Reusing `source_summary` avoids a cross-repository manifest schema migration while still putting all required binding facts inside the signed manifest bytes.

The artifact SHA-256 is calculated only after final canonical bytes are written. The manifest does not contain its own SHA because that would be recursive; the current manifest hash remains an external truth-surface pin.

Alternative rejected: adding a new required top-level dataclass field. That would change every local/private and historical manifest serializer even when the new artifact is absent.

### 3. Validation is fail closed when either half of the binding is present

Ordinary formal validation with `public=True` always requires both `files.sft_train` and `source_summary.sft_train_artifact`; deleting both cannot downgrade the contract. Explicit local/legacy validation with `public=False` may omit both halves, while either mode fails closed if only one half is present. Resolution is selected from manifest identity, never from a caller-controlled raw prefix: only canonical `REPO_ROOT/data/public-samples/manifest_public_sample.json` accepts the exact repo-relative train reference and resolves from module `REPO_ROOT`; every non-formal manifest requires a safe canonical basename and resolves from `manifest.parent`. Every path remains symlink-free and contained. Validation checks final-byte SHA-256, canonical JSONL bytes, exact row count, non-empty unique IDs, train-only split labels, and exact equality with the ordered train subsequence of the supplied mixed SFT artifact.

Alternative rejected: checking only row count and split. That would not detect reordered rows, provenance drift, or substituted row content.

### 4. Preserve the current population identity during materialization

The updated builder will be run twice in temporary directories. Both train artifacts must be byte-identical. Temporary mixed SFT and DPO bytes must equal the committed files. Only the new train artifact and the minimal manifest binding are materialized into `data/public-samples`; current `manifest_id`, `generated_at`, counts, and split counts are preserved.

### 5. Snapshot prior CURRENT inputs for historical audits

Historical design/audit modules that intentionally freeze the old manifest and split-integrity summary SHAs resolve those logical sources to immutable public snapshots containing the exact pre-change bytes. Their expected historical hashes and emitted reports remain unchanged. The CURRENT split-integrity JSON/Markdown are mechanically regenerated against the live metadata-extended manifest, and only the live truth-surface pin advances.

Alternative rejected: replacing old expected hashes with the new live hash. That would rewrite historical evidence rather than preserve it.

## Risks / Trade-offs

- [The dedicated file is reordered or reconstructed differently] → Filter the canonical in-memory row list without sorting or object transformation, then assert exact ordered-subsequence equality.
- [Manifest path escapes or follows a symlink] → Reject absolute paths, backslashes, dot segments, root escape, and every symlink component before reading.
- [A repo-internal non-formal build is mistaken for formal output] → Select path semantics from the exact canonical output/manifest identity; all other locations use basename plus `manifest.parent`.
- [Artifact bytes drift after manifest generation] → Hash final bytes and revalidate hash/count/canonical encoding from disk.
- [A public binding is deleted to bypass validation] → Require both binding halves for `public=True`; allow double absence only for explicit `public=False` local/legacy validation, and reject partial binding in both modes.
- [Current metadata change corrupts historical audit replay] → Keep old manifest bytes in a hash-named snapshot and route only historical readers to it.
- [The new derivative is mistaken for new data or model evidence] → Preserve population identity/counts and state explicitly that this is metadata/data-access hardening only.

## Migration Plan

1. Add failing builder and validation tests.
2. Implement canonical train-only emission and fail-closed validation.
3. Rebuild twice in temporary directories and verify deterministic bytes plus unchanged mixed SFT/DPO.
4. Materialize the new artifact and minimally extend the current manifest while preserving population identity fields.
5. Add prior-manifest and prior-split-summary snapshots and historical resolver entries; regenerate the CURRENT split report and update only the live truth-surface hash.
6. Run focused, full, lint, type, OpenSpec, truth-surface, and diff checks. Leave the change active and uncommitted.

Rollback is deletion of the new artifact and restoration of the exact prior manifest bytes. Historical snapshots are append-only evidence and need not be removed.

## Open Questions

None. The user approved the bounded mixed-artifact read solely for train-only materialization and explicitly withheld all execution and integration actions.
