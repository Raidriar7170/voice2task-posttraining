## Context

The latest archived phase hardened shared prediction prompt policy for two
remaining strict residual families: ambiguous clarify wording and unsafe
payment denial wording. The prior A100 merged slot-value evaluation trained a
7B adapter and produced train/dev/test metrics, but those predictions were
generated before this hardened policy was available.

This phase reuses the prior merged slot-value adapter and only regenerates
predictions/metrics with current code. It must not train, expand data, alter
gold targets, or change evaluator semantics.

## Goals / Non-Goals

**Goals:**

- Prepare prediction-only configs for the existing merged slot-value 7B adapter.
- Run train/dev/test predictions on A100 only when SSH, workspace placement,
  dependency, and GPU occupancy checks are safe.
- Require prediction metadata to show the hardened canonical prompt flags.
- Compare new strict split metrics against the prior merged slot-value evidence.
- Publish public-safe evidence, Human Brief, and validation results.

**Non-Goals:**

- No SFT, DPO, GRPO, or adapter continuation training.
- No data, seed, SFT, DPO, parser, schema, retry, decoding, or evaluator
  semantic changes.
- No semantic-equivalence scoring, strict metric relaxation, prediction repair,
  or prediction replacement.
- No adapter/checkpoint release, full-private-corpus claim, production claim,
  or live-browser benchmark claim.

## Decisions

1. **Prediction-only configs.** The committed configs point at the previous
   `<a100_project_root>/runs/a100-merged-slot-value-heldout-eval/adapter` and
   omit `allow_heavy_training` and `adapter_output_dir`.

2. **Separate evidence directory.** The new evidence lives under
   `reports/public-sample/a100-hardened-canonical-policy-rerun/` so it cannot
   be confused with the prior merged slot-value run.

3. **Prompt policy provenance is required.** The evidence pack records
   `clarify_ambiguity_canonical_phrase_visible` and
   `unsafe_payment_canonical_command_visible` by split from prediction metadata.
   If the flags are absent, the rerun is not treated as hardened-policy
   evidence.

4. **Strict metrics remain primary.** Dev/test `contract_exact_match` are the
   primary held-out signal. Train exact match is only a sanity check that the
   reused adapter still predicts train rows under the current prompt.

5. **Blocked status is acceptable evidence.** If remote execution is unsafe or
   unavailable, the phase publishes a public-safe blocked status rather than
   inventing metrics.

## Risks / Trade-offs

- [Risk] Prompt hardening may not change the adapter output at all. ->
  Mitigation: compare against the previous merged run and report unchanged
  results honestly.
- [Risk] Remote execution may use stale code. -> Mitigation: sync current
  source/configs before running and require prompt flags in metadata.
- [Risk] Evidence can leak remote paths or host details. -> Mitigation: commit
  only sanitized aggregate metadata, use placeholders, and run leak scans.
- [Risk] A fully recovered public sample can be overclaimed. -> Mitigation:
  keep claims limited to this 42-row public sample and no release posture.
