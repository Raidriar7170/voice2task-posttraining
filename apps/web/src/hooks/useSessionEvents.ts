import { useEffect, useMemo, useRef, useState } from "react";

import type { ConnectionState, ExecutionEvent } from "../types";

export function mergeEvents(current: ExecutionEvent[], incoming: ExecutionEvent[]): ExecutionEvent[] {
  const bySequence = new Map<number, ExecutionEvent>();
  for (const event of [...current, ...incoming]) bySequence.set(event.seq, event);
  return [...bySequence.values()].sort((left, right) => left.seq - right.seq);
}

export function useSessionEvents(sessionId: string | null) {
  const [events, setEvents] = useState<ExecutionEvent[]>([]);
  const [connectionState, setConnectionState] = useState<ConnectionState>("idle");
  const lastSequence = useRef(0);

  useEffect(() => {
    setEvents([]);
    lastSequence.current = 0;
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
        lastSequence.current = Math.max(lastSequence.current, event.seq);
        setEvents((current) => mergeEvents(current, [event]));
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
    () => ({ events, setEvents, connectionState }),
    [events, connectionState],
  );
}
