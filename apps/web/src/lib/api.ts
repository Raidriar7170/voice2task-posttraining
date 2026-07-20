import type {
  APIErrorBody,
  ConfirmationChallenge,
  CreateSessionResponse,
  ExecutionEvent,
  PublicConfig,
  SessionRecord,
} from "../types";

export class DemoAPIError extends Error {
  code: string;
  retryable: boolean;

  constructor(code: string, message: string, retryable = false) {
    super(message);
    this.name = "DemoAPIError";
    this.code = code;
    this.retryable = retryable;
  }
}

async function requestJSON<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, init);
  const payload = (await response.json()) as T | APIErrorBody;
  if (!response.ok) {
    const body = payload as APIErrorBody;
    throw new DemoAPIError(body.error.code, body.error.message, body.error.retryable);
  }
  return payload as T;
}

async function requestNoContent(path: string, init: RequestInit): Promise<void> {
  const response = await fetch(path, init);
  if (response.ok) return;
  const body = (await response.json()) as APIErrorBody;
  throw new DemoAPIError(body.error.code, body.error.message, body.error.retryable);
}

export const api = {
  config: () => requestJSON<PublicConfig>("/api/config/public"),
  sessions: () => requestJSON<{ sessions: SessionRecord[] }>("/api/sessions"),
  session: (sessionId: string) =>
    requestJSON<{ session: SessionRecord }>(`/api/sessions/${encodeURIComponent(sessionId)}`),
  events: (sessionId: string, afterSeq = 0) =>
    requestJSON<{ events: ExecutionEvent[] }>(
      `/api/sessions/${encodeURIComponent(sessionId)}/events?after_seq=${afterSeq}`,
    ),
  createText: (text: string, email: string) =>
    requestJSON<CreateSessionResponse>("/api/sessions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ input_kind: "text", text, profile: { email } }),
    }),
  createAudio: (file: File, email: string, fixtureId?: string) => {
    const form = new FormData();
    form.append("input_kind", "audio");
    form.append("audio", file);
    form.append("profile_email", email);
    if (fixtureId) form.append("fixture_id", fixtureId);
    return requestJSON<CreateSessionResponse>("/api/sessions", { method: "POST", body: form });
  },
  confirmTranscript: (sessionId: string, transcript: string, planVersion: number) =>
    requestJSON<{ session: SessionRecord }>(
      `/api/sessions/${encodeURIComponent(sessionId)}/transcript`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ transcript, plan_version: planVersion }),
      },
    ),
  confirmationChallenge: (sessionId: string) =>
    requestJSON<ConfirmationChallenge>(
      `/api/sessions/${encodeURIComponent(sessionId)}/confirmation-challenge`,
      { method: "POST" },
    ),
  confirm: (
    sessionId: string,
    decision: "approve" | "reject",
    planVersion: number,
    confirmationToken: string,
  ) =>
    requestJSON<{ session: SessionRecord }>(`/api/sessions/${encodeURIComponent(sessionId)}/confirm`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        decision,
        plan_version: planVersion,
        confirmation_token: confirmationToken,
      }),
    }),
  execute: (sessionId: string) =>
    requestJSON<{ session: SessionRecord }>(`/api/sessions/${encodeURIComponent(sessionId)}/execute`, {
      method: "POST",
    }),
  cancel: (sessionId: string) =>
    requestJSON<{ session: SessionRecord }>(`/api/sessions/${encodeURIComponent(sessionId)}/cancel`, {
      method: "POST",
    }),
  deleteSession: (sessionId: string) =>
    requestNoContent(`/api/sessions/${encodeURIComponent(sessionId)}`, { method: "DELETE" }),
};
