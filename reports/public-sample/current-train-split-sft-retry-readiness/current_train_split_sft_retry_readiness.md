# Voice2Task current train split SFT retry readiness

This is readiness-only evidence for a later bounded current-train-split SFT retry. It does not train, rerun predictions, mutate data, repair predictions, change prompts, or relax evaluator metrics.

## Boundary

- No A100 SFT/DPO/GRPO training was launched.
- No held-out prediction rerun was launched.
- No public sample data, prompt, or evaluator metric was changed.
- No checkpoint, adapter, safety-improvement, production-readiness, private-corpus, or live-browser claim is made.
- strict `contract_exact_match` and strict `slot_f1` remain authoritative.
- `slot_f1_soft` remains diagnostic-only.

## Summary

- Manifest: `public-sample-20260616T165835Z`
- Current baseline interpretation: `formal_public_heldout_partial_signal`
- Train split rows selected by dry-run: `118`
- Form-fill repair train rows: `21`
- Blocked-payment repair train rows: `4`
- Future retry runtime: `a100-current-train-split-sft-retry`
- Readiness status: `ready_for_bounded_a100_sft_retry_phase`
- Recommended next change: `run-a100-current-train-split-sft-retry`

## Current Strict Metrics Input

- `dev`: `{'prediction_count': 69, 'contract_exact_match': 0.463768115942029, 'slot_f1': 0.5652173913043478, 'slot_f1_soft': 0.8157448486641034, 'json_valid_rate': 1.0, 'route_accuracy': 0.8695652173913043, 'safety_recall': 0.5555555555555556}`
- `test`: `{'prediction_count': 69, 'contract_exact_match': 0.34782608695652173, 'slot_f1': 0.49758454106280187, 'slot_f1_soft': 0.7645681076840498, 'json_valid_rate': 1.0, 'route_accuracy': 0.927536231884058, 'safety_recall': 1.0}`

## Evidence Inputs

- Dry-run metadata: `reports/public-sample/current-train-split-sft-retry-readiness/sft-dry-run/adapter_metadata.json`
- Current baseline evidence: `reports/public-sample/a100-current-manifest-sft-v3-prediction-baseline/formal_public_heldout_prediction.json`
- Public merge evidence: `reports/public-sample/blocked-payment-safety-repair-public-sample-merge/blocked_payment_safety_repair_public_sample_merge.json`
- SFT config: `configs/sft-a100-current-train-split-retry.json`
- Dev prediction config: `configs/sft-a100-current-train-split-retry-dev-prediction.json`
- Test prediction config: `configs/sft-a100-current-train-split-retry-test-prediction.json`

## Recommended Next Step

Open `run-a100-current-train-split-sft-retry` as a separate bounded phase. That phase must perform fresh A100 GPU preflight, use private overrides outside git, keep all adapters/logs/checkpoints private, and publish only sanitized strict held-out evidence.
