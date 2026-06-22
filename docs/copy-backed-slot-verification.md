# Copy-backed Slot Verification

This document describes the bounded offline verifier implemented by `implement-copy-backed-slot-verification-slice`.

## Source-span semantics

- Source basis: original `input_text` from recovered public-safe raw inputs.
- Offset unit: Python/Unicode character index.
- Start is inclusive and end is exclusive.
- A verified exact span must satisfy `input_text[start:end] == span.text`.
- A verified normalized span must map from normalized text back to one contiguous original source span.
- The verifier records `source_text_hash` and never trusts model-authored provenance.

## Matching boundary

Exact matching runs first. If exact lookup is absent, bounded normalized matching may use Unicode NFKC, casefolding, and whitespace/punctuation separator omission. It does not use city aliases, product aliases, date conversion, URL resolving, semantic scoring, LLM judging, embeddings, or fuzzy matching.

## Action stays disabled

Action stays disabled in this phase. `action` is analyzed only because its semantics depend on blocked, clarify, and safety contexts; it receives no verified provenance and is not an acceptance gate.

## Provenance is not correctness

The verifier can prove that an eligible predicted value is present as a unique source span. It does not prove the task type, route, slot selection, executable behavior, or model quality. The report therefore separates source-verified predictions from source-verified-and-gold-correct predictions and source-verified-but-gold-mismatch predictions.

## Current evidence

- Decision: `COPY_SLICE_READY_FOR_SHADOW_INTEGRATION`.
- Enabled triples: `extract:extract_page:target, form_fill:fill_form:field, search:search_web:query`.
- Gold unique verified span rate: 0.863850.
- Prediction source-verified rate over eligible events: 0.874419.
- Provenance false accepts: 0.
- Silent fallbacks: 0.
- V1 evaluator zero delta: True.

## Claim boundary

No training, prediction rerun, data mutation, V1 schema migration, ContractCoreV2 change, evaluator relaxation, action enablement, runtime integration, model improvement claim, slot accuracy claim, executable quality claim, production readiness claim, held-out recovery claim, or live browser claim occurred.
