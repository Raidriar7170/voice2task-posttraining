## Context

The archived A100 assistant-only rerun evidence shows that the current SFT path masks prompt tokens and applies loss to assistant contract tokens, but the resulting three train-split predictions still have `json_valid_rate=0.0000` at the Browser Task Contract schema layer. The raw decoded sidecar shows all three generations are parseable JSON objects and the generation trace shows EOS completion, so the next useful step is field-level schema diagnosis rather than another private training run.

## Goals / Non-Goals

**Goals:**
- Produce a public-safe diagnosis that explains the remaining schema-output failure mode using committed rerun evidence.
- Separate raw JSON object parseability from schema-valid Browser Task Contract success.
- Report row-level and aggregate missing/incorrect field patterns.
- Recommend the next bounded phase without selecting a hidden or unreviewed implementation fix.

**Non-Goals:**
- Do not run new A100 training or private-adapter prediction.
- Do not repair, coerce, normalize, or replace invalid predictions.
- Do not modify decoding, prompt templates, schemas, data generation, or training objectives in this phase.
- Do not make checkpoint, adapter, held-out generalization, live-browser benchmark, or production-readiness claims.

## Decisions

- Generate a static diagnosis artifact from committed public-safe evidence. This keeps the phase deterministic and reviewable, and avoids mixing private runtime state into the repo.
- Treat `raw_json_parseable=true` and `contract_schema_valid=false` as separate dimensions. The prior report's `json_valid_rate` is a schema-valid Browser Task Contract metric, while raw sidecars can still contain parseable JSON objects.
- Use row ids and field names, not private prompts, remote paths, adapter paths, or raw logs. This preserves the existing public-sample evidence boundary.
- Recommend a follow-up fix phase only after the diagnostic evidence identifies the dominant failure pattern.

## Risks / Trade-offs

- [Risk] A static artifact can drift if the source evidence changes. -> Mitigation: add a regression test that cross-checks diagnosis counts against the committed source evidence.
- [Risk] The diagnosis may look like a model-quality claim. -> Mitigation: include explicit non-claim boundaries in JSON, Markdown, Human Brief, and OpenSpec spec text.
- [Risk] The small train split may overfit the diagnosis to one seed family. -> Mitigation: label the evidence as train-internal and recommend a bounded follow-up rather than broad remediation.
