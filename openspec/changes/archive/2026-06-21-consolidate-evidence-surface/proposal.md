## Why

Voice2Task now has multiple valuable but overlapping evidence layers from the
step-matched canonical-slot ablation and Contract V2 projection phases. The
current README, CONTEXT, active OpenSpec list, and report entry points make it
too easy to confuse historical, blocked, superseded, and current evidence.

This change consolidates the public truth surface without changing model
weights, data boundaries, evaluator behavior, schema semantics, or historical
metrics.

## What Changes

- Rewrite README.md and README_en.md around a short current snapshot, the latest
  model experiment, the latest architecture projection, and explicit claim
  boundaries.
- Rewrite CONTEXT.md as the compact developer/Codex context for the current
  formal data boundary, technical interpretation, claim limits, and next change.
- Add `reports/public-sample/EVIDENCE_INDEX.md` and a machine-readable
  evidence index that classifies current, historical, superseded, blocked,
  design-only, raw-input, and archived evidence.
- Add a small consistency/privacy check script and pytest coverage for the
  evidence surface.
- Archive completed, blocked-then-recovered, deprecated, or superseded OpenSpec
  changes so the active change list reflects the current truth surface.
- Add a concise Chinese Human Brief for this cleanup phase.
- Preserve all raw report artifacts and negative results unchanged.

## Capabilities

### New Capabilities

- `evidence-surface`: Public and developer-facing evidence surfaces MUST expose
  the current Voice2Task truth without overstating model, execution, production,
  safety, held-out, or live-browser claims.

### Modified Capabilities

- None.

## Impact

- Affected documentation: README.md, README_en.md, CONTEXT.md, and a new
  `reports/public-sample/EVIDENCE_INDEX.md`.
- Affected verification: a new lightweight evidence-surface checker and focused
  pytest coverage.
- Affected OpenSpec state: completed or superseded changes are archived; after
  cleanup and archive, the active change list should contain zero changes.
- Non-goals: generic chat fine-tuning, skill routing, GUI action policy
  learning, first-phase GRPO, DPO follow-up, training or prediction reruns,
  Contract V2 implementation, evaluator/schema/data changes, public release of
  private corpus, checkpoint/adapter release, and any live-browser or production
  readiness claim.
