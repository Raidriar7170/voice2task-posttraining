# Voice2Task scaled public-sample merge

This report records a formal public-sample data merge. It does not prove held-out recovery, model quality, safety improvement, adapter release, checkpoint release, production readiness, public full-corpus release, or live-browser improvement.

## Boundary

- Formal public sample seed, SFT, DPO, and manifest files were rebuilt.
- No SFT/DPO/GRPO training, prediction run, A100 execution, prompt change, slot normalization, or evaluator relaxation was performed.
- strict `contract_exact_match` and strict `slot_f1` remain authoritative for later evaluation.
- `slot_f1_soft` and semantic equivalence remain diagnostic-only.
- The formal public sample boundary changed; old metrics are not directly comparable.

## Counts

- Pre-merge counts: `{'dpo_pairs': 881, 'seed_rows': 102, 'sft_rows': 261}`
- Post-merge seed rows: `240`
- Post-merge SFT rows: `675`
- Post-merge DPO pairs: `2046`
- Post-merge SFT split counts: `{'train': 261, 'dev': 207, 'test': 207}`

## Candidate Source

- Candidate seed rows: `138`
- Candidate SFT rows: `414`
- Candidate DPO pair delta: `1165`
- Candidate seed split counts: `{'train': 46, 'dev': 46, 'test': 46}`
- Candidate group counts: `{'confirmation_boundary_overlay': 20, 'core_family_delta': 118}`
- Candidate family counts: `{'blocked_payment': 20, 'clarify': 33, 'confirmation_boundary': 20, 'extract': 25, 'form_fill': 3, 'navigation': 17, 'search': 20}`

## Comparison Boundary

- Changed: `True`
- Previous manifest: `public-sample-20260617T045941Z`
- New manifest: `public-sample-20260617T152259Z`
- Old metrics directly comparable: `False`

## Validation

- Dataset validation ok: `True`
- Validation failures: `[]`

## Recommended Next Step

Run any model prediction or training work only in a later bounded phase that explicitly names this new manifest boundary.
