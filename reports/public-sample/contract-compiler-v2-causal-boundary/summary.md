# Contract Compiler V2 causal boundary audit

Status: `ARCHIVED`.

## Conclusion

Both compiler and model-learning causal estimands are `CAUSAL_IDENTIFICATION_BLOCKED`; renderer and transformation mechanics are `DESCRIPTIVE_ONLY`.

**99.77% support is not legacy canonical exact compatibility.** Historical `2180/2185` measures renderer support, not equality with legacy canonical targets.

## Fixed 247-row renderer population

- Parse valid: `247/247`
- Supported and deterministic: `246/247`
- Repeated outcome stable: `247/247`
- Legacy exact: `98/247` (`0.396761`)
- Legacy mismatch among supported rows: `148`
- Supported-only legacy exact (secondary): `98/246` (`0.398374`)
- Policy self-consistent ITT: `246/247` (`0.995951`)

## Architecture boundary

Observed paths are `IMPLEMENTED_OBSERVED`; the candidate compiler graph is `NOT_IMPLEMENTED_HYPOTHETICAL` with `runtime_wired=false`.

## Audit-only scope

- `a100_execution=false`
- `adapter_release=false`
- `checkpoint_release=false`
- `clean_evaluation_run=false`
- `compiler_implementation=false`
- `data_mutation=false`
- `decoder_implementation=false`
- `evaluator_default_change=false`
- `heldout_recovery_claim=false`
- `historical_metrics_rescored=false`
- `live_browser_benchmark_improvement_claim=false`
- `lockbox_row_level_read=false`
- `model_improvement_claim=false`
- `natural_asr_generalization_claim=false`
- `prediction_run=false`
- `production_readiness_claim=false`
- `prompt_change=false`
- `public_dev_test_selection=false`
- `safety_readiness_claim=false`
- `training_run=false`

## Bound sources

- `src/voice2task/formatting.py` — `a5933b89f9f9b43358619b15264047bc449a83dacadfc3e49db88d38d434a8f0`
- `src/voice2task/training.py` — `978e2df42be7b1e020c5215febaf843a527b0fb96469273c93b66ce20b62db3c`
- `src/voice2task/schemas.py` — `e5897b622dbcac398c28b14d264b99fb98ae749cf278cda1cdd9e83a4300d74f`
- `src/voice2task/evaluation.py` — `568f4f41d2d6b0b5d45e68c53e14c5c6b70ebb37227c988a0b4b5aff8017e228`
- `src/voice2task/contract_core_v2.py` — `ed77d5a21af3a868c3b9ff0fa81c62da29bfe939070c39fb3c8a0076f8c29098`
- `src/voice2task/contract_v2_projection.py` — `b35c2b47ea73d96a484b96f3c6d4d38e510a58c5c2fb0ebf389e6da36e3a59b9`
- `data/public-samples/seed_traces.jsonl` — `8fe5e75e9e0891b6824d7c142cbe15547267377420f8b3240414436265d15801`
- `data/public-samples/manifest_public_sample.json` — `f866c173795e97953b1dec85611b405867d0a29497910282f99d399f109cda95`
- `reports/public-sample/split-integrity-audit/summary.json` — `ac10bd0a1c3fefb717433de68ae29d049069b521bae8599234b7f52faec8f598`
- `reports/public-sample/internal-contract-v2-core/summary.json` — `b4cbee7220cb8d9564c4a90a1b0469b27b0eb666b5aed572ff58749994d67d20`
- `CONTEXT.md` — `2ffc67d81be8b3e482555efd23db5b0bf60239eb4ef4d9e24514cae24ea1009f`
- `data/lockbox/lockbox-v1.manifest.json` — `72471bac59749f3bc9d21d73db47dafe1f160b978f5ac3971434e13527ddedde`
- `reports/lockbox-v1/final-evaluation/run-card.json` — `39e59cd6e16baa7adadb6b3c474e7fce8bfe8223e5980a1288a1c50432acec66`
- `reports/lockbox-v1/final-evaluation/base/metrics.json` — `400fa753e6e8bde611af4e4f9623155ceff6664454bfea0f57748043243cd02f`
- `reports/lockbox-v1/final-evaluation/final-sft/metrics.json` — `aaecc8dcdad90e70c0f8a7c59a21d2e65d8d42bae3e304e4dce9b049390bc829`
- `reports/lockbox-v1/final-evaluation/comparison.json` — `48fae0e85e016c1872477881939716076d96998d0c63f83adf1e9be42d9ed544`
