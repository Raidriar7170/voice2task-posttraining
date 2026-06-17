## Context

The current formal public manifest is `public-sample-20260616T165835Z` with
100 seed rows, 256 SFT rows, 864 DPO pairs, and split counts train 118 / dev 69
/ test 69. The latest current-manifest SFT v3 prediction baseline reports:

- dev strict `contract_exact_match=0.4638`, strict `slot_f1=0.5652`,
  `route_accuracy=0.8696`, and `safety_recall=0.5556`
- test strict `contract_exact_match=0.3478`, strict `slot_f1=0.4976`,
  `route_accuracy=0.9275`, and `safety_recall=1.0000`

The readiness phase confirmed that the current train split includes the merged
form-fill repair rows and blocked-payment repair rows, and that a distinct
future runtime label is available: `a100-current-train-split-sft-retry`.

## Goals / Non-Goals

**Goals:**

- Verify A100 connectivity and select a safe idle GPU without disturbing other
  users.
- Resolve private overrides only under the approved A100 project root.
- Run one private SFT retry on the current formal public train split.
- Run dev/test prediction-only strict evaluation with the new adapter.
- Commit only sanitized public evidence and document observed metrics honestly.

**Non-Goals:**

- No DPO, GRPO, prompt edits, evaluator edits, semantic-equivalence scoring,
  slot normalization, prediction repair, or prediction replacement.
- No public checkpoint, adapter, raw log, cache, private override, private path,
  host detail, SSH detail, token, or private corpus release.
- No production-readiness, live-browser benchmark, or private-corpus
  generalization claim.

## Decisions

1. Treat the readiness evidence as an input contract, not as model-quality
   evidence.

2. Create a new private remote root directory for this phase so the output does
   not overwrite prior SFT v3 adapter evidence.

3. Use exactly one selected GPU through `CUDA_VISIBLE_DEVICES`. If safe
   placement cannot be determined, stop and publish blocked evidence.

4. Publish dev/test strict metrics as observed results. Do not tune the
   evaluator or substitute older predictions if the retry does not improve.

5. Keep raw remote logs and adapter metadata private by default; commit only
   sanitized summaries generated from local evidence import helpers.

## Risks / Trade-offs

- A100 SSH or dependency setup can fail; the phase must record blocked/failed
  evidence rather than improvising.
- The 118-row train split is small and may overfit; observed improvements may
  not generalize beyond the current formal public sample.
- Training may improve form-fill while hurting safety, or the reverse; report
  split-level strict metrics and residuals instead of one aggregate claim.
- Metadata may contain private paths; leak scan all committed evidence after
  sanitization.
