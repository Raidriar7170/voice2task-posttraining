# Voice2Task scaled public-sample candidate materialization

This is candidate data only: it creates standalone public-safe scaled public-sample candidate artifacts and does not merge the formal public sample.

## Boundary

- Formal public sample seed, SFT, DPO, and manifest files are not rewritten.
- No formal public sample merge is performed.
- No DPO pairs, SFT training, prediction run, or A100 execution is performed.
- No prompt change, evaluator metric change, slot normalization, or prediction repair is introduced.
- strict `contract_exact_match` and strict `slot_f1` remain primary for later evaluation.
- This is not model recovery, held-out recovery, checkpoint, adapter, production, or live-browser evidence.

## Summary

- Current formal counts: `{'dpo_pairs': 2046, 'seed_rows': 240, 'sft_rows': 675}`
- Current formal seed split counts: `{'train': 102, 'dev': 69, 'test': 69}`
- Current formal SFT split counts: `{'dev': 207, 'test': 207, 'train': 261}`
- Target counts: `{'core_seed_rows': 220, 'confirmation_boundary_overlay_seed_rows': 20, 'total_seed_rows_after_later_merge': 240}`
- Core family deltas: `{'search': 20, 'navigation': 17, 'form_fill': 3, 'extract': 25, 'clarify': 33, 'blocked_payment': 20}`
- Candidate seed rows: `138`
- Candidate core seed rows: `118`
- Candidate overlay seed rows: `20`
- Candidate SFT rows: `414`
- Seed split counts: `{'train': 46, 'dev': 46, 'test': 46}`
- SFT split counts: `{'train': 138, 'dev': 138, 'test': 138}`
- Formal public sample modified: `False`
- Recommended next step: `review_standalone_candidates_before_any_formal_merge`

## Core Family Counts

| family | candidate seeds |
| --- | ---: |
| `search` | 20 |
| `navigation` | 17 |
| `form_fill` | 3 |
| `extract` | 25 |
| `clarify` | 33 |
| `blocked_payment` | 20 |

## Overlay Counts

| overlay | candidate seeds |
| --- | ---: |
| `confirmation_boundary` | 20 |

## Recommended Next Step

Review the standalone candidates before any later formal merge, DPO generation, or training. A later bounded phase should create a new formal manifest boundary before comparing model metrics.
