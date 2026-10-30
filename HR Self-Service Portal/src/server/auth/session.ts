import { createHash, randomBytes } from "node:crypto";
import { cookies } from "next/headers";
import { cache } from "react";
import { prisma } from "@/server/db";
import { SESSION_COOKIE } from "@/server/auth/constants";

export { SESSION_COOKIE };

const SESSION_HOURS = 12;

export function createSessionToken() {
  return randomBytes(32).toString("base64url");
}

export function hashSessionToken(token: string) {
  return createHash("sha256").update(token).digest("hex");
}

export function sessionExpiry(from = new Date()) {
  return new Date(from.getTime() + SESSION_HOURS * 60 * 60 * 1000);
}

export const cookieOptions = (expires: Date) => ({
  httpOnly: true,
  sameSite: "lax" as const,
  secure: process.env.NODE_ENV === "production",
  path: "/",
  expires,
});

export const getCurrentSession = cache(async () => {
  const token = (await cookies()).get(SESSION_COOKIE)?.value;
  if (!token) return null;

  const session = await prisma.session.findUnique({
    where: { tokenHash: hashSessionToken(token) },
    include: { user: { include: { employee: true } } },
  });

  if (!session || session.expiresAt <= new Date() || !session.user.isActive) {
    return null;
  }

  const employee = session.user.employee;
  if (employee?.employmentStatus === "INACTIVE") {
    return null;
  }

  return session;
});

export async function hasSessionCookie() {
  return Boolean((await cookies()).get(SESSION_COOKIE)?.value);
}
