# Voice2Task slot value candidate SFT probe

This is candidate-only dry-run evidence for the standalone slot value candidate SFT rows. It records row selection and A100 readiness only; it does not publish adapter outputs or claim model recovery.

## Boundary

- Formal public sample seed, SFT, DPO, and manifest files are unchanged.
- No DPO training, SFT training, prediction run, checkpoint release, or adapter release is claimed.
- strict `contract_exact_match` remains primary; no evaluator relaxation is introduced.
- This is not held-out, private-corpus, production-readiness, or live-browser evidence.

## Summary

- Candidate SFT rows: `12`
- Selected dry-run training rows: `12`
- Formal public sample modified: `False`
- A100 training status: `blocked_missing_train_dependencies`
- Recommended next step: `prepare_private_a100_train_environment_then_run_candidate_probe`

## A100 Preflight

- SSH status: `ok`
- Output root status: `ok`
- Idle GPU status: `idle_gpu_available`
- Selected GPU index: `3`
- Available train dependencies: `['torch', 'transformers', 'peft', 'accelerate']`
- Missing train dependencies: `['trl', 'datasets']`
- Safe to launch training now: `False`

## Evidence

- Dry-run metadata: `reports/public-sample/slot-value-candidate-sft-probe/sft-dry-run/adapter_metadata.json`
- Candidate manifest: `data/public-samples/manifest_slot_value_candidate_probe.json`
- SFT config: `configs/sft-a100-slot-value-candidate-probe.json`
- Prediction config: `configs/sft-a100-slot-value-candidate-probe-prediction.json`
