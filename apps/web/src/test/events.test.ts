import { describe, expect, it } from "vitest";

import { mergeEvents } from "../hooks/useSessionEvents";
import type { ExecutionEvent } from "../types";

function event(seq: number): ExecutionEvent {
  return {
    session_id: "session",
    seq,
    event_type: "ACTION_COMPLETED",
    stage: "execution",
    status: "ok",
    message: `event-${seq}`,
    payload: {},
    created_at: "2026-07-20T00:00:00Z",
  };
}

describe("event replay merging", () => {
  it("deduplicates replay/live overlap and preserves sequence order", () => {
    expect(mergeEvents([event(1), event(3)], [event(2), event(3), event(4)]).map((item) => item.seq)).toEqual([
      1, 2, 3, 4,
    ]);
  });
});
