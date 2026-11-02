import { createHash, randomBytes } from "node:crypto";
import { cookies } from "next/headers";
import { cache } from "react";
import { prisma } from "@/server/db";
import { SESSION_COOKIE } from "@/server/auth/constants";
import { SESSION_ABSOLUTE_MS, sessionTimedOut } from "@/server/auth/timeout";

export { SESSION_COOKIE };

const TOUCH_AFTER_MS = 60 * 1000;

export function createSessionToken() {
  return randomBytes(32).toString("base64url");
}

export function hashSessionToken(token: string) {
  return createHash("sha256").update(token).digest("hex");
}

export function sessionExpiry(from = new Date()) {
  return new Date(from.getTime() + SESSION_ABSOLUTE_MS);
}

export const cookieOptions = (expires: Date) => ({
  httpOnly: true,
  sameSite: "lax" as const,
  secure: process.env.NODE_ENV === "production",
  path: "/",
  expires,
});

async function readSession(touch: boolean) {
  const token = (await cookies()).get(SESSION_COOKIE)?.value;
  if (!token) return null;

  const session = await prisma.session.findUnique({
    where: { tokenHash: hashSessionToken(token) },
    include: { user: { include: { employee: true } } },
  });

  if (!session || !session.user.isActive) {
    return null;
  }

  if (sessionTimedOut(session)) {
    await prisma.session.delete({ where: { id: session.id } }).catch(() => undefined);
    return null;
  }

  if (touch && Date.now() - session.lastSeenAt.getTime() > TOUCH_AFTER_MS) {
    await prisma.session.update({ where: { id: session.id }, data: { lastSeenAt: new Date() } }).catch(() => undefined);
  }

  const employee = session.user.employee;
  if (employee?.employmentStatus === "INACTIVE") {
    return null;
  }

  return session;
}

export const getCurrentSession = cache(() => readSession(true));

/** Checks the idle limit without extending it. Used when a tab has gone quiet. */
export function peekSession() {
  return readSession(false);
}

export async function hasSessionCookie() {
  return Boolean((await cookies()).get(SESSION_COOKIE)?.value);
}
