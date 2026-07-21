import { describe, expect, it } from "vitest";

import { mergeEvents, shouldRefreshSnapshot } from "../hooks/useSessionEvents";
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

  it("refreshes the authoritative snapshot for every state-bearing event only", () => {
    const critical = [
      "SESSION_CREATED",
      "INPUT_RECEIVED",
      "AUDIO_ACCEPTED",
      "ASR_STARTED",
      "ASR_COMPLETED",
      "ASR_FAILED",
      "TRANSCRIPT_CONFIRMED",
      "TRANSCRIPT_EDITED",
      "INFERENCE_STARTED",
      "INFERENCE_COMPLETED",
      "CONTRACT_VALIDATED",
      "CONTRACT_REJECTED",
      "PLAN_COMPILED",
      "POLICY_ALLOWED",
      "POLICY_BLOCKED",
      "CONFIRMATION_REQUIRED",
      "CONFIRMATION_ACCEPTED",
      "CONFIRMATION_REJECTED",
      "EXECUTION_STARTED",
      "VERIFICATION_STARTED",
      "VERIFICATION_COMPLETED",
      "SESSION_COMPLETED",
      "SESSION_FAILED",
      "SESSION_CANCELLED",
    ];
    expect(critical.every(shouldRefreshSnapshot)).toBe(true);
    expect(shouldRefreshSnapshot("ACTION_COMPLETED")).toBe(false);
    expect(shouldRefreshSnapshot("ACTION_FAILED")).toBe(false);
  });
});
