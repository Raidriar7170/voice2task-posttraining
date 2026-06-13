## Context

The previous archived phase (`diagnose-sft-contract-learning-signal`) found that the current public SFT rows all contain the canonical assistant target in rendered local training text, but it did not inspect true runtime labels. Older runtime-label and train-split overfit artifacts exist, yet the clearest observed runtime-label artifact was produced for `public-sample-20260601T162313Z`, while the current manifest is `public-sample-20260613T072200Z`.

The current problem is therefore not simply "do labels ever work in this repo"; it is whether current public-sample training rows and current 7B failure evidence have a fresh objective-path explanation. The phase must keep private runtime evidence out of git and avoid presenting old artifacts as current proof.

## Goals / Non-Goals

**Goals:**

- Produce a public-safe diagnostic over the current manifest, latest learning-signal evidence, prior repair failure, and prior runtime/tiny-overfit artifacts.
- Mark prior runtime-label evidence as fresh only when its dataset manifest ID matches the current public manifest.
- Preserve exact label-mask fields when fresh runtime evidence exists: `true_label_mask_status`, `prompt_tokens_masked`, `assistant_tokens_carry_loss`, token counts, source kind, and evidence gaps.
- Recommend the next bounded action: run a fresh current-manifest runtime label check, run a 1-3 row tiny-overfit probe, or move to preference-signal diagnosis, depending on evidence.
- Generate JSON/Markdown evidence and a Chinese Human Brief without raw rendered prompts, raw targets, private paths, raw logs, model artifacts, or host/SSH details.

**Non-Goals:**

- No full A100 SFT/DPO/GRPO rerun in this phase.
- No model download from local public artifacts.
- No private adapter load from local public artifacts.
- No evaluator relaxation, semantic-equivalence replacement, rule-baseline substitution, or output repair.
- No checkpoint/adapter release, public full-corpus release, production-readiness claim, or live-browser benchmark claim.
- No generic chat fine-tuning, skill routing, or GUI action policy learning.

## Decisions

1. **Freshness is keyed by `dataset_manifest_id`.**
   - Decision: a runtime-label or tiny-overfit artifact is current only when its manifest ID equals the current public manifest ID.
   - Rationale: old runtime evidence can prove that an earlier training path was inspectable, but cannot explain current 2026-06-13 public rows after seed expansion and repair negatives.
   - Alternative considered: treat any prior runtime-label evidence as sufficient. Rejected because it would collapse historical objective evidence into current training-signal proof.

2. **The diagnostic is local and public-safe by default.**
   - Decision: the committed phase reads existing public-safe JSON/Markdown artifacts and writes only aggregate evidence. It does not execute private runtime code unless a later bounded A100 phase is opened.
   - Rationale: this keeps the phase reviewable and avoids leaking private model paths, logs, or outputs.
   - Alternative considered: immediately SSH to A100 and run a fresh label check. Rejected for this OpenSpec apply step because it changes execution posture and should be represented explicitly by the generated recommendation.

3. **Tiny-overfit remains a gate, not a success claim.**
   - Decision: the report may recommend a 1-3 row tiny-overfit probe, but must state that tiny-overfit evidence is train-internal and does not prove held-out behavior or release readiness.
   - Rationale: the current train repair rows also failed strict memorization; a tiny probe is useful only to isolate whether the training loop can overfit at all.

4. **No raw prompt/target persistence.**
   - Decision: row-level detail is restricted to IDs, splits, routes/task families, hashes, counts, and artifact paths.
   - Rationale: public-safe evidence should be reproducible without copying sensitive or overly detailed runtime content.

## Risks / Trade-offs

- **Risk:** The phase stops with a recommendation instead of proving current runtime labels on A100. → **Mitigation:** the evidence pack must say exactly what is stale, what is current, and what command/phase should run next.
- **Risk:** Old `labels_inspected` evidence could be overclaimed. → **Mitigation:** freshness status must be explicit and tested.
- **Risk:** Tiny-overfit wording could sound like model recovery. → **Mitigation:** claims fields and Markdown/Human Brief must deny model recovery, held-out generalization, release, production, and live-browser benchmark claims.
- **Risk:** Report files become a second source of truth. → **Mitigation:** reports link back to OpenSpec specs, manifests, and source artifacts; OpenSpec and JSON evidence remain authoritative.
