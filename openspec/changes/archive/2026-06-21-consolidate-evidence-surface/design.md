## Context

The repository has accumulated several related Voice2Task evidence phases:
slot-canonicalization policy work, paired SFT ablations, a step-matched
canonical-slot ablation, blocked Contract V2 projection, recovered projection
inputs, and a recovered-input Contract V2 projection rerun. The latest current
truth is split across README files, CONTEXT, report directories, and active
OpenSpec changes.

This design keeps the authoritative evidence in the existing report artifacts
and adds a small navigation and consistency layer above them. Historical
artifacts remain unchanged.

## Goals / Non-Goals

**Goals:**

- Make README.md and README_en.md expose only the current external-review
  snapshot, latest evidence links, and claim boundaries.
- Make CONTEXT.md a compact developer/Codex truth surface with the current data
  boundary, interpretation, claim limits, and one recommended next change.
- Add a unified public-sample evidence index with explicit status
  classification.
- Add a lightweight checker and pytest coverage to prevent drift between the
  current docs, latest Contract V2 projection summary, formal manifest, and
  evidence index.
- Archive completed, blocked-then-recovered, deprecated, and superseded
  OpenSpec changes so root active changes are zero after cleanup and archive.

**Non-Goals:**

- No training, prediction rerun, A100/SSH/GPU work, model/inference logic
  change, evaluator change, schema change, data/split change, Contract V2
  implementation, or metric recomputation.
- No deletion or rewriting of negative, blocked, superseded, or historical
  results.
- No new canonical candidate design, DPO/GRPO follow-up, challenge set, adapter
  release, or live-browser benchmark claim.

## Decisions

1. Keep raw report artifacts authoritative; add indexes instead of rewriting
   evidence.
   - Rationale: this preserves historical results and avoids silently changing
     evidence semantics.
   - Alternative considered: regenerate report summaries into a new consolidated
     report. Rejected because it risks merging metrics across manifests.

2. Use `reports/public-sample/evidence-index.json` as the machine-readable
   check target and `reports/public-sample/EVIDENCE_INDEX.md` as the human
   navigation surface.
   - Rationale: tests can validate JSON deterministically, while reviewers can
     scan Markdown.
   - Alternative considered: parse only Markdown tables. Rejected because table
     parsing would be brittle and harder to keep private-path safe.

3. Validate current README/CONTEXT metrics against the latest recovered-input
   Contract V2 projection summary and formal public-sample manifest.
   - Rationale: the latest projection conclusion and dataset counts are the
     values most likely to drift or be overclaimed.
   - Alternative considered: checking every historical metric. Rejected because
     this phase is an evidence-surface cleanup, not a report-audit phase.

4. Archive old OpenSpec changes with preservation, not deletion.
   - Rationale: archive paths retain proposal/design/tasks and blocked
     conclusions while removing stale active-state noise.
   - Alternative considered: leave inactive changes in root. Rejected because it
     contradicts the requested single current truth surface.

## Risks / Trade-offs

- Current docs could still omit a useful historical artifact -> Mitigation:
  keep historical artifacts in the evidence index rather than README/CONTEXT.
- OpenSpec archive classification could hide an unfinished blocked state ->
  Mitigation: record blocked/recovered relationship in the evidence index and
  keep archived change artifacts.
- Checker could become a second source of truth -> Mitigation: it only compares
  docs/index content to existing summary/manifest artifacts and does not compute
  new experiment results.
