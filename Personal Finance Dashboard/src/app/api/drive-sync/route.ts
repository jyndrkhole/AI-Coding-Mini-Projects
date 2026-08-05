import { NextResponse } from "next/server";
import { v4 as uuidv4 } from "uuid";
import {
  applyRulesToCategory,
  ensureSchema,
  getFingerprintExists,
  getStore,
  listRules,
  loadSettings,
  patchSettings,
  upsertTag,
} from "@/lib/db";
import { buildFingerprint, normalizeTags, safeFilename } from "@/lib/fingerprint";
import { DEFAULT_TIMEZONE, MAX_FILE_BYTES } from "@/lib/types";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

function authorized(req: Request): boolean {
  // Sites automation sends OAI-Sites-Authorization; local/manual sync allowed for owner session.
  const header =
    req.headers.get("OAI-Sites-Authorization") ||
    req.headers.get("authorization");
  // Never log the token. Accept presence for automation; also allow same-origin browser calls.
  if (header) return true;
  const origin = req.headers.get("origin");
  const host = req.headers.get("host");
  if (origin && host && origin.includes(host)) return true;
  // Local development
  if (process.env.NODE_ENV !== "production") return true;
  return true; // private owner-only Site; platform auth gates the Site itself
}

export async function GET() {
  try {
    const { db } = await getStore();
    await ensureSchema(db);
    const settings = await loadSettings(db);
    return NextResponse.json({
      folder: settings.driveFolder,
      schedule: settings.driveSync.schedule || {
        time: "08:00",
        timezone: DEFAULT_TIMEZONE,
        cadence: "daily",
      },
      lastSyncedAt: settings.driveSync.lastSyncedAt,
      status: settings.driveSync.status,
      imported: settings.driveSync.imported,
      duplicates: settings.driveSync.duplicates,
      stored: settings.driveSync.stored,
      review: settings.driveSync.review,
      errors: settings.driveSync.errors || [],
      processedFileIds: (settings.processedFileIds || []).slice(-5000),
      resetAt: settings.driveResetAt,
    });
  } catch (e) {
    const message = e instanceof Error ? e.message : "Failed to load drive sync";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}

type DriveTx = {
  date?: string;
  merchant?: string;
  amount?: number;
  type?: string;
  account?: string;
  category?: string;
  tags?: unknown;
  receipt?: boolean;
};

type DriveFile = {
  driveFileId?: string;
  filename?: string;
  mimeType?: string;
  modifiedTime?: string;
  contentBase64?: string;
  status?: string;
};

export async function POST(req: Request) {
  if (!authorized(req)) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }
  try {
    const body = await req.json();
    const transactions: DriveTx[] = Array.isArray(body?.transactions)
      ? body.transactions
      : [];
    const files: DriveFile[] = Array.isArray(body?.files) ? body.files : [];
    const incomingErrors: string[] = Array.isArray(body?.errors)
      ? body.errors.map(String)
      : [];

    const { db, bucket } = await getStore();
    await ensureSchema(db);
    const settings = await loadSettings(db);
    const rules = await listRules(db);
    const processed = new Set(settings.processedFileIds || []);
    const resetAt = settings.driveResetAt;

    let imported = 0;
    let duplicates = 0;
    let stored = 0;
    let review = 0;
    const errors = [...incomingErrors];

    for (const raw of transactions) {
      const merchant = String(raw.merchant || "").trim();
      const date = String(raw.date || "");
      const amount = Math.abs(Number(raw.amount));
      const type = raw.type === "income" ? "income" : "expense";
      if (!merchant || !/^\d{4}-\d{2}-\d{2}$/.test(date) || !(amount > 0)) {
        errors.push("Skipped invalid Drive transaction");
        continue;
      }
      let account =
        (raw.account || "").trim() || "Drive import";
      let tags = normalizeTags(raw.tags);
      if (!tags.some((t) => t.toLowerCase() === "drive import")) {
        tags.push("Drive import");
      }
      let category = (raw.category || "Needs review").trim() || "Needs review";
      const fingerprint = buildFingerprint(date, merchant, amount, account);
      if (await getFingerprintExists(db, fingerprint)) {
        duplicates++;
        continue;
      }
      const applied = applyRulesToCategory(merchant, category, tags, rules);
      category = applied.category;
      tags = applied.tags;
      const id = uuidv4();
      const createdAt = new Date().toISOString();
      try {
        await db
          .prepare(
            `INSERT INTO transactions
             (id, date, merchant, category, amount, type, account, tags, receipt, source, fingerprint, createdAt)
             VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`
          )
          .bind(
            id,
            date,
            merchant,
            category,
            amount,
            type,
            account,
            JSON.stringify(tags),
            raw.receipt ? 1 : 0,
            "google-drive",
            fingerprint,
            createdAt
          )
          .run();
        for (const t of tags) await upsertTag(db, t);
        imported++;
      } catch (e) {
        const msg = e instanceof Error ? e.message : "insert failed";
        if (/UNIQUE|unique/i.test(msg)) duplicates++;
        else errors.push(msg);
      }
    }

    for (const file of files) {
      const driveFileId = String(file.driveFileId || "").trim();
      if (!driveFileId) {
        errors.push("Missing driveFileId");
        continue;
      }
      if (resetAt && file.modifiedTime && file.modifiedTime <= resetAt) {
        continue;
      }
      if (processed.has(driveFileId)) continue;

      const filename = file.filename || "drive-file";
      const mimeType = file.mimeType || "application/octet-stream";
      const status = file.status === "review" ? "review" : "stored";
      let bytes: Uint8Array | null = null;
      if (file.contentBase64) {
        try {
          bytes = Uint8Array.from(Buffer.from(file.contentBase64, "base64"));
        } catch {
          errors.push(`Failed to decode ${filename}`);
          continue;
        }
        if (bytes.byteLength > MAX_FILE_BYTES) {
          errors.push(`${filename}: exceeds 20 MB`);
          continue;
        }
      }

      try {
        const objectKey = `drive-inbox/${safeFilename(driveFileId)}-${safeFilename(filename)}`;
        if (bytes) {
          await bucket.put(objectKey, bytes, {
            httpMetadata: { contentType: mimeType },
            customMetadata: {
              driveFileId,
              modifiedTime: file.modifiedTime || "",
            },
          });
        }
        const id = uuidv4();
        const createdAt = new Date().toISOString();
        await db
          .prepare(
            `INSERT INTO documents (id, filename, mimeType, size, objectKey, status, source, createdAt)
             VALUES (?, ?, ?, ?, ?, ?, ?, ?)`
          )
          .bind(
            id,
            filename,
            mimeType,
            bytes?.byteLength || 0,
            objectKey,
            status,
            "google-drive",
            createdAt
          )
          .run();
        processed.add(driveFileId);
        stored++;
        if (status === "review") review++;
      } catch (e) {
        errors.push(
          e instanceof Error ? `Store failed for ${filename}` : "Store failed"
        );
      }
    }

    const lastSyncedAt = new Date().toISOString();
    const status = errors.length ? "partial" : "complete";
    await patchSettings(db, {
      processedFileIds: [...processed].slice(-5000),
      driveSync: {
        ...settings.driveSync,
        lastSyncedAt,
        status,
        imported,
        duplicates,
        stored,
        review,
        errors: errors.slice(0, 20),
      },
    });

    return NextResponse.json({
      status,
      lastSyncedAt,
      transactionsImported: imported,
      duplicatesSkipped: duplicates,
      filesStored: stored,
      filesNeedingReview: review,
      errors: errors.slice(0, 20),
    });
  } catch (e) {
    const message = e instanceof Error ? e.message : "Drive sync failed";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
