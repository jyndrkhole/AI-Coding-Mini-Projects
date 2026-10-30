import bcrypt from "bcryptjs";

const COST = 12;

export function hashPassword(password: string) {
  return bcrypt.hash(password, COST);
}

let paddingHash: Promise<string> | null = null;

export function paddingPasswordHash() {
  paddingHash ??= hashPassword("peoplehub-timing-pad");
  return paddingHash;
}

export function verifyPassword(password: string, passwordHash: string) {
  return bcrypt.compare(password, passwordHash);
}
