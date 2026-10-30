import { PrismaClient } from "@prisma/client";
import { hashPassword } from "../src/server/auth/password";

const prisma = new PrismaClient();

async function main() {
  const email = process.env.SEED_ADMIN_EMAIL?.trim().toLowerCase();
  const password = process.env.SEED_ADMIN_PASSWORD;
  const name = process.env.SEED_ADMIN_NAME?.trim() || "Administrator";
  const companyName = process.env.SEED_COMPANY_NAME?.trim() || "Your organization";
  const employeeCode = process.env.SEED_ADMIN_EMPLOYEE_CODE?.trim() || "ADM-001";

  if (!email || !password || password.length < 10) {
    throw new Error("Set SEED_ADMIN_EMAIL and a SEED_ADMIN_PASSWORD of at least 10 characters.");
  }

  const organization = await prisma.organization.findFirst();
  if (!organization) {
    await prisma.organization.create({
      data: { companyName, appName: "PeopleHub", timezone: "Asia/Kolkata" },
    });
  }

  const existing = await prisma.user.findUnique({ where: { email } });
  if (existing) {
    console.log(`Administrator ${email} already exists.`);
    return;
  }

  await prisma.user.create({
    data: {
      email,
      passwordHash: await hashPassword(password),
      role: "ADMINISTRATOR",
      employee: {
        create: {
          employeeCode,
          fullName: name,
          department: "Administration",
          designation: "Administrator",
          joiningDate: new Date("2026-01-01T00:00:00.000Z"),
        },
      },
    },
  });

  const admin = await prisma.user.findUniqueOrThrow({ where: { email } });
  await prisma.auditLog.create({
    data: {
      actorUserId: admin.id,
      action: "organization.bootstrapped",
      entityType: "Organization",
      entityId: admin.id,
    },
  });
  console.log(`Created administrator ${email}.`);
}

main()
  .catch((error) => {
    console.error(error instanceof Error ? error.message : error);
    process.exit(1);
  })
  .finally(async () => {
    await prisma.$disconnect();
  });
