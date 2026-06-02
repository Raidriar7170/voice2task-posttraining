## Context

Voice2Task Post-Training is a new independent companion repository for Voice-to-Browser Agent. The existing product line already has speech-to-task traces, schema validation, route/safety gates, and adaptation evaluation surfaces; this change turns that evidence into a focused SFT/DPO project for Chinese spoken command normalization.

The first phase must be credible to large-model algorithm reviewers without making premature claims. It should show a complete post-training loop: dataset construction, SFT, DPO, metric-driven evaluation, and sanitized reporting. It should not claim a released checkpoint, full public dataset, or live-browser success improvement until those artifacts exist.

## Goals / Non-Goals

**Goals:**

- Build a reproducible public-sample and local/private corpus workflow for speech-to-contract normalization.
- Train Qwen-family small instruction models with LoRA SFT using Transformers, PEFT, and TRL.
- Train DPO adapters from chosen/rejected browser task contract pairs.
- Evaluate outputs through the contract evaluation ladder: schema validity, task type, route, safety, confirmation, slot extraction, and execution smoke.
- Produce reviewer-readable reports and manifests that separate public artifacts from local/private generated corpora.

**Non-Goals:**

- Generic chat fine-tuning.
- Hermes-style skill routing.
- GUI action policy learning.
- First-phase GRPO or rule-reward training.
- Publishing the full local/private corpus.
- Claiming live browser benchmark improvement before controlled evidence exists.

## Decisions

### Keep the repository as a training/evaluation companion

The implementation will own dataset builders, training scripts, evaluation scripts, configs, reports, and adapter export conventions. Voice-to-Browser Agent remains the downstream runtime and source of sanitized seed traces.

Alternatives considered:

- Embed training in Voice-to-Browser Agent: rejected because it makes the runtime repo heavier and blurs product/demo concerns with model training.
- Make a generic agent post-training lab: rejected for the first phase because it weakens the voice-to-contract story and expands scope.

### Use three artifact tiers

The project will distinguish public samples, generated local/private corpora, and reports/manifests.

- Public samples are committed and safe for smoke tests.
- Local/private corpora are reproducible by script but not committed in full.
- Reports/manifests summarize counts, splits, metrics, and validation without leaking raw private rows.

This keeps the public repo useful while preserving the privacy boundary inherited from trace-derived data.

### Implement the transparent TRL/PEFT path first

The first implementation will use a readable Python training stack around Transformers, PEFT, TRL, datasets, and accelerate. Qwen-family small instruction models are the reference model family. ms-swift can be added later as an engineering route for larger A100 runs, but it is not the only first-phase path.

Alternatives considered:

- ms-swift-only: useful for operational training, but less transparent as the first public implementation path.
- Data/eval only: safer but undercuts the purpose of adding a post-training algorithm project.

### Treat DPO as contract preference learning

DPO examples will compare chosen/rejected browser task contracts. Rejected outputs should be plausible failures: unsafe route, missing confirmation, wrong task type, incorrect slots, underspecified contract, or malformed schema. Random invalid JSON alone is not enough to represent preference learning.

### Make evaluation product-relevant but bounded

The evaluation CLI will compute contract metrics before optional downstream execution smoke. Execution smoke verifies that generated contracts can be consumed by controlled Voice-to-Browser Agent validation paths; it is not a live-browser benchmark.

## Risks / Trade-offs

- Trace-derived data may leak local details -> Use sanitized samples, generated manifests, public-leak scans, and keep full corpora out of git.
- Small first-phase corpora may overfit -> Maintain train/dev/test splits, hard negatives, and report baseline comparisons rather than only fine-tuned scores.
- DPO gains may be subtle -> Evaluate route/safety/confirmation and hard-negative slices separately from aggregate scores.
- Execution smoke may fail because of downstream runtime drift -> Keep it optional and controlled, and report it separately from pure contract metrics.
- A100 training may create misplaced artifacts -> Any remote GPU work must write under the approved private A100 project root and keep checkpoints/logs out of public git unless explicitly exported.

## Migration Plan

This is a new repository with no existing runtime users. The apply phase should first add project scaffolding and public sample validation, then add SFT, then DPO, then reporting and execution smoke. Rollback is removing the active change artifacts or reverting the generated project files before public release.

## Open Questions

- Which exact Qwen checkpoint should become the first default config after dependency versions are pinned?
- Which Voice-to-Browser Agent trace/export path should be the canonical local import path for full-corpus builds?
