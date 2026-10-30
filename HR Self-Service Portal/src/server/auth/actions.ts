"use server";

import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { paddingPasswordHash, verifyPassword } from "@/server/auth/password";
import {
  SESSION_COOKIE,
  cookieOptions,
  createSessionToken,
  getCurrentSession,
  hashSessionToken,
  sessionExpiry,
} from "@/server/auth/session";
import { prisma } from "@/server/db";

const WINDOW_MS = 15 * 60 * 1000;
const MAX_FAILURES = 8;

export type ActionState = { error: string };

function safeNext(value: string, role: string) {
  if (!value.startsWith("/") || value.startsWith("//") || value.includes("\\")) {
    return role === "ADMINISTRATOR" ? "/admin" : "/dashboard";
  }
  if (role !== "ADMINISTRATOR" && value.startsWith("/admin")) return "/dashboard";
  return value;
}

function rethrowRedirect(error: unknown): never | void {
  if (
    typeof error === "object" &&
    error !== null &&
    "digest" in error &&
    String((error as { digest?: unknown }).digest).startsWith("NEXT_REDIRECT")
  ) {
    throw error;
  }
}

export async function loginAction(_state: ActionState, formData: FormData): Promise<ActionState> {
  const email = String(formData.get("email") ?? "").trim().toLowerCase();
  const password = String(formData.get("password") ?? "");
  const next = String(formData.get("next") ?? "");

  if (!email || !password) {
    return { error: "Enter your email and password." };
  }

  try {
    const since = new Date(Date.now() - WINDOW_MS);
    const failures = await prisma.loginAttempt.count({
      where: { email, successful: false, createdAt: { gte: since } },
    });
    if (failures >= MAX_FAILURES) {
      return { error: "Too many sign-in attempts. Try again in a few minutes." };
    }

    const user = await prisma.user.findUnique({
      where: { email },
      include: { employee: true },
    });
const passwordHash = user?.passwordHash ?? (await paddingPasswordHash());
    const passwordMatches = await verifyPassword(password, passwordHash);

    if (!user || !passwordMatches) {
      await prisma.loginAttempt.create({ data: { email, successful: false } });
      return { error: "The email or password is incorrect." };
    }

    if (!user.isActive || user.employee?.employmentStatus === "INACTIVE") {
      await prisma.loginAttempt.create({
        data: { email, successful: false, userId: user.id },
      });
      return { error: "This account is inactive. Ask an administrator for help." };
    }

    if (user.role === "MANAGER") {
      return { error: "Manager sign-in is not available yet." };
    }

    const token = createSessionToken();
    const expiresAt = sessionExpiry();
    await prisma.$transaction([
      prisma.session.create({
        data: { userId: user.id, tokenHash: hashSessionToken(token), expiresAt },
      }),
      prisma.loginAttempt.create({ data: { email, successful: true, userId: user.id } }),
    ]);

    const cookieStore = await cookies();
    cookieStore.set(SESSION_COOKIE, token, cookieOptions(expiresAt));
    redirect(safeNext(next, user.role));
  } catch (error) {
    rethrowRedirect(error);
    return { error: "PeopleHub cannot reach the database. Check that PostgreSQL is running." };
  }
}

export async function logoutAction() {
  const session = await getCurrentSession();
  const cookieStore = await cookies();
  const token = cookieStore.get(SESSION_COOKIE)?.value;
  if (session) {
    await prisma.session.delete({ where: { id: session.id } });
  } else if (token) {
    await prisma.session.deleteMany({ where: { tokenHash: hashSessionToken(token) } });
  }
  cookieStore.delete(SESSION_COOKIE);
  redirect("/login");
}
