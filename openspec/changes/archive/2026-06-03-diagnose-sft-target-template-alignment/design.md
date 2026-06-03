## Context

The previous train-split overfit diagnostic showed real private-adapter predictions on three train rows, but schema recovery failed. Existing metadata records the shared contract chat-template policy and prompt constraints, while objective inspection still reports an unavailable boundary. Before another private A100 rerun, this repo needs a local, public-safe diagnostic that can explain what is known and unknown about SFT target rendering, assistant target spans, label-mask evidence, chat-template fallback behavior, and adapter/base metadata alignment.

This change stays within the post-training companion repo. It does not run private prediction, retrain on A100, publish adapters, or change model claims.

## Goals / Non-Goals

**Goals:**

- Generate a deterministic local diagnostic from committed public-sample rows, SFT config, prediction config, and prior sanitized prediction metadata.
- Compare SFT training text and prediction prompt rendering for the same row and record their shared prefix, assistant target presence, and gold-target leakage status.
- Report assistant target span and label-mask evidence separately: structural target span can be proven locally, but true label masking is only proven when inspected labels from the real training path are available.
- Record chat-template source and fallback policy without requiring tokenizer downloads.
- Compare public-safe base model, model source, adapter gate, prediction split, and formatting-policy metadata between config and prior prediction metadata.
- Emit machine-readable JSON and human-readable Markdown evidence under `reports/public-sample/`.

**Non-Goals:**

- Real A100 retraining or private adapter prediction.
- Downloading base models, tokenizers, checkpoints, adapters, or remote caches.
- Repairing predictions, changing metrics, or replacing failed private-adapter output.
- Claiming checkpoint release, adapter release, dev/test generalization, production readiness, or live-browser benchmark improvement.

## Decisions

1. **Use committed public-sample rows as the diagnostic substrate.**
   - Rationale: public rows are enough to verify formatting, prompt/target boundaries, and target leakage without exposing local/private corpus rows.
   - Alternative considered: run against private train rows. Rejected for this bounded phase because it would require private data handling and remote evidence controls.

2. **Separate structural target-span evidence from real label-mask evidence.**
   - Rationale: local rendering can prove where the assistant contract appears in text, but it cannot prove TRL/PEFT labels unless the actual tokenizer/collator labels are inspectable.
   - Alternative considered: infer assistant-only loss from successful text rendering. Rejected because the previous evidence explicitly warned that loss or target text alone is not proof of Browser Task Contract learning.

3. **Treat tokenizer chat-template rendering as optional evidence.**
   - Rationale: local validation should pass without downloading a tokenizer. The diagnostic records whether a tokenizer template was inspectable; otherwise it records deterministic fallback evidence.
   - Alternative considered: require tokenizer loading. Rejected because it would introduce network/model dependency into a public-safe local diagnostic.

4. **Compare adapter/base metadata with public-safe placeholders only.**
   - Rationale: prediction metadata can reveal alignment status such as base model placeholder, model source, adapter configured gate, stack, and formatting policy without exposing private paths.
   - Alternative considered: inspect adapter config files directly. Rejected for this phase because private adapter paths must remain outside committed artifacts.

## Risks / Trade-offs

- [Risk] A structural target-span pass could be misread as proof that real training labels masked system/user tokens correctly. -> Mitigation: reports must label label-mask status as `labels_unavailable` unless real labels are inspected.
- [Risk] A fallback rendering pass may hide tokenizer-specific chat-template issues. -> Mitigation: reports must distinguish `fallback` from `tokenizer_chat_template` evidence and list tokenizer-template absence as an evidence gap.
- [Risk] Adapter/base metadata comparison could leak private config values. -> Mitigation: use existing public-safe placeholders and leak-scan the report directory before commit.
- [Risk] The diagnostic could become a model-fix phase. -> Mitigation: tasks stop at evidence generation and bounded interpretation; retraining or prompt correction requires a later OpenSpec change.
