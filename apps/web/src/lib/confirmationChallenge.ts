import type { ConfirmationChallenge, SessionRecord } from "../types";

const CHALLENGE_PREFIX = "voice2task:confirmation:";

export function challengeStorageKey(sessionId: string, planVersion: number): string {
  return `${CHALLENGE_PREFIX}${encodeURIComponent(sessionId)}:v${planVersion}`;
}

function sessionChallengePrefix(sessionId: string): string {
  return `${CHALLENGE_PREFIX}${encodeURIComponent(sessionId)}:v`;
}

export function saveChallenge(
  storage: Storage,
  sessionId: string,
  challenge: ConfirmationChallenge,
): void {
  storage.setItem(
    challengeStorageKey(sessionId, challenge.plan_version),
    JSON.stringify(challenge),
  );
}

export function removeChallenge(
  storage: Storage,
  sessionId: string,
  planVersion: number,
): void {
  storage.removeItem(challengeStorageKey(sessionId, planVersion));
}

export function removeSessionChallenges(storage: Storage, sessionId: string): void {
  const prefix = sessionChallengePrefix(sessionId);
  const keys: string[] = [];
  for (let index = 0; index < storage.length; index += 1) {
    const key = storage.key(index);
    if (key?.startsWith(prefix)) keys.push(key);
  }
  for (const key of keys) storage.removeItem(key);
}

function parseChallenge(value: string): ConfirmationChallenge | null {
  try {
    const parsed = JSON.parse(value) as Partial<ConfirmationChallenge>;
    if (
      typeof parsed.confirmation_token !== "string"
      || typeof parsed.plan_id !== "string"
      || typeof parsed.plan_version !== "number"
      || typeof parsed.expires_at !== "string"
    ) return null;
    return parsed as ConfirmationChallenge;
  } catch {
    return null;
  }
}

export function loadMatchingChallenge(
  storage: Storage,
  session: SessionRecord,
  now = Date.now(),
): ConfirmationChallenge | null {
  const key = challengeStorageKey(session.id, session.plan_version);
  const stored = storage.getItem(key);
  const challenge = stored ? parseChallenge(stored) : null;
  const matches = session.status === "AWAITING_CONFIRMATION"
    && session.plan !== null
    && challenge !== null
    && challenge.plan_id === session.plan.plan_id
    && challenge.plan_version === session.plan_version
    && Date.parse(challenge.expires_at) > now;
  if (matches) return challenge;
  removeSessionChallenges(storage, session.id);
  return null;
}
