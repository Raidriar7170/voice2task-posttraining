# Voice2Task family-stratified public sample merge

This report records a data merge into the formal public sample. It does not prove held-out recovery, model recovery, adapter release, checkpoint release, production readiness, or live-browser improvement.

## Boundary

- Formal public sample seed, SFT, DPO, and manifest files were rebuilt.
- No SFT/DPO/GRPO training, prediction run, or A100 execution was performed.
- strict `contract_exact_match` remains the future primary evaluation metric.
- Soft slot F1 and semantic equivalence remain diagnostic-only.

## Summary

- Seed rows: `77`
- SFT rows: `231`
- DPO pairs: `661`
- SFT split counts: `{'train': 93, 'dev': 69, 'test': 69}`
- Merged candidate seed rows: `63`
- Merged candidate SFT rows: `189`
- Families: `['blocked_payment', 'clarify', 'confirmation', 'extract', 'form_fill', 'navigation', 'search']`
- Candidate seed split counts: `{'train': 21, 'dev': 21, 'test': 21}`

## Recommended Next Step

Use the new manifest ID for a later prediction-only eval phase. Do not compare new results to prior held-out metrics without noting that the formal public sample boundary changed.
