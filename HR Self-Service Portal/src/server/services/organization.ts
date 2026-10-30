import { cache } from "react";
import { prisma } from "@/server/db";

export const getOrganization = cache(async () => {
  const organization = await prisma.organization.findFirst();
  if (!organization) {
    throw new Error("Organization settings have not been created.");
  }
  return organization;
});
