## Context

The latest A100 rerun produced three train predictions and zero schema-valid Browser Task Contracts. The evidence shows:

- raw attempt 1 was non-JSON despite containing contract-like content;
- raw attempts 2 and 3 were JSON objects but used invalid or incomplete fields;
- retry attempts were JSON fragments wrapped in explanatory prose or Markdown;
- legacy route/task_type strings such as `search_web`, `open_url`, and path-like routes persisted.

This points to a decoding/output-shape problem that can be improved locally before spending A100 time again.

## Design Goals

- Make the retry prompt more canonical and JSON-only.
- Keep validation fail-closed: only `BrowserTaskContract.from_dict()` success counts as schema-valid.
- Preserve raw/retry attempts and decoded summaries for invalid outputs.
- Add public-safe diagnosis that explains whether the next A100 rerun is justified.

## Non-Goals

- No automatic repair that converts invalid model output into a valid contract for metrics.
- No training, A100 execution, private adapter loading, checkpoint release, or adapter release.
- No change to Browser Task Contract schema.
- No held-out generalization or live-browser improvement claim.

## Approach

1. Introduce a canonical Browser Task Contract skeleton for retry/constrained decoding instructions with legal enum values.
2. Update retry prompt wording to prohibit Markdown, prose, code fences, path-like routes, and legacy enum values.
3. Preserve existing schema guard metadata and sidecars.
4. Add local diagnostics over the required-field rerun evidence to classify failure families, especially legacy enum values and prose-wrapped JSON fragments.
5. Add focused tests for fake-model retry behavior and report/evidence boundaries.

## Risks

- A stronger prompt may improve local fake-model tests without improving real adapter output; reports must state this limitation.
- If constrained acceptance is mistaken for repair, metrics could overclaim. Tests must assert invalid outputs remain invalid.
- The next A100 rerun should only happen after local evidence shows the decoder/output-shape path is materially clearer.
