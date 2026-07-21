import { afterEach, describe, expect, it, vi } from "vitest";

import { api } from "../lib/api";

afterEach(() => {
  vi.restoreAllMocks();
});

describe("frontend API client", () => {
  it("requests a typed confirmation challenge without reading it from create", async () => {
    const challenge = {
      confirmation_token: "raw-current-tab-token",
      plan_id: "plan-1",
      plan_version: 3,
      expires_at: "2026-07-20T00:05:00Z",
    };
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify(challenge), { status: 200 }),
    );

    await expect(api.confirmationChallenge("session/one")).resolves.toEqual(challenge);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/sessions/session%2Fone/confirmation-challenge",
      { method: "POST" },
    );
  });

  it("deletes one session without attempting to parse a 204 body", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(null, { status: 204 }),
    );

    await expect(api.deleteSession("session/one")).resolves.toBeUndefined();
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/sessions/session%2Fone",
      { method: "DELETE" },
    );
  });

  it("cancels one session through the explicit cancel endpoint", async () => {
    const payload = { session: { id: "session/one", status: "CANCELLED" } };
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify(payload), { status: 200 }),
    );

    await expect(api.cancel("session/one")).resolves.toEqual(payload);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/sessions/session%2Fone/cancel",
      { method: "POST" },
    );
  });
});
