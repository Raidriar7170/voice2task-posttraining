## Context

The previous local output-boundary phase made the first-pass prompt and metadata explicit, and the following A100 rerun proved that those boundary clauses were visible at prediction time. The real model still emitted fenced JSON fragments. The existing strict parser correctly rejects those fragments, and that behavior is an important evaluator boundary rather than a bug.

This phase therefore avoids parser changes and moves one layer earlier: the generation call can ask Transformers to suppress tokenizer-derived Markdown fence token sequences with `bad_words_ids`. This is a local, testable decoding-policy change. It can prepare a later A100 rerun, but it does not itself prove model behavior improved.

## Goals / Non-Goals

**Goals:**

- Add a deterministic helper that derives public-safe Markdown fence suppression token sequences from the active tokenizer.
- Pass those token sequences to first-pass and retry `model.generate` calls when they are available.
- Surface suppression policy in prediction metadata and prompt snapshots.
- Add focused tests proving the generation call is wired and strict parsing still rejects wrapped JSON.
- Publish a bounded evidence pack and Human Brief that make non-claims explicit.

**Non-Goals:**

- No A100 execution, training, adapter/checkpoint release, deployment, private corpus publication, or public full-corpus release.
- No parser relaxation, embedded JSON extraction, prediction repair, output coercion, evaluator metric change, re-score, semantic-equivalence scoring, or slot normalization.
- No claim of model recovery, held-out generalization, production readiness, model-quality improvement, public checkpoint release, or live-browser benchmark improvement.

## Decisions

1. Use generation-time suppression rather than parser repair.

   `bad_words_ids` can prevent known fence token sequences from being generated without making existing invalid outputs valid. Parser repair was rejected because it would convert a boundary failure into apparent schema recovery.

2. Derive token ids from the runtime tokenizer and fail open when unavailable.

   Tokenizers differ in how they encode backticks and language-tagged fences. The helper will attempt common fence strings and only pass non-empty token sequences. If a tokenizer cannot encode these strings through a supported API, generation continues with metadata showing the configured suppression policy rather than inventing token ids.

3. Keep evidence local before rerunning A100.

   Local unit tests can prove that the generation kwargs and metadata changed. Only a later real A100 prediction-only rerun can determine whether adapter outputs stop using fences.

## Risks / Trade-offs

- [Risk] Tokenizer segmentation may not cover every fence form. -> Suppress common Markdown fence strings and record the sequence count as local wiring evidence, not universal proof.
- [Risk] `bad_words_ids` may interact with specific model/tokenizer implementations. -> Keep the helper minimal, pass the argument only when sequences are available, and verify with focused fake-tokenizer tests before any remote run.
- [Risk] The model may still produce prose or alternative wrappers. -> Preserve strict parser rejection and keep the next A100 rerun as an observation phase, not a quality claim.
- [Risk] Metadata could be misread as output recovery. -> Evidence and Human Brief must state no A100 execution occurred and no model-quality improvement is proven.
