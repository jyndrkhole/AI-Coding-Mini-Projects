/** Idle sign-out for an internal HR app, with a hard stop after 12 hours. */
export const SESSION_IDLE_MS = 30 * 60 * 1000;
export const SESSION_ABSOLUTE_MS = 12 * 60 * 60 * 1000;

export function sessionTimedOut(session: { expiresAt: Date; lastSeenAt: Date }, now = new Date()) {
  if (session.expiresAt.getTime() <= now.getTime()) return true;
  return now.getTime() - session.lastSeenAt.getTime() > SESSION_IDLE_MS;
}
