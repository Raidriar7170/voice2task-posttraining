# Failure Contribution Analysis

Status: blocked.

No failure contribution counts were computed. The latest committed step-matched
evidence root has aggregate metrics and row-status summaries, but does not
include raw Control/Treatment dev/test prediction contracts or dev/test gold
JSONL contracts.

Because the analysis cannot compare field paths on aligned gold and prediction
contracts, it cannot honestly answer:

- how many V1 strict failures are `NORMALIZED_COMMAND_ONLY`;
- how many are `METADATA_ONLY`;
- how many are `DERIVED_FIELD_ONLY`;
- how many remain core slot, route/task, safety/confirmation, or mixed core
  residuals after projection.

Older non-step-matched raw predictions were intentionally not used.
