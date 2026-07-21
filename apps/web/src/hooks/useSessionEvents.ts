import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import type { ConnectionState, ExecutionEvent } from "../types";

const SNAPSHOT_EVENT_TYPES = new Set([
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
]);

export function shouldRefreshSnapshot(eventType: string): boolean {
  return SNAPSHOT_EVENT_TYPES.has(eventType);
}

export function mergeEvents(current: ExecutionEvent[], incoming: ExecutionEvent[]): ExecutionEvent[] {
  const bySequence = new Map<number, ExecutionEvent>();
  for (const event of [...current, ...incoming]) bySequence.set(event.seq, event);
  return [...bySequence.values()].sort((left, right) => left.seq - right.seq);
}

export function useSessionEvents(
  sessionId: string | null,
  onSnapshotSignal?: (event: ExecutionEvent) => void,
) {
  const [events, setEvents] = useState<ExecutionEvent[]>([]);
  const [connectionState, setConnectionState] = useState<ConnectionState>("idle");
  const lastSequence = useRef(0);
  const activeSession = useRef(sessionId);
  const pendingReplay = useRef<{ sessionId: string; events: ExecutionEvent[] } | null>(null);
  const snapshotSignal = useRef(onSnapshotSignal);
  activeSession.current = sessionId;
  snapshotSignal.current = onSnapshotSignal;

  const replaceEvents = useCallback((targetSessionId: string, replay: ExecutionEvent[]) => {
    pendingReplay.current = { sessionId: targetSessionId, events: replay };
    if (activeSession.current !== targetSessionId) return;
    lastSequence.current = replay.reduce((highest, event) => Math.max(highest, event.seq), 0);
    setEvents(replay);
    pendingReplay.current = null;
  }, []);

  useEffect(() => {
    const replay = pendingReplay.current?.sessionId === sessionId
      ? pendingReplay.current.events
      : [];
    pendingReplay.current = null;
    setEvents(replay);
    lastSequence.current = replay.reduce((highest, event) => Math.max(highest, event.seq), 0);
    if (!sessionId) {
      setConnectionState("idle");
      return;
    }
    let disposed = false;
    let socket: WebSocket | null = null;
    let reconnectTimer: number | null = null;
    let attempts = 0;

    const connect = () => {
      if (disposed) return;
      setConnectionState(attempts === 0 ? "connecting" : "reconnecting");
      const scheme = window.location.protocol === "https:" ? "wss" : "ws";
      socket = new WebSocket(
        `${scheme}://${window.location.host}/ws/sessions/${encodeURIComponent(sessionId)}?after_seq=${lastSequence.current}`,
      );
      socket.onopen = () => {
        attempts = 0;
        setConnectionState("connected");
      };
      socket.onmessage = (message) => {
        const payload = JSON.parse(message.data) as ExecutionEvent | { type: "heartbeat"; after_seq: number };
        if ("type" in payload && payload.type === "heartbeat") return;
        const event = payload as ExecutionEvent;
        if (event.seq <= lastSequence.current) return;
        lastSequence.current = Math.max(lastSequence.current, event.seq);
        setEvents((current) => mergeEvents(current, [event]));
        if (shouldRefreshSnapshot(event.event_type)) snapshotSignal.current?.(event);
      };
      socket.onclose = (event) => {
        if (disposed) return;
        if (event.code === 1000) {
          setConnectionState("closed");
          return;
        }
        attempts += 1;
        setConnectionState("reconnecting");
        reconnectTimer = window.setTimeout(connect, Math.min(500 * 2 ** attempts, 5000));
      };
      socket.onerror = () => socket?.close();
    };

    connect();
    return () => {
      disposed = true;
      if (reconnectTimer !== null) window.clearTimeout(reconnectTimer);
      socket?.close(1000);
    };
  }, [sessionId]);

  return useMemo(
    () => ({ events, setEvents, replaceEvents, connectionState }),
    [events, replaceEvents, connectionState],
  );
}
