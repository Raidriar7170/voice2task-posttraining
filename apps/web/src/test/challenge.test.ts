import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  challengeStorageKey,
  loadMatchingChallenge,
  removeChallenge,
  removeSessionChallenges,
  saveChallenge,
} from "../lib/confirmationChallenge";
import type { ConfirmationChallenge, SessionRecord } from "../types";

const challenge: ConfirmationChallenge = {
  confirmation_token: "raw-current-tab-token",
  plan_id: "plan-1",
  plan_version: 3,
  expires_at: "2026-07-20T00:05:00Z",
};

const session = {
  id: "session/one",
  status: "AWAITING_CONFIRMATION",
  plan_version: 3,
  plan: { plan_id: "plan-1", plan_version: 3 },
} as SessionRecord;

beforeEach(() => {
  sessionStorage.clear();
  localStorage.clear();
});

describe("same-tab confirmation challenge storage", () => {
  it("keys, stores, and loads only a matching unexpired session and plan version", () => {
    const localSet = vi.spyOn(Storage.prototype, "setItem");

    expect(challengeStorageKey("session/one", 3)).toContain("session%2Fone");
    expect(challengeStorageKey("session/one", 3)).toContain("3");
    saveChallenge(sessionStorage, "session/one", challenge);

    expect(
      loadMatchingChallenge(sessionStorage, session, Date.parse("2026-07-20T00:04:00Z")),
    ).toEqual(challenge);
    expect(localSet).toHaveBeenCalledTimes(1);
    expect(localSet.mock.instances[0]).toBe(sessionStorage);
    expect(localStorage.length).toBe(0);
  });

  it("clears expired, wrong-version, and terminal challenges", () => {
    saveChallenge(sessionStorage, session.id, challenge);
    expect(
      loadMatchingChallenge(sessionStorage, session, Date.parse("2026-07-20T00:05:00Z")),
    ).toBeNull();
    expect(sessionStorage.length).toBe(0);

    saveChallenge(sessionStorage, session.id, challenge);
    expect(
      loadMatchingChallenge(
        sessionStorage,
        { ...session, plan_version: 4 } as SessionRecord,
        Date.parse("2026-07-20T00:04:00Z"),
      ),
    ).toBeNull();
    expect(sessionStorage.length).toBe(0);

    saveChallenge(sessionStorage, session.id, challenge);
    expect(
      loadMatchingChallenge(
        sessionStorage,
        { ...session, status: "CANCELLED" } as SessionRecord,
        Date.parse("2026-07-20T00:04:00Z"),
      ),
    ).toBeNull();
    expect(sessionStorage.length).toBe(0);
  });

  it("removes an exact challenge or every version for one session only", () => {
    saveChallenge(sessionStorage, session.id, challenge);
    saveChallenge(sessionStorage, session.id, { ...challenge, plan_version: 4 });
    saveChallenge(sessionStorage, "session-two", challenge);

    removeChallenge(sessionStorage, session.id, 3);
    expect(sessionStorage.getItem(challengeStorageKey(session.id, 3))).toBeNull();
    expect(sessionStorage.getItem(challengeStorageKey(session.id, 4))).not.toBeNull();

    removeSessionChallenges(sessionStorage, session.id);
    expect(sessionStorage.getItem(challengeStorageKey(session.id, 4))).toBeNull();
    expect(sessionStorage.getItem(challengeStorageKey("session-two", 3))).not.toBeNull();
    expect(localStorage.length).toBe(0);
  });
});
