# Voice2Task family-stratified generalization candidates

This is candidate data only: it creates a standalone public-safe family-stratified generalization dataset and does not rewrite formal public sample files.

## Boundary

- Formal public sample seed, SFT, DPO, and manifest files are not rewritten.
- No DPO pairs, SFT training, prediction run, or A100 execution is performed.
- strict `contract_exact_match` remains primary.
- Soft slot F1 and semantic equivalence remain diagnostic-only.
- This is not model recovery, held-out recovery, checkpoint, adapter, production, or live-browser evidence.

## Summary

- Families: `['blocked_payment', 'clarify', 'confirmation', 'extract', 'form_fill', 'navigation', 'search']`
- Candidate seed rows: `63`
- Candidate SFT rows: `189`
- SFT split counts: `{'train': 63, 'dev': 63, 'test': 63}`
- Formal public sample seed rows: `77`
- Formal public sample SFT rows: `231`
- Formal public sample DPO pairs: `661`
- Formal public sample modified: `False`
- Recommended next step: `review_candidate_dataset_before_merge_or_training`

## Family Split Counts

| family | train seeds | dev seeds | test seeds | train SFT | dev SFT | test SFT |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `blocked_payment` | 3 | 3 | 3 | 9 | 9 | 9 |
| `clarify` | 3 | 3 | 3 | 9 | 9 | 9 |
| `confirmation` | 3 | 3 | 3 | 9 | 9 | 9 |
| `extract` | 3 | 3 | 3 | 9 | 9 | 9 |
| `form_fill` | 3 | 3 | 3 | 9 | 9 | 9 |
| `navigation` | 3 | 3 | 3 | 9 | 9 | 9 |
| `search` | 3 | 3 | 3 | 9 | 9 | 9 |

## Recommended Next Step

Review this candidate dataset before any merge, DPO generation, or A100 training. A later bounded OpenSpec phase should decide whether to merge candidates into the formal public sample and how to evaluate held-out exact match without changing evaluator semantics.
