## Context

The current SFT evidence chain has three layers: contract-only formatting, public-safe prediction/diagnostic artifacts, and an objective-inspection result. The latest alignment diagnostic proved that the rendered SFT training text contains the assistant contract target while prediction prompts exclude the gold target, but it deliberately reported true label-mask evidence as unavailable because the local path did not inspect labels produced by the real tokenizer/collator path.

This phase adds a narrow provenance diagnostic before another private A100 rerun. It must stay local and public-safe by default: no model download, no private adapter load, no A100 execution, no raw rendered prompt/target dump, and no upgrade from evidence gap to success unless real label tensors are inspected.

## Goals / Non-Goals

**Goals:**

- Record tokenizer/template status, collator status, label tensor source, prompt mask status, and assistant-target loss status in one public-safe inspection result.
- Let local tests simulate an actual tokenizer/collator path so the inspectable and unavailable branches are both covered.
- Reuse the existing `sft-inspect-objective` surface where possible and keep prior objective-inspection consumers compatible.
- Generate a sanitized evidence pack and Human Brief that link prior diagnostics while preserving their failures.

**Non-Goals:**

- No generic chat fine-tuning, skill routing, GUI action-policy learning, first-phase GRPO, checkpoint release, adapter release, public full-corpus release, private A100 rerun, or live-browser benchmark claim.
- No default model download or remote dependency.
- No attempt to repair prior invalid predictions or infer model quality from loss alone.

## Decisions

1. Extend objective inspection rather than add a separate training command.
   - Rationale: Existing reports already consume `objective_inspection.json`; preserving the surface keeps the next diagnostic small and avoids parallel evidence formats.
   - Alternative considered: add `sft-inspect-label-provenance` as a new command. That would be clearer but would duplicate much of the objective-inspection contract and require more report plumbing.

2. Treat label provenance as source-specific evidence.
   - Rationale: A tokenizer-only offset map proves target span structure, not loss masking. The result must say whether labels came from real training labels, TRL/collator labels, fixture labels, or were unavailable.
   - Alternative considered: infer labels from assistant span and tokenizer offsets. Rejected because it would overstate evidence.

3. Keep local validation dependency-light and fail closed.
   - Rationale: CI/local bootstrap should not download Qwen models or require A100 resources. Missing `transformers`, `trl`, `torch`, tokenizers, or collators should produce structured unavailable states.
   - Alternative considered: require train extras for this phase. Rejected because the public repo still needs public-sample smoke validation without heavy runtime setup.

4. Publish summaries and hashes, not raw rendered text.
   - Rationale: Public-safe artifacts should prove evidence shape without leaking private prompts, paths, host details, raw logs, or oversized generated corpora.
   - Alternative considered: include prompt/target excerpts for readability. Rejected because previous review already flagged raw rendered text as a leak/overclaim risk.

## Risks / Trade-offs

- Real tokenizer or TRL versions differ from local fixtures -> Mitigation: record package versions and label source, and keep fixture evidence labeled as non-real.
- Label tensors are still unavailable locally -> Mitigation: make `labels_unavailable` the expected honest output and require the next A100/runtime phase before claims.
- Report consumers may overread `assistant_tokens_carry_loss=true` -> Mitigation: require `label_source` and interpretation boundaries in JSON, Markdown, specs, and Human Briefs.
- Optional dependency behavior may vary across TRL versions -> Mitigation: use defensive extraction and tests around public contract fields instead of private library internals.
