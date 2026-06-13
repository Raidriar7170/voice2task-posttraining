# Voice2Task runtime-label and tiny-overfit diagnostic

This local diagnostic compares public-safe artifacts for the current manifest. It does not train, run prediction, download models, load private adapters, or repair outputs.

## Boundary

- This is not a model recovery claim.
- This is not a checkpoint release.
- This is not an adapter release.
- This is not held-out or private-corpus generalization evidence.
- This makes no production-readiness claim.
- This is not a public full-corpus release claim.
- This is not a live-browser benchmark or benchmark-improvement claim.
- Stale runtime-label or tiny-overfit evidence is prior context only.

## Summary

- Current manifest: `public-sample-20260613T072200Z`
- Runtime label status: `stale_manifest_mismatch`
- Current true label-mask status: `unavailable`
- Tiny-overfit evidence status: `stale_manifest_mismatch`
- Tiny-overfit readiness: `blocked_until_fresh_runtime_label_check`
- Recommended next step: `run_fresh_current_manifest_runtime_label_check`

## Learning Signal Context

- Available: `True`
- Freshness: `fresh_current_manifest`
- Source manifest: `public-sample-20260613T072200Z`
- Assistant target spans present: `True`
- Learning-signal true label-mask status: `unavailable`

## Prior Repair Evidence

- Available: `True`
- Overall interpretation: `public_heldout_residual_repair_failed`
- Split exact match: `{'dev': 0.0, 'test': 0.0, 'train': 0.3333333333333333}`

## Runtime Label Evidence

- Available: `True`
- Freshness: `stale_manifest_mismatch`
- Source manifest: `public-sample-20260601T162313Z`
- Current manifest proof: `False`
- Evidence status: `labels_inspected`
- Runtime check status: `executed_runtime_label_provenance_check`
- Prior label-mask fields: `{'true_label_mask_status': 'inspectable', 'prompt_tokens_masked': False, 'assistant_tokens_carry_loss': True, 'prompt_token_count': 187, 'assistant_token_count': 62, 'label_source_kind': 'private_training_runtime', 'evidence_gaps': []}`
- Current label-mask fields: `{}`
- Assistant-only loss-mask claim: `False`

## Tiny-Overfit Evidence

- Available: `True`
- Freshness: `stale_manifest_mismatch`
- Source manifest: `public-sample-20260601T162313Z`
- Current manifest proof: `False`
- Overfit diagnostic: `True`
- Prediction split: `train`
- Training rows used: `3`
- Assistant-only objective: `{'assistant_tokens_carry_loss': True, 'label_source_kind': 'private_training_runtime', 'prompt_tokens_masked': True, 'true_label_mask_status': 'inspectable'}`

## Readiness

- Status: `blocked_until_fresh_runtime_label_check`
- Reason: `current_manifest_runtime_label_evidence_missing_or_stale`

## Artifact Policy

- `checkpoints_or_adapters_copied_to_git`: `False`
- `host_details_omitted`: `True`
- `private_corpus_rows_omitted`: `True`
- `private_paths_omitted`: `True`
- `raw_assistant_targets_written`: `False`
- `raw_logs_copied_to_git`: `False`
- `raw_rendered_prompts_written`: `False`
- `ssh_details_omitted`: `True`
