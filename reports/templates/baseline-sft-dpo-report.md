# Baseline vs SFT vs DPO Report Template

This template is for aggregate contract-level reporting. It must not claim live-browser benchmark improvement unless a controlled execution-smoke artifact and downstream evidence explicitly support that claim.

## Artifact Inputs

- Dataset manifest:
- Baseline predictions:
- SFT adapter metadata:
- DPO adapter metadata:
- Metrics JSON:

## Summary Table

| System | JSON valid | Route accuracy | Safety precision | Safety recall | Confirmation accuracy | Slot F1 | Contract exact match |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Rule baseline | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| Prompt-only baseline | unavailable unless predictions are supplied |  |  |  |  |  |  |
| SFT dry-run | metadata only | metadata only | metadata only | metadata only | metadata only | metadata only | metadata only |
| DPO dry-run | metadata only | metadata only | metadata only | metadata only | metadata only | metadata only | metadata only |

## Claim Boundary

The bootstrap phase demonstrates reproducible data, formatting, validation, metadata, and metrics plumbing. It does not publish a trained checkpoint, full private corpus, or live-browser improvement claim.
