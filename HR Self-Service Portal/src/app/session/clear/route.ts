import { cookies } from "next/headers";
import { NextResponse } from "next/server";
import { SESSION_COOKIE } from "@/server/auth/constants";
import { hashSessionToken } from "@/server/auth/session";
import { prisma } from "@/server/db";

export async function GET(request: Request) {
  const cookieStore = await cookies();
  const token = cookieStore.get(SESSION_COOKIE)?.value;

  if (token) {
    try {
      const session = await prisma.session.findUnique({
        where: { tokenHash: hashSessionToken(token) },
        include: { user: { include: { employee: true } } },
      });
      const usable =
        session &&
        session.expiresAt > new Date() &&
        session.user.isActive &&
        session.user.employee?.employmentStatus !== "INACTIVE";
      if (usable) {
        return NextResponse.redirect(new URL("/", request.url));
      }
      if (session) {
        await prisma.session.delete({ where: { id: session.id } });
      }
    } catch {
      // Still drop the cookie when the database cannot be reached.
    }
  }

  cookieStore.delete(SESSION_COOKIE);
  return NextResponse.redirect(new URL("/login", request.url));
}
