/** Build the canonical transaction fingerprint used for duplicate detection. */
export function buildFingerprint(
  date: string,
  merchant: string,
  amount: number,
  account: string
): string {
  return [
    date,
    merchant.trim().toLowerCase(),
    Number(amount).toFixed(2),
    account.trim().toLowerCase(),
  ].join("|");
}

export function normalizeTags(tags: unknown): string[] {
  if (!Array.isArray(tags)) return [];
  const seen = new Set<string>();
  const out: string[] = [];
  for (const raw of tags) {
    if (typeof raw !== "string") continue;
    const trimmed = raw.trim();
    if (!trimmed) continue;
    const key = trimmed.toLowerCase();
    if (seen.has(key)) continue;
    seen.add(key);
    out.push(trimmed);
  }
  return out;
}

export function safeFilename(name: string): string {
  return name.replace(/[^a-zA-Z0-9._-]+/g, "_").slice(0, 120) || "file";
}
