# Voice2Task SFT label provenance evidence

This evidence pack summarizes SFT label provenance only. It does not publish raw rendered prompts, checkpoints, adapters, private paths, or raw logs.

## Boundary

- This is not a checkpoint release.
- This is not an adapter release.
- This is not held-out generalization evidence.
- This makes no production-readiness claim.
- This is not a live-browser benchmark or benchmark-improvement claim.

## Summary

- Inspection status: `dependency_unavailable`
- Tokenizer status: `unavailable`
- Tokenizer template status: `unavailable`
- Collator status: `unavailable`
- Label source: `unavailable`
- Label tensor available: `False`
- True label-mask status: `unavailable`
- Prompt token count: `None`
- Assistant token count: `None`
- Prompt tokens masked: `None`
- Assistant tokens carry loss: `None`

## Evidence Gaps

- `real_training_labels_not_inspected`
- `real_training_label_provenance_missing`

## Prior Artifacts

- `target_template_alignment`: `reports/public-sample/sft-target-template-alignment/sft_target_template_alignment.json`
- `target_template_alignment_markdown`: `reports/public-sample/sft-target-template-alignment/sft_target_template_alignment.md`
- `train_split_overfit_objective`: `reports/public-sample/a100-train-split-overfit-diagnostic/objective_inspection.json`
- `train_split_overfit_report`: `reports/public-sample/a100-train-split-overfit-diagnostic/report.md`

## Interpretation

- Loss improvement alone does not prove Browser Task Contract learning.
- Fixture or simulated labels are not real TRL/private-training-path proof.
- True label provenance requires inspected labels from the real tokenizer/collator path.
