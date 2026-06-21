# Contract V2 Projection Decision

- Decision label: `PROJECTION_BLOCKED_OR_INVALID`
- Projection metrics computed: `false`
- Renderer evaluated: `false`
- Failure contribution analysis computed: `false`
- Bootstrap analysis computed: `false`

## Reason

The latest committed step-matched canonical-slot ablation evidence contains
boundary verification, aggregate metrics, paired row summaries, family deltas,
comparison, and decision artifacts. It does not contain the raw current
Control/Treatment dev/test prediction contracts or dev/test gold JSONL
contracts required for deterministic V2 projection.

Using older raw predictions under
`reports/public-sample/canonical-slot-paired-sft-ablation/` would violate the
current step-matched boundary, so they were rejected.

## Required Answers

1. V1 strict failures caused only by `normalized_command` / metadata:
   unavailable.
2. V2 core exact dev/test delta: unavailable.
3. V2 core executable pass delta: unavailable.
4. Whether slot bottleneck still dominates: unavailable from current raw
   projection evidence.
5. Safety and confirmation retention: unavailable from projection; current
   step-matched aggregate safety recall did not drop.
6. Renderer coverage: unavailable.
7. Whether Contract V2 is worth implementing: not established.
8. Final decision label: `PROJECTION_BLOCKED_OR_INVALID`.
9. Recommended next action: recover or commit public-safe raw step-matched
   prediction and gold contract artifacts, then rerun this same bounded
   projection evaluation.
10. Claims still forbidden: model improvement, held-out recovery, production
   readiness, safety readiness, live-browser benchmark gain, checkpoint release,
   adapter release, DPO justification, or approval for another small canonical
   candidate loop.

Hard stop: do not implement Contract V2, train, run DPO, generate new
predictions, expand data, or start a challenge-set phase from this blocked
result.
